"""Tests for BaseImageManager."""

import pytest
from pathlib import Path
import tempfile
import tarfile
import gzip
import shutil
from unittest.mock import Mock, patch, MagicMock

from derpy.build.base_image import BaseImageManager
from derpy.build.models import ImageReference
from derpy.oci.models import Image, Manifest, ImageConfig, Layer, Descriptor, RootFS, ContainerConfig
from derpy.oci.models import MEDIA_TYPE_IMAGE_CONFIG, MEDIA_TYPE_IMAGE_LAYER, MEDIA_TYPE_IMAGE_MANIFEST
from derpy.storage.manager import ImageManager
from derpy.core.exceptions import BaseImageError


class TestImageReferenceParsing:
    """Tests for image reference parsing."""
    
    def test_parse_simple_image(self):
        """Test parsing simple image name."""
        registry, repo, tag = BaseImageManager(Mock(), None).resolve_image_reference("nginx")
        assert registry == "docker.io"
        assert repo == "library/nginx"
        assert tag == "latest"
    
    def test_parse_image_with_tag(self):
        """Test parsing image with tag."""
        registry, repo, tag = BaseImageManager(Mock(), None).resolve_image_reference("ubuntu:22.04")
        assert registry == "docker.io"
        assert repo == "library/ubuntu"
        assert tag == "22.04"
    
    def test_parse_image_with_registry(self):
        """Test parsing image with registry."""
        registry, repo, tag = BaseImageManager(Mock(), None).resolve_image_reference("ghcr.io/org/app:v1")
        assert registry == "ghcr.io"
        assert repo == "org/app"
        assert tag == "v1"
    
    def test_parse_image_with_port(self):
        """Test parsing image with registry port."""
        registry, repo, tag = BaseImageManager(Mock(), None).resolve_image_reference("localhost:5000/myapp:dev")
        assert registry == "localhost:5000"
        assert repo == "myapp"
        assert tag == "dev"
    
    def test_parse_image_with_namespace(self):
        """Test parsing image with namespace."""
        registry, repo, tag = BaseImageManager(Mock(), None).resolve_image_reference("myuser/myapp:latest")
        assert registry == "docker.io"
        assert repo == "myuser/myapp"
        assert tag == "latest"
    
    def test_parse_invalid_image_reference(self):
        """Test parsing invalid image reference."""
        manager = BaseImageManager(Mock(), None)
        with pytest.raises(BaseImageError):
            manager.resolve_image_reference("")
    
    def test_parse_image_with_digest(self):
        """Test parsing image with digest."""
        ref = ImageReference.parse("ubuntu@sha256:abc123")
        assert ref.registry == "docker.io"
        assert ref.repository == "library/ubuntu"
        assert ref.digest == "sha256:abc123"


class TestBaseImageCaching:
    """Tests for base image caching logic."""
    
    def test_cache_hit_returns_cached_image(self):
        """Test that cached image is returned without download."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Mock(spec=ImageManager)
            
            # Create a mock cached image
            cached_image = Mock(spec=Image)
            storage.get_image.return_value = cached_image
            
            manager = BaseImageManager(storage, Path(tmpdir))
            result = manager.pull_base_image("nginx:latest")
            
            assert result == cached_image
            storage.get_image.assert_called_once()
    
    def test_cache_miss_downloads_image(self):
        """Test that image is downloaded on cache miss."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Mock(spec=ImageManager)
            storage.get_image.return_value = None  # Cache miss
            
            manager = BaseImageManager(storage, Path(tmpdir))
            
            # Mock the registry client
            with patch('derpy.build.base_image.RegistryClient') as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value.__enter__.return_value = mock_client
                
                # Mock pull_image to return test data
                manifest_data = {
                    "schemaVersion": 2,
                    "mediaType": MEDIA_TYPE_IMAGE_MANIFEST,
                    "config": {
                        "mediaType": MEDIA_TYPE_IMAGE_CONFIG,
                        "digest": "sha256:config123",
                        "size": 100
                    },
                    "layers": []
                }
                config_data = {
                    "architecture": "amd64",
                    "os": "linux",
                    "rootfs": {"type": "layers", "diff_ids": []},
                    "config": {}
                }
                
                import json
                mock_client.pull_image.return_value = (
                    json.dumps(manifest_data).encode(),
                    json.dumps(config_data).encode(),
                    []
                )
                
                result = manager.pull_base_image("nginx:latest")
                
                assert result is not None
                mock_client.pull_image.assert_called_once()


