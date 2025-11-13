"""Tests for custom exceptions."""

import pytest

from derpy.core.exceptions import (
    DerpyError,
    ConfigError,
    ConfigFileNotFoundError,
    ConfigValidationError,
    ConfigParseError,
    BuildError,
    DockerfileNotFoundError,
    DockerfileSyntaxError,
    UnsupportedInstructionError,
    BuildContextError,
    CommandExecutionError,
    LayerCreationError,
    StorageError,
    ImageNotFoundError,
    ImageValidationError,
    RepositoryError,
    BlobNotFoundError,
    DiskSpaceError,
    RegistryError,
    RegistryConnectionError,
    RegistryAuthenticationError,
    RegistryNotFoundError,
    ImagePushError,
    ImagePullError,
    PlatformError,
    UnsupportedPlatformError,
    ValidationError,
    InvalidTagError,
    InvalidPathError,
    InvalidArgumentError
)


class TestDerpyError:
    """Tests for base DerpyError class."""
    
    def test_derpy_error_basic(self):
        """Test basic DerpyError creation."""
        error = DerpyError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.remediation is None
        assert error.cause is None
    
    def test_derpy_error_with_remediation(self):
        """Test DerpyError with remediation."""
        error = DerpyError("Test error", remediation="Try this fix")
        assert "Test error" in str(error)
        assert "Try this fix" in str(error)
        assert error.remediation == "Try this fix"
    
    def test_derpy_error_with_cause(self):
        """Test DerpyError with cause."""
        cause = ValueError("Original error")
        error = DerpyError("Test error", cause=cause)
        assert "Test error" in str(error)
        assert "ValueError" in str(error)
        assert error.cause is cause
    
    def test_derpy_error_with_all_params(self):
        """Test DerpyError with all parameters."""
        cause = ValueError("Original error")
        error = DerpyError("Test error", remediation="Fix it", cause=cause)
        assert "Test error" in str(error)
        assert "Fix it" in str(error)
        assert "ValueError" in str(error)


class TestConfigErrors:
    """Tests for configuration errors."""
    
    def test_config_error(self):
        """Test ConfigError."""
        error = ConfigError("Config problem")
        assert isinstance(error, DerpyError)
        assert "Config problem" in str(error)
    
    def test_config_file_not_found_error(self):
        """Test ConfigFileNotFoundError."""
        error = ConfigFileNotFoundError("/path/to/config.yaml")
        assert isinstance(error, ConfigError)
        assert "/path/to/config.yaml" in str(error)
        assert error.remediation is not None
    
    def test_config_validation_error(self):
        """Test ConfigValidationError."""
        error = ConfigValidationError("Invalid value")
        assert isinstance(error, ConfigError)
        assert "Invalid value" in str(error)
    
    def test_config_validation_error_with_field(self):
        """Test ConfigValidationError with field."""
        error = ConfigValidationError("Invalid value", field="images_path")
        assert "Invalid value" in str(error)
        assert "images_path" in str(error)
    
    def test_config_parse_error(self):
        """Test ConfigParseError."""
        error = ConfigParseError("/path/to/config.yaml")
        assert isinstance(error, ConfigError)
        assert "/path/to/config.yaml" in str(error)
        assert "YAML" in str(error)


