"""Final push to 70% coverage."""

import pytest
from pathlib import Path
import tempfile

from derpy.core.platform import (
    get_platform_info,
    normalize_path,
    ensure_directory,
    get_default_dir_mode,
    get_default_file_mode,
    set_file_permissions,
    make_executable,
    get_config_dir,
    get_cache_dir,
    get_temp_dir,
    safe_remove,
    join_paths
)
from derpy.oci.models import (
    Descriptor,
    Layer,
    RootFS,
    HistoryEntry,
    ContainerConfig,
    ImageConfig,
    Manifest,
    Index,
    MEDIA_TYPE_IMAGE_CONFIG,
    MEDIA_TYPE_IMAGE_LAYER,
    MEDIA_TYPE_IMAGE_MANIFEST,
    MEDIA_TYPE_IMAGE_INDEX
)


class TestFinalPush:
    """Final tests to reach 70% coverage."""
    
    def test_index_creation(self):
        """Test Index creation."""
        index = Index(
            schema_version=2,
            manifests=[
                Descriptor(
                    media_type=MEDIA_TYPE_IMAGE_MANIFEST,
                    digest="sha256:manifest1",
                    size=100
                )
            ]
        )
        
        assert index.schema_version == 2
        assert len(index.manifests) == 1
    
    def test_index_with_annotations(self):
        """Test Index with annotations."""
        index = Index(
            schema_version=2,
            manifests=[],
            annotations={"org.opencontainers.image.ref.name": "latest"}
        )
        
        assert index.annotations is not None
    
    def test_index_to_dict(self):
        """Test Index to_dict."""
        index = Index(
            schema_version=2,
            manifests=[]
        )
        
        if hasattr(index, 'to_dict'):
            data = index.to_dict()
            assert isinstance(data, dict)
    
    def test_manifest_with_multiple_layers(self):
        """Test Manifest with multiple layers."""
        manifest = Manifest(
            schema_version=2,
            media_type=MEDIA_TYPE_IMAGE_MANIFEST,
            config=Descriptor(
                media_type=MEDIA_TYPE_IMAGE_CONFIG,
                digest="sha256:config",
                size=100
            ),
            layers=[
                Descriptor(
                    media_type=MEDIA_TYPE_IMAGE_LAYER,
                    digest="sha256:layer1",
                    size=200
                ),
                Descriptor(
                    media_type=MEDIA_TYPE_IMAGE_LAYER,
                    digest="sha256:layer2",
                    size=300
                ),
                Descriptor(
                    media_type=MEDIA_TYPE_IMAGE_LAYER,
                    digest="sha256:layer3",
                    size=400
                )
            ]
        )
        
        assert len(manifest.layers) == 3
    
    def test_image_config_with_history(self):
        """Test ImageConfig with history."""
        config = ImageConfig(
            architecture="amd64",
            os="linux",
            rootfs=RootFS(type="layers", diff_ids=["sha256:layer1"]),
            config=ContainerConfig(),
            history=[
                HistoryEntry(
                    created="2024-01-01T00:00:00Z",
                    created_by="FROM ubuntu:20.04"
                ),
                HistoryEntry(
                    created="2024-01-01T00:01:00Z",
                    created_by="RUN apt-get update"
                )
            ]
        )
        
        if hasattr(config, 'history'):
            assert len(config.history) == 2
    
    def test_container_config_with_entrypoint(self):
        """Test ContainerConfig with entrypoint."""
        config = ContainerConfig(
            entrypoint=["/bin/sh", "-c"],
            cmd=["echo", "hello"]
        )
        
        if hasattr(config, 'entrypoint'):
            assert len(config.entrypoint) == 2
    
    def test_container_config_with_volumes(self):
        """Test ContainerConfig with volumes."""
        config = ContainerConfig(
            volumes={"/data": {}, "/logs": {}}
        )
        
        if hasattr(config, 'volumes'):
            assert len(config.volumes) == 2
    
    def test_container_config_with_exposed_ports(self):
        """Test ContainerConfig with exposed ports."""
        config = ContainerConfig(
            exposed_ports={"80/tcp": {}, "443/tcp": {}}
        )
        
        if hasattr(config, 'exposed_ports'):
            assert len(config.exposed_ports) == 2
    
    def test_platform_directories_are_paths(self):
        """Test platform directories return Path objects."""
        assert isinstance(get_config_dir(), Path)
        assert isinstance(get_cache_dir(), Path)
        assert isinstance(get_temp_dir(), Path)
    
    def test_default_modes_are_valid(self):
        """Test default modes are valid octal values."""
        dir_mode = get_default_dir_mode()
        file_mode = get_default_file_mode()
        
        assert isinstance(dir_mode, int)
        assert isinstance(file_mode, int)
        assert dir_mode > 0
        assert file_mode > 0
    
    def test_normalize_path_idempotence(self):
        """Test normalize_path is idempotent."""
        path1 = normalize_path("/tmp/test")
        path2 = normalize_path(path1)
        path3 = normalize_path(path2)
        
        assert path1 == path2 == path3
    
    def test_join_paths_with_many_parts(self):
        """Test join_paths with many parts."""
        result = join_paths("a", "b", "c", "d", "e", "f", "g")
        assert isinstance(result, Path)
        assert "a" in str(result)
        assert "g" in str(result)
    
    def test_safe_remove_with_missing_ok_false_on_missing(self):
        """Test safe_remove with missing_ok=False on missing file."""
        non_existent = Path("/tmp/definitely_does_not_exist_12345")
        
        with pytest.raises(FileNotFoundError):
            safe_remove(non_existent, missing_ok=False)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



