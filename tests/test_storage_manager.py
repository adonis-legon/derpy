"""Tests for storage manager."""

import pytest
from pathlib import Path
import tempfile
import shutil
from derpy.storage.manager import ImageManager, ImageMetadata, ImageInfo, StorageError
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


class TestImageMetadata:
    """Tests for ImageMetadata model."""
    
    def test_create_image_metadata(self):
        """Test creating image metadata."""
        metadata = ImageMetadata(
            tag="myapp:latest",
            manifest_digest="sha256:abc123",
            config_digest="sha256:def456",
            size=1024000,
            created="2024-01-15T10:00:00Z",
            architecture="amd64",
            os="linux",
            layers_count=3
        )
        assert metadata.tag == "myapp:latest"
        assert metadata.size == 1024000
        assert metadata.layers_count == 3
    
    def test_metadata_to_dict(self):
        """Test metadata serialization."""
        metadata = ImageMetadata(
            tag="myapp:latest",
            manifest_digest="sha256:abc123",
            config_digest="sha256:def456",
            size=1024000,
            created="2024-01-15T10:00:00Z",
            architecture="amd64",
            os="linux",
            layers_count=3
        )
        data = metadata.to_dict()
        assert data["tag"] == "myapp:latest"
        assert data["size"] == 1024000
    
    def test_metadata_from_dict(self):
        """Test metadata deserialization."""
        data = {
            "tag": "myapp:latest",
            "manifest_digest": "sha256:abc123",
            "config_digest": "sha256:def456",
            "size": 1024000,
            "created": "2024-01-15T10:00:00Z",
            "architecture": "amd64",
            "os": "linux",
            "layers_count": 3
        }
        metadata = ImageMetadata.from_dict(data)
        assert metadata.tag == "myapp:latest"
        assert metadata.size == 1024000


class TestImageInfo:
    """Tests for ImageInfo model."""
    
    def test_create_image_info(self):
        """Test creating image info."""
        info = ImageInfo(
            tag="myapp:latest",
            size=1024000,
            created="2024-01-15T10:00:00Z",
            architecture="amd64",
            os="linux"
        )
        assert info.tag == "myapp:latest"
        assert info.size == 1024000
    
    def test_image_info_str(self):
        """Test image info string representation."""
        info = ImageInfo(
            tag="myapp:latest",
            size=1024000,
            created="2024-01-15T10:00:00Z",
            architecture="amd64",
            os="linux"
        )
        str_repr = str(info)
        assert "myapp:latest" in str_repr
        assert "amd64/linux" in str_repr
    
    def test_format_size(self):
        """Test size formatting."""
        # Test bytes
        assert "B" in ImageInfo._format_size(500)
        # Test KB
        assert "KB" in ImageInfo._format_size(2048)
        # Test MB
        assert "MB" in ImageInfo._format_size(2 * 1024 * 1024)
        # Test GB
        assert "GB" in ImageInfo._format_size(2 * 1024 * 1024 * 1024)


