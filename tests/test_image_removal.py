"""Tests for image removal functionality in ImageManager."""

import pytest
from pathlib import Path
import tempfile
import hashlib
import os
from derpy.storage.manager import ImageManager, ImageMetadata, StorageError
from derpy.oci.models import (
    Image,
    ImageConfig,
    Manifest,
    Layer,
    Descriptor,
    RootFS,
    ContainerConfig,
    MEDIA_TYPE_IMAGE_CONFIG,
    MEDIA_TYPE_IMAGE_LAYER,
)


class TestImageRemoval:
    """Tests for ImageManager removal methods."""
    
    def create_test_image(self, tag: str = "test:latest") -> Image:
        """Helper to create a test image with real content."""
        # Create a simple test layer with real digest
        layer_content = b"test layer content for " + tag.encode()
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.tar.gz') as f:
            f.write(layer_content)
            layer_path = Path(f.name)
        
        # Compute real digest
        layer_digest = f"sha256:{hashlib.sha256(layer_content).hexdigest()}"
        
        layer = Layer(
            digest=layer_digest,
            size=len(layer_content),
            diff_id="sha256:testdiff123",
            content_path=layer_path
        )
        
        config = ImageConfig(
            architecture="amd64",
            os="linux",
            rootfs=RootFS(diff_ids=["sha256:testdiff123"]),
            config=ContainerConfig(cmd=["/bin/sh"]),
            created="2024-01-15T10:00:00Z"
        )
        
        config_desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_CONFIG,
            digest="sha256:testconfig123",
            size=100
        )
        
        layer_desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_LAYER,
            digest=layer_digest,
            size=len(layer_content)
        )
        
        manifest = Manifest(
            config=config_desc,
            layers=[layer_desc]
        )
        
        return Image(
            manifest=manifest,
            config=config,
            layers=[layer]
        )
    
    def test_remove_existing_image_returns_true(self):
        """Test removing existing image returns True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            manager = ImageManager(repo_path)
            
            # Store an image
            image = self.create_test_image("myapp:v1")
            manager.store_image(image, "myapp:v1")
            
            # Verify image exists
            assert manager.image_exists("myapp:v1")
            
            # Remove the image
            result = manager.remove_image("myapp:v1")
            
            # Should return True
            assert result is True
    
    def test_remove_nonexistent_image_returns_false(self):
        """Test removing non-existent image returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            manager = ImageManager(repo_path)
            
            # Try to remove non-existent image
            result = manager.remove_image("nonexistent:v1")
            
            # Should return False
            assert result is False
    
    def test_metadata_updated_after_removal(self):
        """Test metadata is updated correctly after removal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            manager = ImageManager(repo_path)
            
            # Store two images
            image1 = self.create_test_image("app1:v1")
            manager.store_image(image1, "app1:v1")
            
            image2 = self.create_test_image("app2:v2")
            manager.store_image(image2, "app2:v2")
            
            # Verify both exist
            assert manager.image_exists("app1:v1")
            assert manager.image_exists("app2:v2")
            
            # Remove one image
            manager.remove_image("app1:v1")
            
            # Verify metadata is updated
            assert not manager.image_exists("app1:v1")
            assert manager.image_exists("app2:v2")
            
            # Verify metadata file contains only app2:v2
            metadata = manager._load_metadata()
            assert "app1:v1" not in metadata
            assert "app2:v2" in metadata
    
    def test_oci_index_updated_after_removal(self):
        """Test OCI index is updated correctly after removal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            manager = ImageManager(repo_path)
            
            # Store an image
            image = self.create_test_image("myapp:v1")
            manager.store_image(image, "myapp:v1")
            
            # Verify manifest is in index
            manifest_desc = manager.oci_layout.get_manifest_by_tag("myapp:v1")
            assert manifest_desc is not None
            
            # Remove the image
            manager.remove_image("myapp:v1")
            
            # Verify manifest is removed from index
            manifest_desc = manager.oci_layout.get_manifest_by_tag("myapp:v1")
            assert manifest_desc is None
    
    def test_storage_error_on_permission_issues(self):
        """Test StorageError is raised on file permission issues."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            manager = ImageManager(repo_path)
            
            # Store an image
            image = self.create_test_image("myapp:v1")
            manager.store_image(image, "myapp:v1")
            
            # Make metadata file read-only to simulate permission error
            os.chmod(manager.metadata_path, 0o444)
            
            try:
                # Try to remove the image - should raise StorageError
                with pytest.raises(StorageError):
                    manager.remove_image("myapp:v1")
            finally:
                # Restore permissions for cleanup
                os.chmod(manager.metadata_path, 0o644)


class TestRemoveAllImages:
    """Tests for remove_all_images() method."""
    
    def create_test_image(self, tag: str = "test:latest") -> Image:
        """Helper to create a test image with real content."""
        # Create a simple test layer with real digest
        layer_content = b"test layer content for " + tag.encode()
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.tar.gz') as f:
            f.write(layer_content)
            layer_path = Path(f.name)
        
        # Compute real digest
        layer_digest = f"sha256:{hashlib.sha256(layer_content).hexdigest()}"
        
        layer = Layer(
            digest=layer_digest,
            size=len(layer_content),
            diff_id="sha256:testdiff123",
            content_path=layer_path
        )
        
        config = ImageConfig(
            architecture="amd64",
            os="linux",
            rootfs=RootFS(diff_ids=["sha256:testdiff123"]),
            config=ContainerConfig(cmd=["/bin/sh"]),
            created="2024-01-15T10:00:00Z"
        )
        
        config_desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_CONFIG,
            digest="sha256:testconfig123",
            size=100
        )
        
        layer_desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_LAYER,
            digest=layer_digest,
            size=len(layer_content)
        )
        
        manifest = Manifest(
            config=config_desc,
            layers=[layer_desc]
        )
        
        return Image(
            manifest=manifest,
            config=config,
            layers=[layer]
        )
    
    def test_remove_multiple_images_returns_correct_count(self):
        """Test removing multiple images returns correct count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            manager = ImageManager(repo_path)
            
            # Store three images
            image1 = self.create_test_image("app1:v1")
            manager.store_image(image1, "app1:v1")
            
            image2 = self.create_test_image("app2:v2")
            manager.store_image(image2, "app2:v2")
            
            image3 = self.create_test_image("app3:v3")
            manager.store_image(image3, "app3:v3")
            
            # Remove all images
            count = manager.remove_all_images()
            
            # Should return 3
            assert count == 3
    
    def test_remove_when_no_images_returns_zero(self):
        """Test removing when no images exist returns 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            manager = ImageManager(repo_path)
            
            # Remove all images (none exist)
            count = manager.remove_all_images()
            
            # Should return 0
            assert count == 0
    
    def test_metadata_file_cleared(self):
        """Test metadata file is cleared."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            manager = ImageManager(repo_path)
            
            # Store images
            image1 = self.create_test_image("app1:v1")
            manager.store_image(image1, "app1:v1")
            
            image2 = self.create_test_image("app2:v2")
            manager.store_image(image2, "app2:v2")
            
            # Remove all images
            manager.remove_all_images()
            
            # Verify metadata is empty
            metadata = manager._load_metadata()
            assert len(metadata) == 0
            assert metadata == {}
    
    def test_oci_layout_cleared(self):
        """Test OCI layout is cleared."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            manager = ImageManager(repo_path)
            
            # Store images
            image1 = self.create_test_image("app1:v1")
            manager.store_image(image1, "app1:v1")
            
            image2 = self.create_test_image("app2:v2")
            manager.store_image(image2, "app2:v2")
            
            # Verify blobs exist
            assert manager.blobs_path.exists()
            blob_count_before = len(list(manager.blobs_path.iterdir()))
            assert blob_count_before > 0
            
            # Remove all images
            manager.remove_all_images()
            
            # Verify blobs directory is recreated and empty
            assert manager.blobs_path.exists()
            blob_count_after = len(list(manager.blobs_path.iterdir()))
            assert blob_count_after == 0
            
            # Verify index is empty
            index = manager.oci_layout.load_index()
            assert index is not None
            assert len(index.manifests) == 0
    
    def test_storage_error_on_failures(self):
        """Test StorageError is raised on failures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            manager = ImageManager(repo_path)
            
            # Store an image
            image = self.create_test_image("myapp:v1")
            manager.store_image(image, "myapp:v1")
            
            # Make metadata file read-only to simulate permission error
            os.chmod(manager.metadata_path, 0o444)
            
            try:
                # Try to remove all images - should raise StorageError
                with pytest.raises(StorageError):
                    manager.remove_all_images()
            finally:
                # Restore permissions for cleanup
                os.chmod(manager.metadata_path, 0o644)


