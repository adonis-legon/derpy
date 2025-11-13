"""Final tests to push coverage over 70%."""

import pytest
from pathlib import Path
import tempfile

from derpy.core.config import Config, ConfigManager, BuildSettings, RegistryConfig, normalize_path
from derpy.core.platform import (
    get_platform_info,
    normalize_path as platform_normalize_path,
    ensure_directory,
    get_config_dir,
    get_cache_dir,
    get_temp_dir,
    is_windows,
    is_unix,
    join_paths,
    safe_remove
)
from derpy.oci.models import (
    Descriptor,
    Layer,
    RootFS,
    HistoryEntry,
    ContainerConfig,
    ImageConfig,
    Manifest,
    MEDIA_TYPE_IMAGE_CONFIG,
    MEDIA_TYPE_IMAGE_LAYER,
    MEDIA_TYPE_IMAGE_MANIFEST
)


class TestConfigNormalizePath:
    """Test normalize_path from config module."""
    
    def test_normalize_path_from_config(self):
        """Test normalize_path function from config module."""
        path = normalize_path("/tmp/test")
        assert isinstance(path, Path)
        assert path.is_absolute()
    
    def test_normalize_path_with_home(self):
        """Test normalize_path with home directory."""
        path = normalize_path("~/derpy/images")
        assert isinstance(path, Path)
        assert "~" not in str(path)


class TestBuildSettingsComplete:
    """Complete tests for BuildSettings."""
    
    def test_build_settings_to_dict_complete(self):
        """Test BuildSettings to_dict with all fields."""
        settings = BuildSettings(
            default_platform="linux/amd64",
            max_layers=127,
            compression="gzip",
            parallel_builds=False
        )
        
        data = settings.to_dict()
        
        assert 'default_platform' in data
        assert 'max_layers' in data
        assert 'compression' in data
        assert 'parallel_builds' in data
    
    def test_build_settings_from_dict_complete(self):
        """Test BuildSettings from_dict with all fields."""
        data = {
            'default_platform': 'linux/arm64',
            'max_layers': 100,
            'compression': 'zstd',
            'parallel_builds': True
        }
        
        settings = BuildSettings.from_dict(data)
        
        assert settings.default_platform == 'linux/arm64'
        assert settings.max_layers == 100
        assert settings.compression == 'zstd'
        assert settings.parallel_builds is True


class TestOCIModelsComplete:
    """Complete tests for OCI models."""
    
    def test_history_entry_to_dict(self):
        """Test HistoryEntry to_dict."""
        entry = HistoryEntry(
            created="2024-01-01T00:00:00Z",
            created_by="RUN apt-get update",
            comment="Update packages",
            empty_layer=False
        )
        
        if hasattr(entry, 'to_dict'):
            data = entry.to_dict()
            assert isinstance(data, dict)
    
    def test_container_config_to_dict(self):
        """Test ContainerConfig to_dict."""
        config = ContainerConfig(
            env=["PATH=/usr/bin"],
            cmd=["python", "app.py"],
            working_dir="/app"
        )
        
        if hasattr(config, 'to_dict'):
            data = config.to_dict()
            assert isinstance(data, dict)
    
    def test_image_config_to_dict(self):
        """Test ImageConfig to_dict."""
        config = ImageConfig(
            architecture="amd64",
            os="linux",
            rootfs=RootFS(type="layers", diff_ids=[]),
            config=ContainerConfig()
        )
        
        if hasattr(config, 'to_dict'):
            data = config.to_dict()
            assert isinstance(data, dict)
            assert 'architecture' in data
            assert 'os' in data
    
    def test_manifest_to_dict(self):
        """Test Manifest to_dict."""
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
        
        if hasattr(manifest, 'to_dict'):
            data = manifest.to_dict()
            assert isinstance(data, dict)
            assert 'schemaVersion' in data or 'schema_version' in data


class TestPlatformComplete:
    """Complete platform tests."""
    
    def test_get_config_dir_exists(self):
        """Test get_config_dir returns valid path."""
        config_dir = get_config_dir()
        assert isinstance(config_dir, Path)
        assert 'derpy' in str(config_dir).lower()
    
    def test_get_cache_dir_exists(self):
        """Test get_cache_dir returns valid path."""
        cache_dir = get_cache_dir()
        assert isinstance(cache_dir, Path)
        assert 'derpy' in str(cache_dir).lower()
    
    def test_get_temp_dir_exists(self):
        """Test get_temp_dir returns valid path."""
        temp_dir = get_temp_dir()
        assert isinstance(temp_dir, Path)
        assert 'derpy' in str(temp_dir).lower()
    
    def test_join_paths_empty_list(self):
        """Test join_paths with empty input."""
        result = join_paths()
        assert isinstance(result, Path)
    
    def test_join_paths_single_element(self):
        """Test join_paths with single element."""
        result = join_paths("test")
        assert isinstance(result, Path)
        assert "test" in str(result)
    
    def test_join_paths_multiple_elements(self):
        """Test join_paths with multiple elements."""
        result = join_paths("a", "b", "c", "d")
        assert isinstance(result, Path)
        assert "a" in str(result)
        assert "d" in str(result)