class TestImageManager:
    """Tests for ImageManager."""
    
    def create_test_image(self, tag: str = "test:latest") -> Image:
        """Helper to create a test image."""
        import hashlib
        
        # Create a simple test layer with real digest
        layer_content = b"test layer content"
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
    
    def test_create_image_manager(self):
        """Test creating image manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            manager = ImageManager(repo_path)
            assert manager.repository_path == repo_path
            assert repo_path.exists()
    
    def test_initialize_repository(self):
        """Test repository initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            manager = ImageManager(repo_path)
            
            # Check OCI layout structure
            assert (repo_path / "oci-layout").exists()
            assert (repo_path / "blobs" / "sha256").exists()
            assert (repo_path / "index.json").exists()
            assert manager.metadata_path.exists()
    
    def test_store_and_get_image(self):
        """Test storing and retrieving an image."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            manager = ImageManager(repo_path)
            
            # Create and store test image
            image = self.create_test_image("myapp:v1")
            manager.store_image(image, "myapp:v1")
            
            # Retrieve image
            retrieved = manager.get_image("myapp:v1")
            assert retrieved is not None
            assert retrieved.config.architecture == "amd64"
            assert len(retrieved.layers) == 1
    
    def test_image_exists(self):
        """Test checking if image exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            manager = ImageManager(repo_path)
            
            # Image doesn't exist yet
            assert not manager.image_exists("myapp:v1")
            
            # Store image
            image = self.create_test_image("myapp:v1")
            manager.store_image(image, "myapp:v1")
            
            # Image now exists
            assert manager.image_exists("myapp:v1")
    
    def test_list_local_images(self):
        """Test listing local images."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            manager = ImageManager(repo_path)
            
            # Empty list initially
            images = manager.list_local_images()
            assert len(images) == 0
            
            # Store some images
            image1 = self.create_test_image("app1:v1")
            manager.store_image(image1, "app1:v1")
            
            image2 = self.create_test_image("app2:v2")
            manager.store_image(image2, "app2:v2")
            
            # List images
            images = manager.list_local_images()
            assert len(images) == 2
            tags = [img.tag for img in images]
            assert "app1:v1" in tags
            assert "app2:v2" in tags
    
    def test_delete_image(self):
        """Test deleting an image."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            manager = ImageManager(repo_path)
            
            # Store image
            image = self.create_test_image("myapp:v1")
            manager.store_image(image, "myapp:v1")
            
            # Delete image
            result = manager.delete_image("myapp:v1")
            assert result is True
            
            # Image no longer exists
            assert not manager.image_exists("myapp:v1")
            
            # Deleting non-existent image returns False
            result = manager.delete_image("nonexistent:v1")
            assert result is False
    
    def test_get_repository_size(self):
        """Test calculating repository size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            manager = ImageManager(repo_path)
            
            # Initial size
            initial_size = manager.get_repository_size()
            
            # Store image
            image = self.create_test_image("myapp:v1")
            manager.store_image(image, "myapp:v1")
            
            # Size should increase
            new_size = manager.get_repository_size()
            assert new_size > initial_size


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



class TestImageManagerAdditional:
    """Additional tests for ImageManager."""
    
    def test_image_manager_has_store_image(self):
        """Test ImageManager has store_image method."""
        manager = ImageManager()
        assert hasattr(manager, 'store_image')
        assert callable(getattr(manager, 'store_image', None))
    
    def test_image_manager_has_list_local_images(self):
        """Test ImageManager has list_local_images method."""
        manager = ImageManager()
        assert hasattr(manager, 'list_local_images')
        assert callable(getattr(manager, 'list_local_images', None))
    
    def test_image_manager_has_image_exists(self):
        """Test ImageManager has image_exists method."""
        manager = ImageManager()
        assert hasattr(manager, 'image_exists')
        assert callable(getattr(manager, 'image_exists', None))
    
    def test_image_manager_has_prepare_image_for_push(self):
        """Test ImageManager has prepare_image_for_push method."""
        manager = ImageManager()
        assert hasattr(manager, 'prepare_image_for_push')
        assert callable(getattr(manager, 'prepare_image_for_push', None))
    
    def test_image_manager_has_get_image(self):
        """Test ImageManager has get_image method."""
        manager = ImageManager()
        assert hasattr(manager, 'get_image')
        assert callable(getattr(manager, 'get_image', None))
    
    def test_image_manager_has_delete_image(self):
        """Test ImageManager has delete_image method."""
        manager = ImageManager()
        assert hasattr(manager, 'delete_image')
        assert callable(getattr(manager, 'delete_image', None))



class TestImageManagerAdditional:
    """Additional tests for ImageManager."""
    
    def test_image_manager_methods_exist(self):
        """Test ImageManager has required methods."""
        manager = ImageManager()
        assert hasattr(manager, 'store_image')
        assert hasattr(manager, 'list_local_images')
        assert callable(getattr(manager, 'store_image', None))
        assert callable(getattr(manager, 'list_local_images', None))



class TestImageManagerMethods:
    """Tests for ImageManager methods."""
    
    def test_image_manager_store_image_method_exists(self):
        """Test store_image method exists."""
        manager = ImageManager()
        assert hasattr(manager, 'store_image')
        assert callable(manager.store_image)
    
    def test_image_manager_get_image_method_exists(self):
        """Test get_image method exists."""
        manager = ImageManager()
        assert hasattr(manager, 'get_image')
        assert callable(manager.get_image)
    
    def test_image_manager_list_local_images_method_exists(self):
        """Test list_local_images method exists."""
        manager = ImageManager()
        assert hasattr(manager, 'list_local_images')
        assert callable(manager.list_local_images)


class TestStorageError:
    """Tests for StorageError."""
    
    def test_storage_error_creation(self):
        """Test creating StorageError."""
        from derpy.storage import StorageError
        error = StorageError("Test error")
        assert "Test error" in str(error)
    
    def test_storage_error_is_exception(self):
        """Test StorageError is an Exception."""
        from derpy.storage import StorageError
        assert issubclass(StorageError, Exception)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
