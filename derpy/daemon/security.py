"""Security utilities for daemon operations.

This module provides security features including input validation,
path validation, command sanitization, privilege dropping, and
log sanitization to prevent security vulnerabilities.
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Optional, Tuple


logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Exception raised for security violations."""
    pass


class InputValidator:
    """Validates user inputs to prevent injection attacks."""
    
    # Allowed characters for tags (alphanumeric, dash, underscore, dot, colon)
    # Only ASCII alphanumeric to prevent unicode issues
    TAG_PATTERN = re.compile(r'^[a-zA-Z0-9._:/-]+$', re.ASCII)
    
    # Maximum lengths for various inputs
    MAX_TAG_LENGTH = 256
    MAX_PATH_LENGTH = 4096
    MAX_BUILD_ARG_KEY_LENGTH = 128
    MAX_BUILD_ARG_VALUE_LENGTH = 1024
    
    @classmethod
    def validate_tag(cls, tag: str) -> List[str]:
        """Validate an image tag.
        
        Args:
            tag: Image tag to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not tag:
            errors.append("Tag cannot be empty")
            return errors
        
        if len(tag) > cls.MAX_TAG_LENGTH:
            errors.append(f"Tag exceeds maximum length of {cls.MAX_TAG_LENGTH}")
        
        # Check for non-ASCII characters
        try:
            tag.encode('ascii')
        except UnicodeEncodeError:
            errors.append("Tag contains non-ASCII characters")
            return errors
        
        if not cls.TAG_PATTERN.match(tag):
            errors.append("Tag contains invalid characters (only alphanumeric, dash, underscore, dot, colon, slash allowed)")
        
        return errors
    
    @classmethod
    def validate_path(cls, path_str: str, must_exist: bool = False) -> List[str]:
        """Validate a file path.
        
        Args:
            path_str: Path string to validate
            must_exist: Whether the path must exist
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not path_str:
            errors.append("Path cannot be empty")
            return errors
        
        if len(path_str) > cls.MAX_PATH_LENGTH:
            errors.append(f"Path exceeds maximum length of {cls.MAX_PATH_LENGTH}")
        
        # Check for directory traversal attempts
        if cls.contains_directory_traversal(path_str):
            errors.append("Path contains directory traversal sequences (..)")
        
        # Check for null bytes
        if '\0' in path_str:
            errors.append("Path contains null bytes")
        
        # Validate path exists if required
        if must_exist and not errors:
            try:
                path = Path(path_str)
                if not path.exists():
                    errors.append(f"Path does not exist: {path_str}")
            except Exception as e:
                errors.append(f"Invalid path: {e}")
        
        return errors
    
    @classmethod
    def validate_build_args(cls, build_args: dict) -> List[str]:
        """Validate build arguments.
        
        Args:
            build_args: Dictionary of build arguments
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not isinstance(build_args, dict):
            errors.append("Build args must be a dictionary")
            return errors
        
        for key, value in build_args.items():
            # Validate key
            if not isinstance(key, str):
                errors.append(f"Build arg key must be string: {key}")
                continue
            
            if not key:
                errors.append("Build arg key cannot be empty")
                continue
            
            if len(key) > cls.MAX_BUILD_ARG_KEY_LENGTH:
                errors.append(f"Build arg key '{key}' exceeds maximum length of {cls.MAX_BUILD_ARG_KEY_LENGTH}")
            
            # Check for shell metacharacters in key
            if re.search(r'[;&|`$(){}[\]<>\\]', key):
                errors.append(f"Build arg key '{key}' contains shell metacharacters")
            
            # Validate value
            if not isinstance(value, str):
                errors.append(f"Build arg value for '{key}' must be string")
                continue
            
            if len(value) > cls.MAX_BUILD_ARG_VALUE_LENGTH:
                errors.append(f"Build arg value for '{key}' exceeds maximum length of {cls.MAX_BUILD_ARG_VALUE_LENGTH}")
        
        return errors
    
    @classmethod
    def contains_directory_traversal(cls, path_str: str) -> bool:
        """Check if path contains directory traversal sequences.
        
        Args:
            path_str: Path string to check
            
        Returns:
            True if path contains directory traversal, False otherwise
        """
        # Normalize the path and check if it tries to escape
        try:
            path = Path(path_str).resolve()
            # Check for .. in the path components
            parts = Path(path_str).parts
            for part in parts:
                if part == '..':
                    return True
            return False
        except Exception:
            # If path resolution fails, consider it suspicious
            return True


class PathValidator:
    """Validates and sanitizes file paths to prevent directory traversal."""
    
    @classmethod
    def validate_path_within_root(cls, path: Path, root: Path) -> Tuple[bool, Optional[str]]:
        """Validate that a path is within a root directory.
        
        This prevents directory traversal attacks by ensuring the resolved
        path is within the specified root directory.
        
        Args:
            path: Path to validate
            root: Root directory that path must be within
            
        Returns:
            Tuple of (is_valid, error_message). If valid, error_message is None.
        """
        try:
            # Resolve both paths to absolute paths
            resolved_path = path.resolve()
            resolved_root = root.resolve()
            
            # Check if resolved path is within root
            try:
                resolved_path.relative_to(resolved_root)
                return True, None
            except ValueError:
                return False, f"Path '{path}' is outside root directory '{root}'"
                
        except Exception as e:
            return False, f"Failed to validate path: {e}"
    
    @classmethod
    def sanitize_path(cls, path_str: str) -> str:
        """Sanitize a path string by removing dangerous components.
        
        Args:
            path_str: Path string to sanitize
            
        Returns:
            Sanitized path string
        """
        # Remove null bytes
        path_str = path_str.replace('\0', '')
        
        # Remove leading/trailing whitespace
        path_str = path_str.strip()
        
        return path_str


class CommandSanitizer:
    """Sanitizes commands to prevent injection attacks."""
    
    # Shell metacharacters that could be used for injection
    SHELL_METACHARACTERS = r'[;&|`$(){}[\]<>\\]'
    
    @classmethod
    def validate_command(cls, command: str) -> List[str]:
        """Validate a command for potential injection attempts.
        
        Args:
            command: Command string to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not command:
            errors.append("Command cannot be empty")
            return errors
        
        # Check for null bytes
        if '\0' in command:
            errors.append("Command contains null bytes")
        
        # Check for command chaining attempts
        if re.search(r'[;&|]', command):
            errors.append("Command contains command chaining characters (;, &, |)")
        
        # Check for parentheses (used in subshells and command substitution)
        if re.search(r'[()]', command):
            errors.append("Command contains parentheses (subshell or command substitution)")
        
        # Check for command substitution (both backticks and $())
        if '`' in command:
            errors.append("Command contains command substitution")
        
        # Check for variable expansion ($ followed by alphanumeric or {)
        if re.search(r'\$[a-zA-Z_{]', command):
            errors.append("Command contains variable expansion")
        
        # Check for redirection
        if re.search(r'[<>]', command):
            errors.append("Command contains redirection operators")
        
        return errors
    
    @classmethod
    def sanitize_command_arg(cls, arg: str) -> str:
        """Sanitize a command argument by escaping special characters.
        
        Args:
            arg: Argument to sanitize
            
        Returns:
            Sanitized argument
        """
        # Remove null bytes
        arg = arg.replace('\0', '')
        
        # Escape shell metacharacters
        # This is a basic implementation - in production, use shlex.quote()
        for char in ['$', '`', '"', '\\', '!']:
            arg = arg.replace(char, '\\' + char)
        
        return arg