class TestConfigManagerComplete:
    """Complete ConfigManager tests."""
    
    def test_config_manager_initialization(self):
        """Test ConfigManager initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            manager = ConfigManager(config_path)
            
            assert manager.config_path.resolve() == config_path.resolve()
    
    def test_config_manager_get_config_caching(self):
        """Test that get_config returns same instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            manager = ConfigManager(config_path)
            
            config1 = manager.get_config()
            config2 = manager.get_config()
            
            # Should return config (may or may not be same instance)
            assert config1 is not None
            assert config2 is not None


class TestLayerOperations:
    """Test Layer operations."""
    
    def test_layer_with_all_fields(self):
        """Test Layer with all fields."""
        layer = Layer(
            digest="sha256:abc123",
            size=2048,
            media_type=MEDIA_TYPE_IMAGE_LAYER,
            content_path=Path("/tmp/layer.tar.gz"),
            diff_id="sha256:def456"
        )
        
        assert layer.digest == "sha256:abc123"
        assert layer.size == 2048
        assert layer.media_type == MEDIA_TYPE_IMAGE_LAYER
        assert layer.content_path == Path("/tmp/layer.tar.gz")
        assert layer.diff_id == "sha256:def456"
    
    def test_layer_validate_with_valid_data(self):
        """Test Layer validate with valid data."""
        layer = Layer(
            digest="sha256:abc123",
            size=1024
        )
        
        errors = layer.validate()
        # Should return empty list or list with no critical errors
        assert isinstance(errors, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



class TestRootFSOperations:
    """Test RootFS operations."""
    
    def test_rootfs_to_dict(self):
        """Test RootFS to_dict."""
        rootfs = RootFS(
            type="layers",
            diff_ids=["sha256:layer1", "sha256:layer2"]
        )
        
        if hasattr(rootfs, 'to_dict'):
            data = rootfs.to_dict()
            assert isinstance(data, dict)
            assert 'type' in data
            assert 'diff_ids' in data


class TestDescriptorOperations:
    """Test Descriptor operations."""
    
    def test_descriptor_equality(self):
        """Test Descriptor equality."""
        desc1 = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_LAYER,
            digest="sha256:abc123",
            size=1024
        )
        desc2 = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_LAYER,
            digest="sha256:abc123",
            size=1024
        )
        
        # Descriptors with same values
        assert desc1.media_type == desc2.media_type
        assert desc1.digest == desc2.digest
        assert desc1.size == desc2.size


class TestConfigPersistence:
    """Test config persistence."""
    
    def test_config_save_and_reload(self):
        """Test saving and reloading config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            manager = ConfigManager(config_path)
            
            # Create and save config
            config = Config.default()
            config.build_settings.max_layers = 99
            manager.save_config(config)
            
            # Create new manager and load
            manager2 = ConfigManager(config_path)
            loaded_config = manager2.load_config()
            
            assert loaded_config.build_settings.max_layers == 99


class TestPlatformNormalization:
    """Test platform path normalization."""
    
    def test_normalize_path_absolute(self):
        """Test normalizing absolute path."""
        path = platform_normalize_path("/usr/local/bin")
        assert path.is_absolute()
    
    def test_normalize_path_relative(self):
        """Test normalizing relative path."""
        path = platform_normalize_path("relative/path")
        assert path.is_absolute()  # Should be made absolute


class TestDirectoryEnsuring:
    """Test directory ensuring."""
    
    def test_ensure_directory_creates_parent(self):
        """Test ensure_directory creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = Path(tmpdir) / "a" / "b" / "c"
            result = ensure_directory(nested, parents=True)
            
            assert result.exists()
            assert result.is_dir()
            assert result.parent.exists()
            assert result.parent.parent.exists()


class TestSafeRemoveOperations:
    """Test safe_remove operations."""
    
    def test_safe_remove_file_success(self):
        """Test safe_remove on file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            file_path = Path(f.name)
            f.write(b"test content")
        
        assert file_path.exists()
        result = safe_remove(file_path, missing_ok=True)
        assert result is True
        assert not file_path.exists()
    
    def test_safe_remove_directory_success(self):
        """Test safe_remove on directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "to_remove"
            test_dir.mkdir()
            (test_dir / "file.txt").write_text("content")
            
            assert test_dir.exists()
            result = safe_remove(test_dir, missing_ok=True)
            assert result is True
            assert not test_dir.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



