"""Tests for configuration management."""

import pytest
from pathlib import Path
import tempfile
import shutil
from derpy.core.config import (
    Config,
    ConfigManager,
    ConfigError,
    RegistryConfig,
    BuildSettings,
    serialize_config,
    deserialize_config,
)


class TestConfig:
    """Tests for Config model."""
    
    def test_create_default_config(self):
        """Test creating default configuration."""
        config = Config.default()
        assert config.images_path == Path("~/.derpy/images").expanduser()
        assert isinstance(config.build_settings, BuildSettings)
        assert len(config.registry_configs) == 0
    
    def test_config_to_dict(self):
        """Test config serialization to dict."""
        config = Config.default()
        data = config.to_dict()
        assert "images_path" in data
        assert "build_settings" in data
        assert "registry_configs" in data
    
    def test_config_from_dict(self):
        """Test config deserialization from dict."""
        data = {
            "images_path": "/tmp/test_images",
            "build_settings": {
                "default_platform": "linux/amd64",
                "max_layers": 127,
                "compression": "gzip",
                "parallel_builds": False
            },
            "registry_configs": {}
        }
        config = Config.from_dict(data)
        # Compare resolved paths since normalize_path resolves symlinks
        assert config.images_path.resolve() == Path("/tmp/test_images").resolve()
        assert config.build_settings.default_platform == "linux/amd64"


class TestRegistryConfig:
    """Tests for RegistryConfig model."""
    
    def test_create_registry_config(self):
        """Test creating registry configuration."""
        reg_config = RegistryConfig(
            url="https://registry.example.com",
            username="testuser",
            password="testpass"
        )
        assert reg_config.url == "https://registry.example.com"
        assert reg_config.username == "testuser"
        assert reg_config.insecure is False
    
    def test_registry_config_to_dict(self):
        """Test registry config serialization."""
        reg_config = RegistryConfig(
            url="https://registry.example.com",
            username="testuser"
        )
        data = reg_config.to_dict()
        assert data["url"] == "https://registry.example.com"
        assert data["username"] == "testuser"


class TestBuildSettings:
    """Tests for BuildSettings model."""
    
    def test_create_build_settings(self):
        """Test creating build settings."""
        settings = BuildSettings()
        assert settings.default_platform == "linux/amd64"
        assert settings.max_layers == 127
        assert settings.compression == "gzip"
        assert settings.parallel_builds is False
    
    def test_build_settings_custom(self):
        """Test creating custom build settings."""
        settings = BuildSettings(
            default_platform="linux/arm64",
            max_layers=100,
            compression="none"
        )
        assert settings.default_platform == "linux/arm64"
        assert settings.max_layers == 100
        assert settings.compression == "none"


class TestConfigSerialization:
    """Tests for config serialization."""
    
    def test_serialize_config(self):
        """Test serializing config to YAML."""
        config = Config.default()
        yaml_str = serialize_config(config)
        assert "images_path" in yaml_str
        assert "build_settings" in yaml_str
    
    def test_deserialize_config(self):
        """Test deserializing config from YAML."""
        yaml_str = """
images_path: /tmp/test_images
build_settings:
  default_platform: linux/amd64
  max_layers: 127
  compression: gzip
  parallel_builds: false
registry_configs: {}
"""
        config = deserialize_config(yaml_str)
        # Compare resolved paths since normalize_path resolves symlinks
        assert config.images_path.resolve() == Path("/tmp/test_images").resolve()
        assert config.build_settings.max_layers == 127
    
    def test_serialize_deserialize_roundtrip(self):
        """Test config serialization roundtrip."""
        original_config = Config.default()
        yaml_str = serialize_config(original_config)
        restored_config = deserialize_config(yaml_str)
        
        assert restored_config.build_settings.default_platform == original_config.build_settings.default_platform
        assert restored_config.build_settings.max_layers == original_config.build_settings.max_layers


class TestConfigManager:
    """Tests for ConfigManager."""
    
    def test_create_config_manager(self):
        """Test creating config manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            manager = ConfigManager(config_path)
            # Compare resolved paths since normalize_path resolves symlinks
            assert manager.config_path.resolve() == config_path.resolve()
    
    def test_load_config_creates_default(self):
        """Test loading config creates default if not exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            manager = ConfigManager(config_path)
            config = manager.load_config()
            
            assert config_path.exists()
            assert isinstance(config, Config)
    
    def test_save_and_load_config(self):
        """Test saving and loading config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            manager = ConfigManager(config_path)
            
            # Create and save config
            config = Config.default()
            manager.save_config(config)
            
            # Load config
            loaded_config = manager.load_config()
            assert loaded_config.build_settings.max_layers == config.build_settings.max_layers
    
    def test_update_images_path(self):
        """Test updating images path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            manager = ConfigManager(config_path)
            
            new_path = Path(tmpdir) / "new_images"
            manager.update_images_path(new_path)
            
            config = manager.get_config()
            # Compare resolved paths since normalize_path resolves symlinks
            assert config.images_path.resolve() == new_path.resolve()
    
    def test_add_registry(self):
        """Test adding registry configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            manager = ConfigManager(config_path)
            
            reg_config = RegistryConfig(
                url="https://registry.example.com",
                username="testuser"
            )
            manager.add_registry("myregistry", reg_config)
            
            config = manager.get_config()
            assert "myregistry" in config.registry_configs
            assert config.registry_configs["myregistry"].url == "https://registry.example.com"
    
    def test_remove_registry(self):
        """Test removing registry configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            manager = ConfigManager(config_path)
            
            # Add registry
            reg_config = RegistryConfig(url="https://registry.example.com")
            manager.add_registry("myregistry", reg_config)
            
            # Remove registry
            manager.remove_registry("myregistry")
            
            config = manager.get_config()
            assert "myregistry" not in config.registry_configs
    
    def test_update_build_settings(self):
        """Test updating build settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            manager = ConfigManager(config_path)
            
            manager.update_build_settings(max_layers=100, compression="none")
            
            config = manager.get_config()
            assert config.build_settings.max_layers == 100
            assert config.build_settings.compression == "none"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
