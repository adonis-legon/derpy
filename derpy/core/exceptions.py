"""Custom exception hierarchy for derpy.

This module defines all custom exceptions used throughout the derpy application,
providing clear error messages and remediation suggestions.

Exception Hierarchy:
    DerpyError (base)
    ├── ConfigError
    │   ├── ConfigFileNotFoundError
    │   ├── ConfigValidationError
    │   └── ConfigParseError
    ├── BuildError
    │   ├── DockerfileNotFoundError
    │   ├── DockerfileSyntaxError
    │   ├── UnsupportedInstructionError
    │   ├── BuildContextError
    │   ├── CommandExecutionError
    │   ├── LayerCreationError
    │   ├── BaseImageError
    │   ├── IsolationError
    │   └── FilesystemDiffError
    ├── StorageError
    │   ├── ImageNotFoundError
    │   ├── ImageValidationError
    │   ├── RepositoryError
    │   ├── BlobNotFoundError
    │   └── DiskSpaceError
    ├── RegistryError
    │   ├── RegistryConnectionError
    │   └── RegistryAuthenticationError
    ├── AuthenticationError
    │   ├── CredentialStorageError
    │   ├── TokenAuthenticationError
    │   └── InvalidCredentialsError
    ├── PlatformError
    │   ├── UnsupportedPlatformError
    │   ├── PermissionError
    │   └── PlatformNotSupportedError
    └── ValidationError
        ├── InvalidTagError
        ├── InvalidPathError
        └── InvalidArgumentError
"""

from typing import Optional


class DerpyError(Exception):
    """Base exception for all derpy errors.
    
    All custom exceptions in derpy should inherit from this class.
    Provides a consistent interface for error handling with optional
    remediation suggestions.
    """
    
    def __init__(
        self,
        message: str,
        remediation: Optional[str] = None,
        cause: Optional[Exception] = None
    ):
        """Initialize DerpyError.
        
        Args:
            message: Error message describing what went wrong
            remediation: Optional suggestion for how to fix the error
            cause: Optional underlying exception that caused this error
        """
        self.message = message
        self.remediation = remediation
        self.cause = cause
        
        # Build full error message
        full_message = message
        if remediation:
            full_message += f"\n\nSuggestion: {remediation}"
        if cause:
            full_message += f"\n\nCaused by: {type(cause).__name__}: {str(cause)}"
        
        super().__init__(full_message)
    
    def __str__(self) -> str:
        """String representation of the error."""
        return super().__str__()


# Configuration Errors

class ConfigError(DerpyError):
    """Configuration-related errors.
    
    Raised when there are issues with configuration files, settings,
    or configuration validation.
    """
    pass


class ConfigFileNotFoundError(ConfigError):
    """Configuration file not found."""
    
    def __init__(self, config_path: str):
        super().__init__(
            message=f"Configuration file not found: {config_path}",
            remediation="Run 'derpy config show' to create a default configuration"
        )