class PrivilegeManager:
    """Manages privilege dropping for non-critical operations."""
    
    @classmethod
    def drop_privileges(cls, uid: int, gid: int) -> None:
        """Drop privileges to specified user and group.
        
        This should be called for non-critical operations that don't
        require root privileges.
        
        Args:
            uid: User ID to drop to
            gid: Group ID to drop to
            
        Raises:
            SecurityError: If privilege dropping fails
        """
        if os.getuid() != 0:
            # Not running as root, nothing to drop
            logger.debug("Not running as root, skipping privilege drop")
            return
        
        try:
            # Drop group privileges first
            os.setgid(gid)
            logger.debug(f"Dropped group privileges to gid={gid}")
            
            # Drop user privileges
            os.setuid(uid)
            logger.debug(f"Dropped user privileges to uid={uid}")
            
        except OSError as e:
            raise SecurityError(f"Failed to drop privileges: {e}")
    
    @classmethod
    def can_drop_privileges(cls) -> bool:
        """Check if we can drop privileges (i.e., running as root).
        
        Returns:
            True if running as root and can drop privileges
        """
        return os.getuid() == 0
    
    @classmethod
    def set_restrictive_permissions(cls, path: Path, mode: int = 0o700) -> None:
        """Set restrictive permissions on a file or directory.
        
        Args:
            path: Path to set permissions on
            mode: Permission mode (default: 0o700 - owner only)
            
        Raises:
            SecurityError: If setting permissions fails
        """
        try:
            os.chmod(path, mode)
            logger.debug(f"Set permissions {oct(mode)} on {path}")
        except OSError as e:
            raise SecurityError(f"Failed to set permissions on {path}: {e}")


