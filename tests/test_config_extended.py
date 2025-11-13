"""Extended tests for configuration management."""

import pytest
from pathlib import Path
import tempfile
from derpy.core.config import (
    Config,
    ConfigManager,
    RegistryConfig,
    BuildSettings,
    normalize_path
)


class TestNormalizePath:
    """Tests for normalize_path function."""
    
    def test_normalize_path_string(self):
        """Test normalizing string path."""
        result = normalize_path("/tmp/test")
        assert isinstance(result, Path)
    
    def test_normalize_path_with_tilde(self):
        """Test normalizing path with tilde."""
        result = normalize_path("~/test")
        assert isinstance(result, Path)
        assert "~" not in str(result)
    
    def test_normalize_path_relative(self):
        """Test normalizing relative path."""
        result = normalize_path("test/path")
        assert isinstance(result, Path)


class TestConfigDefaults:
    """Tests for Config default values."""
    
    def test_config_default_images_path(self):
        """Test default images path."""
        config = Config.default()
        assert config.images_path is not None
        assert isinstance(config.images_path, Path)
    
    def test_config_default_build_settings(self):
        """Test default build settings."""
        config = Config.default()
        assert config.build_settings is not None
        assert config.build_settings.default_platform == "linux/amd64"
        assert config.build_settings.max_layers == 127
    
    def test_config_default_registry_configs(self):
        """Test default registry configs."""
        config = Config.default()
        assert config.registry_configs is not None
        assert isinstance(config.registry_configs, dict)


class TestRegistryConfigValidation:
    """Tests for RegistryConfig validation."""
    
    def test_registry_config_url_required(self):
        """Test that URL is required."""
        config = RegistryConfig(url="https://registry.example.com")
        assert config.url == "https://registry.example.com"
    
    def test_registry_config_optional_fields(self):
        """Test optional fields."""
        config = RegistryConfig(url="https://registry.example.com")
        assert config.username is None
        assert config.password is None
        assert config.insecure is False
    
    def test_registry_config_with_all_fields(self):
        """Test with all fields."""
        config = RegistryConfig(
            url="https://registry.example.com",
            username="user",
            password="pass",
            insecure=True
        )
        assert config.url == "https://registry.example.com"
        assert config.username == "user"
        assert config.password == "pass"
        assert config.insecure is True


class TestBuildSettingsValidation:
    """Tests for BuildSettings validation."""
    
    def test_build_settings_defaults(self):
        """Test default build settings."""
        settings = BuildSettings()
        assert settings.default_platform == "linux/amd64"
        assert settings.max_layers == 127
        assert settings.compression == "gzip"
        assert settings.parallel_builds is False
    
    def test_build_settings_custom_platform(self):
        """Test custom platform."""
        settings = BuildSettings(default_platform="linux/arm64")
        assert settings.default_platform == "linux/arm64"
    
    def test_build_settings_custom_max_layers(self):
        """Test custom max layers."""
        settings = BuildSettings(max_layers=50)
        assert settings.max_layers == 50
    
    def test_build_settings_custom_compression(self):
        """Test custom compression."""
        settings = BuildSettings(compression="none")
        assert settings.compression == "none"
    
    def test_build_settings_parallel_builds(self):
        """Test parallel builds setting."""
        settings = BuildSettings(parallel_builds=True)
        assert settings.parallel_builds is True


class TestConfigManagerPersistence:
    """Tests for ConfigManager persistence."""
    
    def test_config_persists_after_save(self):
        """Test that config persists after save."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            manager = ConfigManager(config_path)
            
            # Create and save config
            config = Config.default()
            manager.save_config(config)
            
            # Create new manager and load
            manager2 = ConfigManager(config_path)
            loaded_config = manager2.load_config()
            
            assert loaded_config.build_settings.max_layers == config.build_settings.max_layers
    
    def test_config_updates_persist(self):
        """Test that config updates persist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            manager = ConfigManager(config_path)
            
            # Update setting
            manager.update_build_settings(max_layers=100)
            
            # Create new manager and verify
            manager2 = ConfigManager(config_path)
            config = manager2.load_config()
            
            assert config.build_settings.max_layers == 100