class ConfigValidationError(ConfigError):
    """Configuration validation failed."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        remediation = "Check your configuration file for errors"
        if field:
            remediation = f"Check the '{field}' field in your configuration"
        
        super().__init__(
            message=f"Configuration validation error: {message}",
            remediation=remediation
        )


class ConfigParseError(ConfigError):
    """Configuration file parsing failed."""
    
    def __init__(self, config_path: str, cause: Optional[Exception] = None):
        super().__init__(
            message=f"Failed to parse configuration file: {config_path}",
            remediation="Ensure the configuration file is valid YAML format",
            cause=cause
        )


# Build Errors

class BuildError(DerpyError):
    """Errors during image building process.
    
    Raised when there are issues during the container image build process.
    """
    pass


class DockerfileNotFoundError(BuildError):
    """Dockerfile not found."""
    
    def __init__(self, dockerfile_path: str):
        super().__init__(
            message=f"Dockerfile not found: {dockerfile_path}",
            remediation="Ensure the Dockerfile exists at the specified path"
        )


class DockerfileSyntaxError(BuildError):
    """Dockerfile syntax error."""
    
    def __init__(self, message: str, line_number: Optional[int] = None):
        error_msg = f"Dockerfile syntax error: {message}"
        if line_number:
            error_msg = f"Dockerfile syntax error at line {line_number}: {message}"
        
        super().__init__(
            message=error_msg,
            remediation="Check your Dockerfile syntax and fix any errors"
        )


class UnsupportedInstructionError(BuildError):
    """Unsupported Dockerfile instruction."""
    
    def __init__(self, instruction: str, line_number: Optional[int] = None):
        error_msg = f"Unsupported Dockerfile instruction: {instruction}"
        if line_number:
            error_msg = f"Unsupported Dockerfile instruction at line {line_number}: {instruction}"
        
        super().__init__(
            message=error_msg,
            remediation=(
                "This version of derpy only supports FROM, RUN, and CMD instructions. "
                "Remove or comment out unsupported instructions."
            )
        )


class BuildContextError(BuildError):
    """Build context error."""
    
    def __init__(self, message: str, context_path: Optional[str] = None):
        error_msg = f"Build context error: {message}"
        if context_path:
            error_msg = f"Build context error at {context_path}: {message}"
        
        super().__init__(
            message=error_msg,
            remediation="Ensure the build context directory exists and is accessible"
        )


class CommandExecutionError(BuildError):
    """Command execution failed during build."""
    
    def __init__(
        self,
        command: str,
        exit_code: int,
        stdout: Optional[str] = None,
        stderr: Optional[str] = None
    ):
        error_msg = f"Command failed with exit code {exit_code}: {command}"
        if stderr:
            error_msg += f"\nError output: {stderr}"
        
        super().__init__(
            message=error_msg,
            remediation="Check the command syntax and ensure all dependencies are available"
        )


class LayerCreationError(BuildError):
    """Layer creation failed."""
    
    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(
            message=f"Failed to create layer: {message}",
            remediation="Check disk space and file permissions",
            cause=cause
        )


# Storage Errors

class StorageError(DerpyError):
    """Storage-related errors.
    
    Raised when there are issues with local image storage operations.
    """
    pass


class ImageNotFoundError(StorageError):
    """Image not found in local repository."""
    
    def __init__(self, image_tag: str):
        super().__init__(
            message=f"Image not found in local repository: {image_tag}",
            remediation="Use 'derpy ls' to list available images or build the image first"
        )


class ImageValidationError(StorageError):
    """Image validation failed."""
    
    def __init__(self, message: str):
        super().__init__(
            message=f"Image validation error: {message}",
            remediation="Ensure the image was built correctly and is OCI-compliant"
        )


class RepositoryError(StorageError):
    """Local repository error."""
    
    def __init__(self, message: str, repository_path: Optional[str] = None):
        error_msg = f"Repository error: {message}"
        if repository_path:
            error_msg = f"Repository error at {repository_path}: {message}"
        
        super().__init__(
            message=error_msg,
            remediation="Check that the repository directory exists and has proper permissions"
        )


class BlobNotFoundError(StorageError):
    """Blob not found in storage."""
    
    def __init__(self, digest: str):
        super().__init__(
            message=f"Blob not found in storage: {digest}",
            remediation="The image may be corrupted. Try rebuilding the image."
        )


class DiskSpaceError(StorageError):
    """Insufficient disk space."""
    
    def __init__(self, required_space: Optional[int] = None):
        message = "Insufficient disk space for operation"
        if required_space:
            message = f"Insufficient disk space. Required: {required_space} bytes"
        
        super().__init__(
            message=message,
            remediation="Free up disk space or use 'derpy cleanup' to remove unused images"
        )


# Registry Errors

class RegistryError(DerpyError):
    """Registry-related errors.
    
    Raised when there are issues with remote registry operations.
    """
    pass


class RegistryConnectionError(RegistryError):
    """Failed to connect to registry."""
    
    def __init__(self, registry_url: str, cause: Optional[Exception] = None):
        super().__init__(
            message=f"Failed to connect to registry: {registry_url}",
            remediation=(
                "Check your network connection and ensure the registry URL is correct. "
                "Use --insecure flag if the registry uses self-signed certificates."
            ),
            cause=cause
        )


class RegistryAuthenticationError(RegistryError):
    """Registry authentication failed."""
    
    def __init__(self, registry_url: str):
        super().__init__(
            message=f"Authentication failed for registry: {registry_url}",
            remediation=(
                "Check your username and password. "
                "Use 'derpy config set registry_configs.<name>.username <username>' "
                "to configure credentials."
            )
        )


# Authentication Errors

class AuthenticationError(DerpyError):
    """Base class for authentication errors.
    
    Raised when there are issues with registry authentication,
    credential storage, or token-based authentication.
    """
    pass


class CredentialStorageError(AuthenticationError):
    """Error storing or retrieving credentials.
    
    Raised when there are issues reading or writing the auth file,
    or when the auth file format is invalid.
    """
    
    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(
            message=f"Credential storage error: {message}",
            remediation="Check file permissions for ~/.derpy/auth.json",
            cause=cause
        )


class TokenAuthenticationError(AuthenticationError):
    """Error during token authentication.
    
    Raised when there are issues requesting or using bearer tokens
    for registry authentication (e.g., Docker Hub token auth).
    """
    
    def __init__(self, message: str, realm: Optional[str] = None, cause: Optional[Exception] = None):
        error_msg = f"Token authentication error: {message}"
        if realm:
            error_msg = f"Token authentication error for {realm}: {message}"
        
        super().__init__(
            message=error_msg,
            remediation="Check network connectivity and registry authentication service status",
            cause=cause
        )


class InvalidCredentialsError(AuthenticationError):
    """Invalid username or password.
    
    Raised when authentication fails due to incorrect credentials.
    """
    
    def __init__(self, registry: str):
        super().__init__(
            message=f"Invalid credentials for registry: {registry}",
            remediation=f"Check your username and password. Run 'derpy login {registry}' to update credentials."
        )


class RegistryNotFoundError(RegistryError):
    """Registry not found in configuration."""
    
    def __init__(self, registry_name: str):
        super().__init__(
            message=f"Registry not found in configuration: {registry_name}",
            remediation=(
                "Add the registry to your configuration with: "
                f"derpy config set registry_configs.{registry_name}.url <url>"
            )
        )


class ImagePushError(RegistryError):
    """Failed to push image to registry."""
    
    def __init__(self, image_tag: str, message: str):
        super().__init__(
            message=f"Failed to push image '{image_tag}': {message}",
            remediation="Check network connectivity and registry permissions"
        )


class ImagePullError(RegistryError):
    """Failed to pull image from registry."""
    
    def __init__(self, image_tag: str, message: str):
        super().__init__(
            message=f"Failed to pull image '{image_tag}': {message}",
            remediation="Check that the image exists in the registry and you have pull permissions"
        )


# Platform Errors

class PlatformError(DerpyError):
    """Platform-specific errors.
    
    Raised when there are platform-specific issues.
    """
    pass


class UnsupportedPlatformError(PlatformError):
    """Platform not supported."""
    
    def __init__(self, platform: str, feature: Optional[str] = None):
        message = f"Platform not supported: {platform}"
        if feature:
            message = f"Feature '{feature}' not supported on platform: {platform}"
        
        super().__init__(
            message=message,
            remediation="Check the documentation for platform-specific requirements"
        )


class PermissionError(PlatformError):
    """Permission denied."""
    
    def __init__(self, path: str, operation: str):
        super().__init__(
            message=f"Permission denied for {operation}: {path}",
            remediation=(
                "Check file/directory permissions. "
                "You may need to run with elevated privileges or change ownership."
            )
        )


# Validation Errors

class ValidationError(DerpyError):
    """Validation error.
    
    Raised when input validation fails.
    """
    pass


class InvalidTagError(ValidationError):
    """Invalid image tag format."""
    
    def __init__(self, tag: str):
        super().__init__(
            message=f"Invalid image tag format: {tag}",
            remediation=(
                "Image tags should be in the format 'name:version' or 'name:latest'. "
                "Example: myapp:v1.0"
            )
        )


class InvalidPathError(ValidationError):
    """Invalid path."""
    
    def __init__(self, path: str, reason: Optional[str] = None):
        message = f"Invalid path: {path}"
        if reason:
            message += f" - {reason}"
        
        super().__init__(
            message=message,
            remediation="Ensure the path is valid and accessible"
        )


class InvalidArgumentError(ValidationError):
    """Invalid argument."""
    
    def __init__(self, argument: str, value: str, reason: Optional[str] = None):
        message = f"Invalid value for argument '{argument}': {value}"
        if reason:
            message += f" - {reason}"
        
        super().__init__(
            message=message,
            remediation="Check the command help for valid argument values"
        )


# Build Isolation Errors

class BaseImageError(BuildError):
    """Base image retrieval or extraction failed.
    
    Raised when there are issues downloading or extracting base images.
    """
    
    def __init__(self, image_ref: str, message: str, cause: Optional[Exception] = None):
        super().__init__(
            message=f"Base image error for '{image_ref}': {message}",
            remediation=(
                "Ensure the image reference is correct and the registry is accessible. "
                "Check network connectivity and authentication credentials."
            ),
            cause=cause
        )


class IsolationError(BuildError):
    """Chroot isolation setup or execution failed.
    
    Raised when there are issues with chroot environment setup or command execution.
    """
    
    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(
            message=f"Isolation error: {message}",
            remediation=(
                "Ensure you are running on Linux with appropriate permissions. "
                "You may need to run with sudo or have CAP_SYS_CHROOT capability."
            ),
            cause=cause
        )


class FilesystemDiffError(BuildError):
    """Filesystem diff capture failed.
    
    Raised when there are issues capturing filesystem changes between snapshots.
    """
    
    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(
            message=f"Filesystem diff error: {message}",
            remediation="Check disk space and file permissions in the build directory",
            cause=cause
        )


class PlatformNotSupportedError(PlatformError):
    """Operation not supported on current platform.
    
    Raised when attempting to use features that require specific platform support.
    """
    
    def __init__(self, operation: str, required_platform: str, current_platform: str):
        super().__init__(
            message=(
                f"Operation '{operation}' requires {required_platform} "
                f"but running on {current_platform}"
            ),
            remediation=(
                f"This feature requires {required_platform}. "
                "Consider using a Linux VM or container to run this operation."
            )
        )