class TestLayerExtraction:
    """Tests for layer extraction with whiteouts."""
    
    def test_extract_simple_layer(self):
        """Test extracting a simple layer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test layer tar.gz
            layer_dir = Path(tmpdir) / "layer"
            layer_dir.mkdir()
            (layer_dir / "test.txt").write_text("hello")
            
            layer_file = Path(tmpdir) / "layer.tar.gz"
            with tarfile.open(layer_file, 'w:gz') as tar:
                tar.add(layer_dir / "test.txt", arcname="test.txt")
            
            # Create test image
            layer = Layer(
                digest="sha256:test123",
                size=layer_file.stat().st_size,
                content_path=layer_file,
                diff_id="sha256:diff123"
            )
            
            manifest = Manifest(
                config=Descriptor(
                    media_type=MEDIA_TYPE_IMAGE_CONFIG,
                    digest="sha256:config",
                    size=100
                ),
                layers=[layer.to_descriptor()]
            )
            
            config = ImageConfig(
                architecture="amd64",
                os="linux",
                rootfs=RootFS(diff_ids=["sha256:diff123"])
            )
            
            image = Image(manifest=manifest, config=config, layers=[layer])
            
            # Extract
            target_dir = Path(tmpdir) / "rootfs"
            manager = BaseImageManager(Mock(), Path(tmpdir))
            result = manager.extract_base_image(image, target_dir)
            
            assert result == target_dir
            assert (target_dir / "test.txt").exists()
            assert (target_dir / "test.txt").read_text() == "hello"
    
    def test_extract_layer_with_whiteout(self):
        """Test extracting layer with whiteout files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create base layer with a file
            base_dir = Path(tmpdir) / "base"
            base_dir.mkdir()
            (base_dir / "file1.txt").write_text("base")
            (base_dir / "file2.txt").write_text("keep")
            
            base_file = Path(tmpdir) / "base.tar.gz"
            with tarfile.open(base_file, 'w:gz') as tar:
                tar.add(base_dir / "file1.txt", arcname="file1.txt")
                tar.add(base_dir / "file2.txt", arcname="file2.txt")
            
            # Create layer with whiteout
            layer_dir = Path(tmpdir) / "layer"
            layer_dir.mkdir()
            (layer_dir / ".wh.file1.txt").write_text("")  # Whiteout marker
            
            layer_file = Path(tmpdir) / "layer.tar.gz"
            with tarfile.open(layer_file, 'w:gz') as tar:
                tar.add(layer_dir / ".wh.file1.txt", arcname=".wh.file1.txt")
            
            # Create test image with both layers
            base_layer = Layer(
                digest="sha256:base123",
                size=base_file.stat().st_size,
                content_path=base_file,
                diff_id="sha256:basediff"
            )
            
            whiteout_layer = Layer(
                digest="sha256:layer123",
                size=layer_file.stat().st_size,
                content_path=layer_file,
                diff_id="sha256:layerdiff"
            )
            
            manifest = Manifest(
                config=Descriptor(
                    media_type=MEDIA_TYPE_IMAGE_CONFIG,
                    digest="sha256:config",
                    size=100
                ),
                layers=[base_layer.to_descriptor(), whiteout_layer.to_descriptor()]
            )
            
            config = ImageConfig(
                architecture="amd64",
                os="linux",
                rootfs=RootFS(diff_ids=["sha256:basediff", "sha256:layerdiff"])
            )
            
            image = Image(manifest=manifest, config=config, layers=[base_layer, whiteout_layer])
            
            # Extract
            target_dir = Path(tmpdir) / "rootfs"
            manager = BaseImageManager(Mock(), Path(tmpdir))
            result = manager.extract_base_image(image, target_dir)
            
            assert result == target_dir
            assert not (target_dir / "file1.txt").exists()  # Deleted by whiteout
            assert (target_dir / "file2.txt").exists()  # Should still exist
    
    def test_extract_layer_with_opaque_whiteout(self):
        """Test extracting layer with opaque whiteout."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create base layer with directory
            base_dir = Path(tmpdir) / "base"
            base_dir.mkdir()
            (base_dir / "dir").mkdir()
            (base_dir / "dir" / "file1.txt").write_text("old")
            (base_dir / "dir" / "file2.txt").write_text("old")
            
            base_file = Path(tmpdir) / "base.tar.gz"
            with tarfile.open(base_file, 'w:gz') as tar:
                tar.add(base_dir / "dir", arcname="dir", recursive=True)
            
            # Create layer with opaque whiteout
            layer_dir = Path(tmpdir) / "layer"
            layer_dir.mkdir()
            (layer_dir / "dir").mkdir()
            (layer_dir / "dir" / ".wh..wh..opq").write_text("")  # Opaque whiteout
            (layer_dir / "dir" / "new.txt").write_text("new")
            
            layer_file = Path(tmpdir) / "layer.tar.gz"
            with tarfile.open(layer_file, 'w:gz') as tar:
                tar.add(layer_dir / "dir", arcname="dir", recursive=True)
            
            # Create test image
            base_layer = Layer(
                digest="sha256:base123",
                size=base_file.stat().st_size,
                content_path=base_file,
                diff_id="sha256:basediff"
            )
            
            opaque_layer = Layer(
                digest="sha256:layer123",
                size=layer_file.stat().st_size,
                content_path=layer_file,
                diff_id="sha256:layerdiff"
            )
            
            manifest = Manifest(
                config=Descriptor(
                    media_type=MEDIA_TYPE_IMAGE_CONFIG,
                    digest="sha256:config",
                    size=100
                ),
                layers=[base_layer.to_descriptor(), opaque_layer.to_descriptor()]
            )
            
            config = ImageConfig(
                architecture="amd64",
                os="linux",
                rootfs=RootFS(diff_ids=["sha256:basediff", "sha256:layerdiff"])
            )
            
            image = Image(manifest=manifest, config=config, layers=[base_layer, opaque_layer])
            
            # Extract
            target_dir = Path(tmpdir) / "rootfs"
            manager = BaseImageManager(Mock(), Path(tmpdir))
            result = manager.extract_base_image(image, target_dir)
            
            assert result == target_dir
            assert (target_dir / "dir").exists()
            assert not (target_dir / "dir" / "file1.txt").exists()  # Cleared by opaque
            assert not (target_dir / "dir" / "file2.txt").exists()  # Cleared by opaque
            assert (target_dir / "dir" / "new.txt").exists()  # New file from layer


class TestBaseImageManagerErrors:
    """Tests for error handling in BaseImageManager."""
    
    def test_pull_image_not_found(self):
        """Test error when image is not found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Mock(spec=ImageManager)
            storage.get_image.return_value = None
            
            manager = BaseImageManager(storage, Path(tmpdir))
            
            with patch('derpy.build.base_image.RegistryClient') as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value.__enter__.return_value = mock_client
                mock_client.pull_image.side_effect = Exception("404 not found")
                
                with pytest.raises(BaseImageError, match="not found"):
                    manager.pull_base_image("nonexistent:latest")
    
    def test_extract_nonexistent_layer(self):
        """Test error when layer file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            layer = Layer(
                digest="sha256:test123",
                size=100,
                content_path=Path("/nonexistent/layer.tar.gz"),
                diff_id="sha256:diff123"
            )
            
            manifest = Manifest(
                config=Descriptor(
                    media_type=MEDIA_TYPE_IMAGE_CONFIG,
                    digest="sha256:config",
                    size=100
                ),
                layers=[layer.to_descriptor()]
            )
            
            config = ImageConfig(
                architecture="amd64",
                os="linux",
                rootfs=RootFS(diff_ids=["sha256:diff123"])
            )
            
            image = Image(manifest=manifest, config=config, layers=[layer])
            
            target_dir = Path(tmpdir) / "rootfs"
            manager = BaseImageManager(Mock(), Path(tmpdir))
            
            with pytest.raises(BaseImageError, match="not found"):
                manager.extract_base_image(image, target_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