class TestSizeCalculation:
    """Tests for size calculation methods."""
    
    def create_test_image(self, tag: str = "test:latest") -> Image:
        """Helper to create a test image with real content."""
        # Create a simple test layer with real digest
        layer_content = b"test layer content for " + tag.encode()
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.tar.gz') as f:
            f.write(layer_content)
            layer_path = Path(f.name)
        
        # Compute real digest
        layer_digest = f"sha256:{hashlib.sha256(layer_content).hexdigest()}"
        
        layer = Layer(
            digest=layer_digest,
            size=len(layer_content),
            diff_id="sha256:testdiff123",
            content_path=layer_path
        )
        
        config = ImageConfig(
            architecture="amd64",
            os="linux",
            rootfs=RootFS(diff_ids=["sha256:testdiff123"]),
            config=ContainerConfig(cmd=["/bin/sh"]),
            created="2024-01-15T10:00:00Z"
        )
        
        config_desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_CONFIG,
            digest="sha256:testconfig123",
            size=100
        )
        
        layer_desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_LAYER,
            digest=layer_digest,
            size=len(layer_content)
        )
        
        manifest = Manifest(
            config=config_desc,
            layers=[layer_desc]
        )
        
        return Image(
            manifest=manifest,
            config=config,
            layers=[layer]
        )
    
    def test_calculate_storage_size_with_multiple_images(self):
        """Test calculate_storage_size() with multiple images."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            manager = ImageManager(repo_path)
            
            # Get initial size
            initial_size = manager.calculate_storage_size()
            
            # Store multiple images
            image1 = self.create_test_image("app1:v1")
            manager.store_image(image1, "app1:v1")
            
            image2 = self.create_test_image("app2:v2")
            manager.store_image(image2, "app2:v2")
            
            # Calculate size
            size = manager.calculate_storage_size()
            
            # Size should be greater than initial size
            assert size > initial_size
            assert size > 0
    
    def test_calculate_storage_size_with_empty_repository(self):
        """Test calculate_storage_size() with empty repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            manager = ImageManager(repo_path)
            
            # Calculate size of empty repository
            size = manager.calculate_storage_size()
            
            # Should have some size from OCI layout files
            assert size >= 0
    
    def test_get_cache_size_with_cache_directory(self):
        """Test get_cache_size() with cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            cache_dir.mkdir()
            
            # Create some test files in cache
            (cache_dir / "file1.txt").write_text("test content 1")
            (cache_dir / "file2.txt").write_text("test content 2")
            
            # Create subdirectory with files
            subdir = cache_dir / "subdir"
            subdir.mkdir()
            (subdir / "file3.txt").write_text("test content 3")
            
            # Calculate cache size
            repo_path = Path(tmpdir) / "images"
            manager = ImageManager(repo_path)
            size = manager.get_cache_size(cache_dir)
            
            # Should be sum of all file sizes
            expected_size = (
                len("test content 1") +
                len("test content 2") +
                len("test content 3")
            )
            assert size == expected_size
    
    def test_get_cache_size_with_nonexistent_directory(self):
        """Test get_cache_size() with non-existent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "nonexistent_cache"
            
            # Calculate cache size for non-existent directory
            repo_path = Path(tmpdir) / "images"
            manager = ImageManager(repo_path)
            size = manager.get_cache_size(cache_dir)
            
            # Should return 0
            assert size == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