class TestConfigManagerRegistryOperations:
    """Tests for ConfigManager registry operations."""
    
    def test_add_multiple_registries(self):
        """Test adding multiple registries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            manager = ConfigManager(config_path)
            
            # Add multiple registries
            manager.add_registry("reg1", RegistryConfig(url="https://reg1.com"))
            manager.add_registry("reg2", RegistryConfig(url="https://reg2.com"))
            
            config = manager.get_config()
            assert len(config.registry_configs) == 2
            assert "reg1" in config.registry_configs
            assert "reg2" in config.registry_configs
    
    def test_remove_nonexistent_registry(self):
        """Test removing non-existent registry raises error."""
        from derpy.core.exceptions import ConfigError
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            manager = ConfigManager(config_path)
            
            # Should raise ConfigError
            with pytest.raises(ConfigError):
                manager.remove_registry("nonexistent")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



class TestConfigSerialization:
    """Tests for config serialization."""
    
    def test_config_to_dict_includes_all_fields(self):
        """Test that to_dict includes all fields."""
        config = Config.default()
        data = config.to_dict()
        
        assert "images_path" in data
        assert "build_settings" in data
        assert "registry_configs" in data
    
    def test_config_from_dict_creates_valid_config(self):
        """Test that from_dict creates valid config."""
        data = {
            "images_path": "/tmp/images",
            "build_settings": {
                "default_platform": "linux/amd64",
                "max_layers": 127,
                "compression": "gzip",
                "parallel_builds": False
            },
            "registry_configs": {}
        }
        config = Config.from_dict(data)
        
        assert config is not None
        assert config.build_settings.default_platform == "linux/amd64"


class TestRegistryConfigSerialization:
    """Tests for RegistryConfig serialization."""
    
    def test_registry_config_to_dict_includes_all_fields(self):
        """Test that to_dict includes all fields."""
        config = RegistryConfig(
            url="https://registry.example.com",
            username="user",
            password="pass",
            insecure=True
        )
        data = config.to_dict()
        
        assert "url" in data
        assert "username" in data
        assert "password" in data
        assert "insecure" in data
    
    def test_registry_config_from_dict_creates_valid_config(self):
        """Test that from_dict creates valid config."""
        data = {
            "url": "https://registry.example.com",
            "username": "user",
            "password": "pass",
            "insecure": True
        }
        config = RegistryConfig.from_dict(data)
        
        assert config.url == "https://registry.example.com"
        assert config.username == "user"
        assert config.insecure is True


class TestBuildSettingsSerialization:
    """Tests for BuildSettings serialization."""
    
    def test_build_settings_to_dict(self):
        """Test BuildSettings to_dict."""
        settings = BuildSettings(
            default_platform="linux/arm64",
            max_layers=100,
            compression="none",
            parallel_builds=True
        )
        data = settings.to_dict()
        
        assert data["default_platform"] == "linux/arm64"
        assert data["max_layers"] == 100
        assert data["compression"] == "none"
        assert data["parallel_builds"] is True
    
    def test_build_settings_from_dict(self):
        """Test BuildSettings from_dict."""
        data = {
            "default_platform": "linux/arm64",
            "max_layers": 100,
            "compression": "none",
            "parallel_builds": True
        }
        settings = BuildSettings.from_dict(data)
        
        assert settings.default_platform == "linux/arm64"
        assert settings.max_layers == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



class TestConfigManagerEdgeCases:
    """Edge case tests for ConfigManager."""
    
    def test_config_manager_get_config_creates_if_missing(self):
        """Test get_config creates config if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            manager = ConfigManager(config_path)
            
            config = manager.get_config()
            assert config is not None
            assert config_path.exists()
    
    def test_config_manager_update_images_path_creates_dir(self):
        """Test update_images_path creates directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            manager = ConfigManager(config_path)
            
            new_path = Path(tmpdir) / "new_images"
            manager.update_images_path(new_path)
            
            config = manager.get_config()
            assert config.images_path.resolve() == new_path.resolve()
    
    def test_config_manager_add_registry_overwrites(self):
        """Test adding registry with same name overwrites."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            manager = ConfigManager(config_path)
            
            # Add first registry
            reg1 = RegistryConfig(url="https://reg1.com")
            manager.add_registry("test", reg1)
            
            # Add second with same name
            reg2 = RegistryConfig(url="https://reg2.com")
            manager.add_registry("test", reg2)
            
            config = manager.get_config()
            assert config.registry_configs["test"].url == "https://reg2.com"


class TestBuildSettingsEdgeCases:
    """Edge case tests for BuildSettings."""
    
    def test_build_settings_max_layers_boundary(self):
        """Test max_layers at boundary value."""
        settings = BuildSettings(max_layers=1)
        assert settings.max_layers == 1
        
        settings = BuildSettings(max_layers=127)
        assert settings.max_layers == 127
    
    def test_build_settings_compression_options(self):
        """Test different compression options."""
        for compression in ["gzip", "none", "zstd"]:
            settings = BuildSettings(compression=compression)
            assert settings.compression == compression


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



class TestConfigManagerAdvanced:
    """Advanced tests for ConfigManager."""
    
    def test_config_manager_load_creates_default(self):
        """Test that load_config creates default if file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "new_config.yaml"
            manager = ConfigManager(config_path)
            
            config = manager.load_config()
            
            assert config is not None
            assert config_path.exists()
    
    def test_config_manager_save_creates_directory(self):
        """Test that save_config creates directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "subdir" / "config.yaml"
            manager = ConfigManager(config_path)
            
            config = Config.default()
            manager.save_config(config)
            
            assert config_path.exists()
            assert config_path.parent.exists()
    
    def test_config_manager_update_build_settings_multiple(self):
        """Test updating multiple build settings at once."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            manager = ConfigManager(config_path)
            
            manager.update_build_settings(
                max_layers=50,
                compression="none",
                parallel_builds=True
            )
            
            config = manager.get_config()
            assert config.build_settings.max_layers == 50
            assert config.build_settings.compression == "none"
            assert config.build_settings.parallel_builds is True


class TestRegistryConfigAdvanced:
    """Advanced tests for RegistryConfig."""
    
    def test_registry_config_without_credentials(self):
        """Test RegistryConfig without credentials."""
        config = RegistryConfig(url="https://registry.example.com")
        
        assert config.username is None
        assert config.password is None
    
    def test_registry_config_with_only_username(self):
        """Test RegistryConfig with only username."""
        config = RegistryConfig(
            url="https://registry.example.com",
            username="user"
        )
        
        assert config.username == "user"
        assert config.password is None
    
    def test_registry_config_serialization_with_credentials(self):
        """Test RegistryConfig serialization includes credentials."""
        config = RegistryConfig(
            url="https://registry.example.com",
            username="user",
            password="secret"
        )
        
        data = config.to_dict()
        
        assert data['username'] == "user"
        assert data['password'] == "secret"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