class TestBuildErrors:
    """Tests for build errors."""
    
    def test_build_error(self):
        """Test BuildError."""
        error = BuildError("Build failed")
        assert isinstance(error, DerpyError)
        assert "Build failed" in str(error)
    
    def test_dockerfile_not_found_error(self):
        """Test DockerfileNotFoundError."""
        error = DockerfileNotFoundError("/path/to/Dockerfile")
        assert isinstance(error, BuildError)
        assert "/path/to/Dockerfile" in str(error)
    
    def test_dockerfile_syntax_error(self):
        """Test DockerfileSyntaxError."""
        error = DockerfileSyntaxError("Invalid instruction")
        assert isinstance(error, BuildError)
        assert "Invalid instruction" in str(error)
    
    def test_dockerfile_syntax_error_with_line(self):
        """Test DockerfileSyntaxError with line number."""
        error = DockerfileSyntaxError("Invalid instruction", line_number=42)
        assert "Invalid instruction" in str(error)
        assert "42" in str(error)
    
    def test_unsupported_instruction_error(self):
        """Test UnsupportedInstructionError."""
        error = UnsupportedInstructionError("COPY")
        assert isinstance(error, BuildError)
        assert "COPY" in str(error)
        assert error.remediation is not None
    
    def test_unsupported_instruction_error_with_line(self):
        """Test UnsupportedInstructionError with line number."""
        error = UnsupportedInstructionError("COPY", line_number=10)
        assert "COPY" in str(error)
        assert "10" in str(error)
    
    def test_build_context_error(self):
        """Test BuildContextError."""
        error = BuildContextError("Context not found")
        assert isinstance(error, BuildError)
        assert "Context not found" in str(error)
    
    def test_command_execution_error(self):
        """Test CommandExecutionError."""
        error = CommandExecutionError("apt-get update", 1, stderr="Error output")
        assert isinstance(error, BuildError)
        assert "apt-get update" in str(error)
        assert "1" in str(error)
        assert "Error output" in str(error)
    
    def test_layer_creation_error(self):
        """Test LayerCreationError."""
        error = LayerCreationError("Failed to create layer")
        assert isinstance(error, BuildError)
        assert "Failed to create layer" in str(error)


class TestStorageErrors:
    """Tests for storage errors."""
    
    def test_storage_error(self):
        """Test StorageError."""
        error = StorageError("Storage problem")
        assert isinstance(error, DerpyError)
        assert "Storage problem" in str(error)
    
    def test_image_not_found_error(self):
        """Test ImageNotFoundError."""
        error = ImageNotFoundError("myapp:latest")
        assert isinstance(error, StorageError)
        assert "myapp:latest" in str(error)
        assert error.remediation is not None
    
    def test_image_validation_error(self):
        """Test ImageValidationError."""
        error = ImageValidationError("Invalid manifest")
        assert isinstance(error, StorageError)
        assert "Invalid manifest" in str(error)
    
    def test_repository_error(self):
        """Test RepositoryError."""
        error = RepositoryError("Repository corrupted")
        assert isinstance(error, StorageError)
        assert "Repository corrupted" in str(error)
    
    def test_repository_error_with_path(self):
        """Test RepositoryError with path."""
        error = RepositoryError("Corrupted", repository_path="/path/to/repo")
        assert "Corrupted" in str(error)
        assert "/path/to/repo" in str(error)
    
    def test_blob_not_found_error(self):
        """Test BlobNotFoundError."""
        error = BlobNotFoundError("sha256:abc123")
        assert isinstance(error, StorageError)
        assert "sha256:abc123" in str(error)
    
    def test_disk_space_error(self):
        """Test DiskSpaceError."""
        error = DiskSpaceError()
        assert isinstance(error, StorageError)
        assert "disk space" in str(error).lower()
    
    def test_disk_space_error_with_size(self):
        """Test DiskSpaceError with required space."""
        error = DiskSpaceError(required_space=1000000)
        assert "1000000" in str(error)


class TestRegistryErrors:
    """Tests for registry errors."""
    
    def test_registry_error(self):
        """Test RegistryError."""
        error = RegistryError("Registry problem")
        assert isinstance(error, DerpyError)
        assert "Registry problem" in str(error)
    
    def test_registry_connection_error(self):
        """Test RegistryConnectionError."""
        error = RegistryConnectionError("https://registry.example.com")
        assert isinstance(error, RegistryError)
        assert "registry.example.com" in str(error)
        assert error.remediation is not None
    
    def test_registry_authentication_error(self):
        """Test RegistryAuthenticationError."""
        error = RegistryAuthenticationError("https://registry.example.com")
        assert isinstance(error, RegistryError)
        assert "registry.example.com" in str(error)
        assert "Authentication" in str(error)
    
    def test_registry_not_found_error(self):
        """Test RegistryNotFoundError."""
        error = RegistryNotFoundError("myregistry")
        assert isinstance(error, RegistryError)
        assert "myregistry" in str(error)
    
    def test_image_push_error(self):
        """Test ImagePushError."""
        error = ImagePushError("myapp:latest", "Connection timeout")
        assert isinstance(error, RegistryError)
        assert "myapp:latest" in str(error)
        assert "Connection timeout" in str(error)
    
    def test_image_pull_error(self):
        """Test ImagePullError."""
        error = ImagePullError("myapp:latest", "Not found")
        assert isinstance(error, RegistryError)
        assert "myapp:latest" in str(error)
        assert "Not found" in str(error)


