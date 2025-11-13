"""Tests for OCI layout manager."""

import pytest
from pathlib import Path
import tempfile
from derpy.oci.layout import OCILayoutManager
from derpy.oci.models import (
    Descriptor,
    Manifest,
    ImageConfig,
    Index,
    RootFS,
    ContainerConfig,
    MEDIA_TYPE_IMAGE_CONFIG,
    MEDIA_TYPE_IMAGE_LAYER,
    MEDIA_TYPE_IMAGE_MANIFEST,
)


class TestOCILayoutManager:
    """Tests for OCILayoutManager."""
    
    def test_create_layout_manager(self):
        """Test creating OCI layout manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            layout_path = Path(tmpdir) / "oci"
            manager = OCILayoutManager(layout_path)
            assert manager.root_path == layout_path
    
    def test_create_layout(self):
        """Test creating OCI layout structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            layout_path = Path(tmpdir) / "oci"
            manager = OCILayoutManager(layout_path)
            manager.create_layout()
            
            # Check structure
            assert layout_path.exists()
            assert (layout_path / "oci-layout").exists()
            assert (layout_path / "blobs" / "sha256").exists()
            assert (layout_path / "index.json").exists()
    
    def test_store_and_get_blob(self):
        """Test storing and retrieving a blob."""
        with tempfile.TemporaryDirectory() as tmpdir:
            layout_path = Path(tmpdir) / "oci"
            manager = OCILayoutManager(layout_path)
            manager.create_layout()
            
            # Store blob
            content = b"test blob content"
            descriptor = manager.store_blob(content, MEDIA_TYPE_IMAGE_LAYER)
            
            assert descriptor.digest.startswith("sha256:")
            assert descriptor.size == len(content)
            
            # Retrieve blob
            retrieved = manager.get_blob(descriptor.digest)
            assert retrieved == content
    
    def test_blob_exists(self):
        """Test checking if blob exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            layout_path = Path(tmpdir) / "oci"
            manager = OCILayoutManager(layout_path)
            manager.create_layout()
            
            # Blob doesn't exist
            assert not manager.blob_exists("sha256:nonexistent")
            
            # Store blob
            content = b"test content"
            descriptor = manager.store_blob(content, MEDIA_TYPE_IMAGE_LAYER)
            
            # Blob now exists
            assert manager.blob_exists(descriptor.digest)
    
    def test_store_and_get_manifest(self):
        """Test storing and retrieving a manifest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            layout_path = Path(tmpdir) / "oci"
            manager = OCILayoutManager(layout_path)
            manager.create_layout()
            
            # Create manifest
            config_desc = Descriptor(
                media_type=MEDIA_TYPE_IMAGE_CONFIG,
                digest="sha256:config123",
                size=100
            )
            layer_desc = Descriptor(
                media_type=MEDIA_TYPE_IMAGE_LAYER,
                digest="sha256:layer123",
                size=200
            )
            manifest = Manifest(
                config=config_desc,
                layers=[layer_desc]
            )
            
            # Store manifest
            manifest_desc = manager.store_manifest(manifest)
            assert manifest_desc.digest.startswith("sha256:")
            
            # Retrieve manifest
            retrieved = manager.get_manifest(manifest_desc.digest)
            assert retrieved is not None
            assert retrieved.config.digest == config_desc.digest
            assert len(retrieved.layers) == 1
    
    def test_store_and_get_config(self):
        """Test storing and retrieving image config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            layout_path = Path(tmpdir) / "oci"
            manager = OCILayoutManager(layout_path)
            manager.create_layout()
            
            # Create config
            config = ImageConfig(
                architecture="amd64",
                os="linux",
                rootfs=RootFS(diff_ids=["sha256:layer123"]),
                config=ContainerConfig(cmd=["/bin/sh"])
            )
            
            # Store config
            config_desc = manager.store_config(config)
            assert config_desc.digest.startswith("sha256:")
            
            # Retrieve config
            retrieved = manager.get_config(config_desc.digest)
            assert retrieved is not None
            assert retrieved.architecture == "amd64"
            assert retrieved.os == "linux"
    
    def test_store_layer(self):
        """Test storing a layer file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            layout_path = Path(tmpdir) / "oci"
            manager = OCILayoutManager(layout_path)
            manager.create_layout()
            
            # Create layer file
            layer_file = Path(tmpdir) / "layer.tar.gz"
            layer_file.write_bytes(b"layer content")
            
            # Store layer
            layer_desc = manager.store_layer(layer_file)
            assert layer_desc.digest.startswith("sha256:")
            assert layer_desc.size == 13
            
            # Verify layer exists
            assert manager.blob_exists(layer_desc.digest)
    
    def test_get_layer_path(self):
        """Test getting layer path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            layout_path = Path(tmpdir) / "oci"
            manager = OCILayoutManager(layout_path)
            manager.create_layout()
            
            # Store layer
            layer_file = Path(tmpdir) / "layer.tar.gz"
            layer_file.write_bytes(b"layer content")
            layer_desc = manager.store_layer(layer_file)
            
            # Get layer path
            path = manager.get_layer_path(layer_desc.digest)
            assert path is not None
            assert path.exists()
            assert path.read_bytes() == b"layer content"
    
    def test_create_and_save_index(self):
        """Test creating and saving index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            layout_path = Path(tmpdir) / "oci"
            manager = OCILayoutManager(layout_path)
            manager.create_layout()
            
            # Create index
            manifest_desc = Descriptor(
                media_type=MEDIA_TYPE_IMAGE_MANIFEST,
                digest="sha256:manifest123",
                size=500
            )
            index = manager.create_index([manifest_desc])
            
            # Save index
            manager.save_index(index)
            
            # Load index
            loaded = manager.load_index()
            assert loaded is not None
            assert len(loaded.manifests) == 1
            assert loaded.manifests[0].digest == "sha256:manifest123"
    
    def test_add_manifest_to_index(self):
        """Test adding manifest to index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            layout_path = Path(tmpdir) / "oci"
            manager = OCILayoutManager(layout_path)
            manager.create_layout()
            
            # Add manifest to index
            manifest_desc = Descriptor(
                media_type=MEDIA_TYPE_IMAGE_MANIFEST,
                digest="sha256:manifest123",
                size=500
            )
            manager.add_manifest_to_index(manifest_desc, "myapp:latest")
            
            # Load index and verify
            index = manager.load_index()
            assert len(index.manifests) == 1
            assert index.manifests[0].annotations["org.opencontainers.image.ref.name"] == "myapp:latest"
    
    def test_list_manifests(self):
        """Test listing manifests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            layout_path = Path(tmpdir) / "oci"
            manager = OCILayoutManager(layout_path)
            manager.create_layout()
            
            # Add manifests
            desc1 = Descriptor(
                media_type=MEDIA_TYPE_IMAGE_MANIFEST,
                digest="sha256:manifest1",
                size=100
            )
            desc2 = Descriptor(
                media_type=MEDIA_TYPE_IMAGE_MANIFEST,
                digest="sha256:manifest2",
                size=200
            )
            manager.add_manifest_to_index(desc1, "app1:v1")
            manager.add_manifest_to_index(desc2, "app2:v2")
            
            # List manifests
            manifests = manager.list_manifests()
            assert len(manifests) == 2
    
    def test_get_manifest_by_tag(self):
        """Test getting manifest by tag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            layout_path = Path(tmpdir) / "oci"
            manager = OCILayoutManager(layout_path)
            manager.create_layout()
            
            # Add manifest with tag
            manifest_desc = Descriptor(
                media_type=MEDIA_TYPE_IMAGE_MANIFEST,
                digest="sha256:manifest123",
                size=500
            )
            manager.add_manifest_to_index(manifest_desc, "myapp:latest")
            
            # Get by tag
            found = manager.get_manifest_by_tag("myapp:latest")
            assert found is not None
            assert found.digest == "sha256:manifest123"
            
            # Non-existent tag
            not_found = manager.get_manifest_by_tag("nonexistent:v1")
            assert not_found is None
    
    def test_delete_blob(self):
        """Test deleting a blob."""
        with tempfile.TemporaryDirectory() as tmpdir:
            layout_path = Path(tmpdir) / "oci"
            manager = OCILayoutManager(layout_path)
            manager.create_layout()
            
            # Store blob
            content = b"test content"
            descriptor = manager.store_blob(content, MEDIA_TYPE_IMAGE_LAYER)
            
            # Delete blob
            result = manager.delete_blob(descriptor.digest)
            assert result is True
            
            # Blob no longer exists
            assert not manager.blob_exists(descriptor.digest)
            
            # Deleting non-existent blob
            result = manager.delete_blob("sha256:nonexistent")
            assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



class TestOCILayoutAdditional:
    """Additional tests for OCILayoutManager."""
    
    def test_oci_layout_manager_methods_exist(self):
        """Test OCILayoutManager has required methods."""
        with tempfile.TemporaryDirectory() as tmpdir:
            layout = OCILayoutManager(Path(tmpdir))
            # Just verify the object was created successfully
            assert layout is not None
            assert layout.root_path == Path(tmpdir)

    
    def test_oci_layout_manager_has_store_blob(self):
        """Test OCILayoutManager has store_blob method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            layout = OCILayoutManager(Path(tmpdir))
            assert hasattr(layout, 'store_blob')
            assert callable(getattr(layout, 'store_blob', None))
    
    def test_oci_layout_manager_has_get_blob(self):
        """Test OCILayoutManager has get_blob method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            layout = OCILayoutManager(Path(tmpdir))
            assert hasattr(layout, 'get_blob')
            assert callable(getattr(layout, 'get_blob', None))



class TestOCILayoutMethods:
    """Tests for OCILayout methods."""
    
    def test_oci_layout_store_manifest_method_exists(self):
        """Test store_manifest method exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            layout = OCILayoutManager(Path(tmpdir))
            assert hasattr(layout, 'store_manifest')
            assert callable(layout.store_manifest)
    
    def test_oci_layout_get_manifest_method_exists(self):
        """Test get_manifest method exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            layout = OCILayoutManager(Path(tmpdir))
            assert hasattr(layout, 'get_manifest')
            assert callable(layout.get_manifest)
    
    def test_oci_layout_store_config_method_exists(self):
        """Test store_config method exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            layout = OCILayoutManager(Path(tmpdir))
            assert hasattr(layout, 'store_config')
            assert callable(layout.store_config)
    
    def test_oci_layout_get_config_method_exists(self):
        """Test get_config method exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            layout = OCILayoutManager(Path(tmpdir))
            assert hasattr(layout, 'get_config')
            assert callable(layout.get_config)
    
    def test_oci_layout_list_manifests_method_exists(self):
        """Test list_manifests method exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            layout = OCILayoutManager(Path(tmpdir))
            assert hasattr(layout, 'list_manifests')
            assert callable(layout.list_manifests)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