class LogSanitizer:
    """Sanitizes log messages to remove sensitive information."""
    
    # Patterns for sensitive information
    PASSWORD_PATTERNS = [
        re.compile(r'(password|passwd|pwd)["\']?\s*[:=]\s*["\']?([^"\'\s]+)', re.IGNORECASE),
    ]
    
    TOKEN_PATTERNS = [
        re.compile(r'(token|api[_-]?key|secret)["\']?\s*[:=]\s*["\']?([^"\'\s]+)', re.IGNORECASE),
    ]
    
    # Docker Hub token pattern (Bearer tokens) - match any non-whitespace after Bearer
    BEARER_TOKEN_PATTERN = re.compile(r'Bearer\s+(\S+)', re.IGNORECASE)
    
    # Basic auth pattern (base64 encoded credentials)
    BASIC_AUTH_PATTERN = re.compile(r'Basic\s+([A-Za-z0-9+/=]+)', re.IGNORECASE)
    
    @classmethod
    def sanitize_log_message(cls, message: str) -> str:
        """Sanitize a log message by removing sensitive information.
        
        Args:
            message: Log message to sanitize
            
        Returns:
            Sanitized log message with credentials redacted
        """
        sanitized = message
        
        # Redact passwords - replace the entire match including the value
        for pattern in cls.PASSWORD_PATTERNS:
            sanitized = pattern.sub(r'\1=***REDACTED***', sanitized)
        
        # Redact tokens and API keys
        for pattern in cls.TOKEN_PATTERNS:
            sanitized = pattern.sub(r'\1=***REDACTED***', sanitized)
        
        # Redact Bearer tokens
        sanitized = cls.BEARER_TOKEN_PATTERN.sub(r'Bearer ***REDACTED***', sanitized)
        
        # Redact Basic auth
        sanitized = cls.BASIC_AUTH_PATTERN.sub(r'Basic ***REDACTED***', sanitized)
        
        return sanitized
    
    @classmethod
    def sanitize_dict(cls, data: dict) -> dict:
        """Sanitize a dictionary by removing sensitive keys.
        
        Args:
            data: Dictionary to sanitize
            
        Returns:
            Sanitized dictionary with sensitive values redacted
        """
        if not isinstance(data, dict):
            return data
        
        sensitive_keys = {
            'password', 'passwd', 'pwd',
            'token', 'api_key', 'apikey', 'secret',
            'authorization',
        }
        
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            # Check if the key itself is sensitive (exact match or contains sensitive word)
            is_sensitive_key = any(sensitive == key_lower or sensitive in key_lower for sensitive in sensitive_keys)
            
            if is_sensitive_key:
                # Redact the entire value if key is sensitive
                sanitized[key] = '***REDACTED***'
            elif isinstance(value, dict):
                # Recursively sanitize nested dicts
                sanitized[key] = cls.sanitize_dict(value)
            elif isinstance(value, str):
                # Sanitize string values for embedded credentials
                sanitized[key] = cls.sanitize_log_message(value)
            else:
                sanitized[key] = value
        
        return sanitized