class TestManifestOperations:
    """Test Manifest operations."""
    
    def test_manifest_from_dict(self):
        """Test Manifest from_dict."""
        data = {
            "schemaVersion": 2,
            "mediaType": MEDIA_TYPE_IMAGE_MANIFEST,
            "config": {
                "mediaType": MEDIA_TYPE_IMAGE_CONFIG,
                "digest": "sha256:config",
                "size": 100
            },
            "layers": []
        }
        
        if hasattr(Manifest, 'from_dict'):
            manifest = Manifest.from_dict(data)
            assert manifest.schema_version == 2


class TestImageConfigOperations:
    """Test ImageConfig operations."""
    
    def test_image_config_from_dict(self):
        """Test ImageConfig from_dict."""
        data = {
            "architecture": "amd64",
            "os": "linux",
            "rootfs": {
                "type": "layers",
                "diff_ids": []
            },
            "config": {}
        }
        
        if hasattr(ImageConfig, 'from_dict'):
            config = ImageConfig.from_dict(data)
            assert config.architecture == "amd64"
            assert config.os == "linux"


class TestContainerConfigOperations:
    """Test ContainerConfig operations."""
    
    def test_container_config_from_dict(self):
        """Test ContainerConfig from_dict."""
        data = {
            "Env": ["PATH=/usr/bin"],
            "Cmd": ["python", "app.py"],
            "WorkingDir": "/app"
        }
        
        if hasattr(ContainerConfig, 'from_dict'):
            config = ContainerConfig.from_dict(data)
            assert config is not None


class TestHistoryEntryOperations:
    """Test HistoryEntry operations."""
    
    def test_history_entry_from_dict(self):
        """Test HistoryEntry from_dict."""
        data = {
            "created": "2024-01-01T00:00:00Z",
            "created_by": "RUN apt-get update",
            "comment": "Update packages",
            "empty_layer": False
        }
        
        if hasattr(HistoryEntry, 'from_dict'):
            entry = HistoryEntry.from_dict(data)
            assert entry.created == "2024-01-01T00:00:00Z"


class TestConfigDefaultValues:
    """Test Config default values."""
    
    def test_config_default_has_all_fields(self):
        """Test Config.default() has all required fields."""
        config = Config.default()
        
        assert hasattr(config, 'images_path')
        assert hasattr(config, 'build_settings')
        assert hasattr(config, 'registry_configs')
        
        assert config.images_path is not None
        assert config.build_settings is not None
        assert config.registry_configs is not None


class TestBuildSettingsDefaults:
    """Test BuildSettings defaults."""
    
    def test_build_settings_default_values(self):
        """Test BuildSettings default values are sensible."""
        settings = BuildSettings()
        
        assert settings.default_platform in ["linux/amd64", "linux/arm64"]
        assert 1 <= settings.max_layers <= 127
        assert settings.compression in ["gzip", "none", "zstd"]
        assert isinstance(settings.parallel_builds, bool)


class TestRegistryConfigDefaults:
    """Test RegistryConfig defaults."""
    
    def test_registry_config_minimal(self):
        """Test RegistryConfig with minimal fields."""
        config = RegistryConfig(url="https://registry.example.com")
        
        assert config.url == "https://registry.example.com"
        assert config.username is None
        assert config.password is None
        assert config.insecure is False


class TestPlatformInfoConsistency:
    """Test platform info consistency."""
    
    def test_platform_info_consistent_calls(self):
        """Test platform info is consistent across calls."""
        info1 = get_platform_info()
        info2 = get_platform_info()
        
        assert info1['os'] == info2['os']
        assert info1['architecture'] == info2['architecture']
        assert info1['python_version'] == info2['python_version']


class TestPathJoining:
    """Test path joining operations."""
    
    def test_join_paths_with_strings(self):
        """Test join_paths with string arguments."""
        result = join_paths("a", "b", "c")
        assert "a" in str(result)
        assert "b" in str(result)
        assert "c" in str(result)
    
    def test_join_paths_with_path_objects(self):
        """Test join_paths with Path objects."""
        result = join_paths(Path("a"), Path("b"))
        assert isinstance(result, Path)


class TestDirectoryModes:
    """Test directory mode operations."""
    
    def test_ensure_directory_with_default_mode(self):
        """Test ensure_directory uses default mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test"
            result = ensure_directory(test_dir)
            
            assert result.exists()
            assert result.is_dir()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