class TestPlatformErrors:
    """Tests for platform errors."""
    
    def test_platform_error(self):
        """Test PlatformError."""
        error = PlatformError("Platform issue")
        assert isinstance(error, DerpyError)
        assert "Platform issue" in str(error)
    
    def test_unsupported_platform_error(self):
        """Test UnsupportedPlatformError."""
        error = UnsupportedPlatformError("windows")
        assert isinstance(error, PlatformError)
        assert "windows" in str(error)
    
    def test_unsupported_platform_error_with_feature(self):
        """Test UnsupportedPlatformError with feature."""
        error = UnsupportedPlatformError("windows", feature="symlinks")
        assert "windows" in str(error)
        assert "symlinks" in str(error)
    
    def test_permission_error(self):
        """Test PermissionError."""
        error = PlatformError("Permission denied", remediation="Check permissions")
        assert isinstance(error, DerpyError)
        assert "Permission denied" in str(error)


class TestValidationErrors:
    """Tests for validation errors."""
    
    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Validation failed")
        assert isinstance(error, DerpyError)
        assert "Validation failed" in str(error)
    
    def test_invalid_tag_error(self):
        """Test InvalidTagError."""
        error = InvalidTagError("invalid tag format")
        assert isinstance(error, ValidationError)
        assert "invalid tag format" in str(error)
        assert error.remediation is not None
    
    def test_invalid_path_error(self):
        """Test InvalidPathError."""
        error = InvalidPathError("/invalid/path")
        assert isinstance(error, ValidationError)
        assert "/invalid/path" in str(error)
    
    def test_invalid_path_error_with_reason(self):
        """Test InvalidPathError with reason."""
        error = InvalidPathError("/invalid/path", reason="Does not exist")
        assert "/invalid/path" in str(error)
        assert "Does not exist" in str(error)
    
    def test_invalid_argument_error(self):
        """Test InvalidArgumentError."""
        error = InvalidArgumentError("--format", "invalid")
        assert isinstance(error, ValidationError)
        assert "--format" in str(error)
        assert "invalid" in str(error)
    
    def test_invalid_argument_error_with_reason(self):
        """Test InvalidArgumentError with reason."""
        error = InvalidArgumentError("--format", "invalid", reason="Must be json or table")
        assert "--format" in str(error)
        assert "invalid" in str(error)
        assert "Must be json or table" in str(error)


class TestExceptionHierarchy:
    """Tests for exception hierarchy."""
    
    def test_all_exceptions_inherit_from_derpy_error(self):
        """Test that all custom exceptions inherit from DerpyError."""
        exceptions = [
            ConfigError,
            BuildError,
            StorageError,
            RegistryError,
            PlatformError,
            ValidationError
        ]
        
        for exc_class in exceptions:
            assert issubclass(exc_class, DerpyError)
    
    def test_specific_exceptions_inherit_from_category(self):
        """Test specific exceptions inherit from their category."""
        test_cases = [
            (ConfigFileNotFoundError, ConfigError),
            (DockerfileNotFoundError, BuildError),
            (ImageNotFoundError, StorageError),
            (RegistryConnectionError, RegistryError),
            (UnsupportedPlatformError, PlatformError),
            (InvalidTagError, ValidationError)
        ]
        
        for specific, category in test_cases:
            assert issubclass(specific, category)
            assert issubclass(specific, DerpyError)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