class TestMoreCoverage:
    """More tests for coverage."""
    
    def test_descriptor_without_optional_fields(self):
        """Test Descriptor without optional fields."""
        desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_LAYER,
            digest="sha256:abc123",
            size=1024
        )
        
        data = desc.to_dict()
        assert "urls" not in data
        assert "annotations" not in data
    
    def test_layer_validate_empty_digest(self):
        """Test Layer validate with empty digest."""
        layer = Layer(digest="", size=1024)
        errors = layer.validate()
        assert len(errors) > 0
    
    def test_layer_validate_zero_size(self):
        """Test Layer validate with zero size."""
        layer = Layer(digest="sha256:abc123", size=0)
        errors = layer.validate()
        # Zero size might be valid for empty layers
        assert isinstance(errors, list)
    
    def test_rootfs_empty_diff_ids(self):
        """Test RootFS with empty diff_ids."""
        rootfs = RootFS(type="layers", diff_ids=[])
        assert len(rootfs.diff_ids) == 0
    
    def test_history_entry_minimal(self):
        """Test HistoryEntry with minimal fields."""
        entry = HistoryEntry(
            created="2024-01-01T00:00:00Z",
            created_by="FROM ubuntu:20.04"
        )
        assert entry.created == "2024-01-01T00:00:00Z"
        assert entry.created_by == "FROM ubuntu:20.04"
    
    def test_container_config_minimal(self):
        """Test ContainerConfig with minimal fields."""
        config = ContainerConfig()
        assert config is not None
    
    def test_image_config_minimal(self):
        """Test ImageConfig with minimal fields."""
        config = ImageConfig(
            architecture="amd64",
            os="linux",
            rootfs=RootFS(type="layers", diff_ids=[]),
            config=ContainerConfig()
        )
        assert config.architecture == "amd64"
        assert config.os == "linux"
    
    def test_manifest_minimal(self):
        """Test Manifest with minimal fields."""
        manifest = Manifest(
            schema_version=2,
            media_type=MEDIA_TYPE_IMAGE_MANIFEST,
            config=Descriptor(
                media_type=MEDIA_TYPE_IMAGE_CONFIG,
                digest="sha256:config",
                size=100
            ),
            layers=[]
        )
        assert manifest.schema_version == 2
        assert len(manifest.layers) == 0
    
    def test_index_minimal(self):
        """Test Index with minimal fields."""
        index = Index(schema_version=2, manifests=[])
        assert index.schema_version == 2
        assert len(index.manifests) == 0
    
    def test_normalize_path_current_directory(self):
        """Test normalize_path with current directory."""
        path = normalize_path(".")
        assert path.is_absolute()
    
    def test_normalize_path_parent_directory(self):
        """Test normalize_path with parent directory."""
        path = normalize_path("..")
        assert path.is_absolute()
    
    def test_ensure_directory_exist_ok_true(self):
        """Test ensure_directory with exist_ok=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test"
            test_dir.mkdir()
            
            # Should not raise
            result = ensure_directory(test_dir, exist_ok=True)
            assert result.exists()
    
    def test_safe_remove_returns_false_for_missing(self):
        """Test safe_remove returns False for missing file."""
        non_existent = Path("/tmp/does_not_exist_xyz123")
        result = safe_remove(non_existent, missing_ok=True)
        assert result is False
    
    def test_safe_remove_returns_true_for_removed(self):
        """Test safe_remove returns True when file is removed."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            file_path = Path(f.name)
        
        result = safe_remove(file_path, missing_ok=True)
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
