"""Configuration management for derpy container tool."""

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Optional, Any
import yaml

from derpy.core.platform import normalize_path, ensure_directory, get_config_dir
from derpy.core.exceptions import ConfigError, ConfigParseError, ConfigValidationError


@dataclass
class RegistryConfig:
    """Configuration for a container registry."""
    
    url: str
    username: Optional[str] = None
    password: Optional[str] = None
    insecure: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RegistryConfig":
        """Create from dictionary during YAML deserialization."""
        return cls(**data)


@dataclass
class BuildSettings:
    """Build configuration settings."""
    
    default_platform: str = "linux/amd64"
    max_layers: int = 127
    compression: str = "gzip"
    parallel_builds: bool = False
    enable_isolation: bool = True
    base_image_cache_dir: str = "~/.derpy/cache/base-images"
    chroot_timeout: int = 600  # 10 minutes - enough for apt-get/apk operations
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BuildSettings":
        """Create from dictionary during YAML deserialization."""
        return cls(**data)


@dataclass
class Config:
    """Main configuration for derpy."""
    
    images_path: Path
    registry_configs: Dict[str, RegistryConfig] = field(default_factory=dict)
    build_settings: BuildSettings = field(default_factory=BuildSettings)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            "images_path": str(self.images_path),
            "registry_configs": {
                name: config.to_dict() 
                for name, config in self.registry_configs.items()
            },
            "build_settings": self.build_settings.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create from dictionary during YAML deserialization."""
        images_path = normalize_path(data.get("images_path", "~/.derpy/images"))
        
        registry_configs = {}
        for name, reg_data in data.get("registry_configs", {}).items():
            registry_configs[name] = RegistryConfig.from_dict(reg_data)
        
        build_settings_data = data.get("build_settings", {})
        build_settings = BuildSettings.from_dict(build_settings_data)
        
        return cls(
            images_path=images_path,
            registry_configs=registry_configs,
            build_settings=build_settings
        )
    
    @classmethod
    def default(cls) -> "Config":
        """Create default configuration."""
        config_dir = get_config_dir()
        return cls(
            images_path=config_dir / "images",
            registry_configs={},
            build_settings=BuildSettings()
        )


def serialize_config(config: Config) -> str:
    """
    Serialize configuration to YAML string.
    
    Args:
        config: Configuration object to serialize
        
    Returns:
        YAML string representation
        
    Raises:
        ConfigError: If serialization fails
    """
    try:
        return yaml.dump(config.to_dict(), default_flow_style=False, sort_keys=False)
    except Exception as e:
        raise ConfigError(f"Failed to serialize configuration: {e}")


def deserialize_config(yaml_content: str) -> Config:
    """
    Deserialize configuration from YAML string.
    
    Args:
        yaml_content: YAML string to deserialize
        
    Returns:
        Configuration object
        
    Raises:
        ConfigError: If deserialization fails or YAML is invalid
    """
    try:
        data = yaml.safe_load(yaml_content)
        if data is None:
            data = {}
        return Config.from_dict(data)
    except yaml.YAMLError as e:
        raise ConfigParseError("config", cause=e)
    except Exception as e:
        raise ConfigError(f"Failed to deserialize configuration: {e}", cause=e)


class ConfigManager:
    """Manages configuration file operations for derpy."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize ConfigManager.
        
        Args:
            config_path: Path to configuration file. Defaults to platform-specific config directory
        """
        if config_path is None:
            config_path = get_config_dir() / "config.yaml"
        self.config_path = normalize_path(config_path)
        self._config: Optional[Config] = None
    
    def _ensure_config_directory(self) -> None:
        """Create configuration directory if it doesn't exist."""
        try:
            ensure_directory(self.config_path.parent)
        except Exception as e:
            raise ConfigError(
                f"Failed to create configuration directory {self.config_path.parent}: {e}"
            )
    
    def _ensure_images_directory(self, config: Config) -> None:
        """Create images directory if it doesn't exist."""
        try:
            ensure_directory(config.images_path)
        except Exception as e:
            raise ConfigError(
                f"Failed to create images directory {config.images_path}: {e}"
            )
    
    def load_config(self) -> Config:
        """
        Load configuration from file.
        
        If the configuration file doesn't exist, creates a default configuration
        and saves it to the file.
        
        Returns:
            Configuration object
            
        Raises:
            ConfigError: If loading or validation fails
        """
        if not self.config_path.exists():
            # Create default configuration
            config = Config.default()
            self.save_config(config)
            return config
        
        try:
            yaml_content = self.config_path.read_text()
            config = deserialize_config(yaml_content)
            self._validate_config(config)
            self._ensure_images_directory(config)
            self._config = config
            return config
        except ConfigError:
            raise
        except Exception as e:
            raise ConfigError(f"Failed to load configuration from {self.config_path}: {e}")
    
    def save_config(self, config: Config) -> None:
        """
        Save configuration to file.
        
        Args:
            config: Configuration object to save
            
        Raises:
            ConfigError: If saving fails
        """
        try:
            self._validate_config(config)
            self._ensure_config_directory()
            self._ensure_images_directory(config)
            
            yaml_content = serialize_config(config)
            self.config_path.write_text(yaml_content)
            self._config = config
        except ConfigError:
            raise
        except Exception as e:
            raise ConfigError(f"Failed to save configuration to {self.config_path}: {e}")
    
    def _validate_config(self, config: Config) -> None:
        """
        Validate configuration object.
        
        Args:
            config: Configuration to validate
            
        Raises:
            ConfigError: If validation fails
        """
        if not isinstance(config.images_path, Path):
            raise ConfigError("images_path must be a Path object")
        
        if not isinstance(config.registry_configs, dict):
            raise ConfigError("registry_configs must be a dictionary")
        
        if not isinstance(config.build_settings, BuildSettings):
            raise ConfigError("build_settings must be a BuildSettings object")
        
        # Validate build settings
        if config.build_settings.max_layers < 1 or config.build_settings.max_layers > 127:
            raise ConfigError("max_layers must be between 1 and 127")
        
        if config.build_settings.compression not in ["gzip", "none"]:
            raise ConfigError("compression must be 'gzip' or 'none'")
        
        if not isinstance(config.build_settings.enable_isolation, bool):
            raise ConfigError("enable_isolation must be a boolean")
        
        if not isinstance(config.build_settings.base_image_cache_dir, str):
            raise ConfigError("base_image_cache_dir must be a string")
        
        if config.build_settings.chroot_timeout < 1:
            raise ConfigError("chroot_timeout must be at least 1 second")
        
        # Validate registry configs
        for name, reg_config in config.registry_configs.items():
            if not isinstance(reg_config, RegistryConfig):
                raise ConfigError(f"Invalid registry config for '{name}'")
            if not reg_config.url:
                raise ConfigError(f"Registry '{name}' must have a URL")
    
    def get_config(self) -> Config:
        """
        Get current configuration.
        
        Loads from file if not already loaded.
        
        Returns:
            Configuration object
        """
        if self._config is None:
            return self.load_config()
        return self._config
    
    def update_images_path(self, path: Path) -> None:
        """
        Update images path in configuration.
        
        Args:
            path: New images path
            
        Raises:
            ConfigError: If update fails
        """
        config = self.get_config()
        config.images_path = normalize_path(path)
        self.save_config(config)
    
    def add_registry(self, name: str, registry_config: RegistryConfig) -> None:
        """
        Add or update registry configuration.
        
        Args:
            name: Registry name
            registry_config: Registry configuration
            
        Raises:
            ConfigError: If update fails
        """
        config = self.get_config()
        config.registry_configs[name] = registry_config
        self.save_config(config)
    
    def remove_registry(self, name: str) -> None:
        """
        Remove registry configuration.
        
        Args:
            name: Registry name to remove
            
        Raises:
            ConfigError: If registry doesn't exist or removal fails
        """
        config = self.get_config()
        if name not in config.registry_configs:
            raise ConfigError(f"Registry '{name}' not found in configuration")
        del config.registry_configs[name]
        self.save_config(config)
    
    def update_build_settings(self, **kwargs: Any) -> None:
        """
        Update build settings.
        
        Args:
            **kwargs: Build settings to update
            
        Raises:
            ConfigError: If update fails
        """
        config = self.get_config()
        for key, value in kwargs.items():
            if hasattr(config.build_settings, key):
                setattr(config.build_settings, key, value)
            else:
                raise ConfigError(f"Unknown build setting: {key}")
        self.save_config(config)
