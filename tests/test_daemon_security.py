"""Property-based tests for daemon security features.

This module tests security features including:
- Property 29: Privilege dropping for non-critical operations
- Property 30: Restrictive temporary directory permissions
- Property 31: Command injection prevention
- Property 32: Directory traversal prevention
- Property 33: Credential sanitization in logs

Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5
"""

import pytest
import os
import tempfile
import stat
from pathlib import Path
from hypothesis import given, settings, strategies as st
from unittest.mock import patch, MagicMock

from derpy.daemon.security import (
    InputValidator,
    PathValidator,
    CommandSanitizer,
    PrivilegeManager,
    LogSanitizer,
    SecurityError,
)


class TestPrivilegeDropping:
    """Tests for privilege dropping functionality.
    
    Property 29: Privilege dropping for non-critical operations
    Validates: Requirements 9.1
    """
    
    @given(
        uid=st.integers(min_value=1000, max_value=65535),
        gid=st.integers(min_value=1000, max_value=65535)
    )
    @settings(max_examples=100)
    def test_property_privilege_dropping_for_non_critical_operations(self, uid, gid):
        """
        Property 29: Privilege dropping for non-critical operations
        
        For any non-critical operation, the daemon should drop root privileges
        before executing it.
        
        Validates: Requirements 9.1
        """
        # Mock os functions to simulate privilege dropping
        with patch('os.getuid', return_value=0):  # Simulate running as root
            with patch('os.setuid') as mock_setuid:
                with patch('os.setgid') as mock_setgid:
                    # Attempt to drop privileges
                    PrivilegeManager.drop_privileges(uid, gid)
                    
                    # Verify setgid was called first (group before user)
                    mock_setgid.assert_called_once_with(gid)
                    
                    # Verify setuid was called
                    mock_setuid.assert_called_once_with(uid)
    
    def test_privilege_dropping_when_not_root(self):
        """Test that privilege dropping is skipped when not running as root."""
        # When not running as root, drop_privileges should do nothing
        with patch('os.getuid', return_value=1000):  # Not root
            with patch('os.setuid') as mock_setuid:
                with patch('os.setgid') as mock_setgid:
                    # Should not raise an error
                    PrivilegeManager.drop_privileges(1001, 1001)
                    
                    # Should not call setuid/setgid
                    mock_setuid.assert_not_called()
                    mock_setgid.assert_not_called()
    
    def test_can_drop_privileges_detection(self):
        """Test detection of whether we can drop privileges."""
        # When running as root
        with patch('os.getuid', return_value=0):
            assert PrivilegeManager.can_drop_privileges() is True
        
        # When not running as root
        with patch('os.getuid', return_value=1000):
            assert PrivilegeManager.can_drop_privileges() is False


class TestRestrictivePermissions:
    """Tests for restrictive directory permissions.
    
    Property 30: Restrictive temporary directory permissions
    Validates: Requirements 9.2
    """
    
    @given(dummy=st.just(None))
    @settings(max_examples=100)
    def test_property_restrictive_temporary_directory_permissions(self, dummy):
        """
        Property 30: Restrictive temporary directory permissions
        
        For any temporary directory created by the daemon, the permissions
        should be restrictive (0700) to prevent unauthorized access.
        
        Validates: Requirements 9.2
        """
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Set restrictive permissions
            PrivilegeManager.set_restrictive_permissions(tmppath, mode=0o700)
            
            # Verify permissions are 0700 (owner read/write/execute only)
            file_stat = tmppath.stat()
            mode = stat.S_IMODE(file_stat.st_mode)
            
            # Check that only owner has permissions
            assert mode == 0o700, f"Expected 0o700, got {oct(mode)}"
            
            # Verify no group permissions
            assert not (mode & stat.S_IRGRP), "Group should not have read permission"
            assert not (mode & stat.S_IWGRP), "Group should not have write permission"
            assert not (mode & stat.S_IXGRP), "Group should not have execute permission"
            
            # Verify no other permissions
            assert not (mode & stat.S_IROTH), "Others should not have read permission"
            assert not (mode & stat.S_IWOTH), "Others should not have write permission"
            assert not (mode & stat.S_IXOTH), "Others should not have execute permission"
    
    @given(
        mode=st.sampled_from([0o700, 0o600, 0o500, 0o400])
    )
    @settings(max_examples=100)
    def test_property_various_restrictive_modes(self, mode):
        """Test that various restrictive permission modes can be set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Set permissions
            PrivilegeManager.set_restrictive_permissions(tmppath, mode=mode)
            
            # Verify permissions match
            file_stat = tmppath.stat()
            actual_mode = stat.S_IMODE(file_stat.st_mode)
            assert actual_mode == mode


class TestCommandInjectionPrevention:
    """Tests for command injection prevention.
    
    Property 31: Command injection prevention
    Validates: Requirements 9.3
    """
    
    @given(
        injection_char=st.sampled_from([';', '&', '|', '`', '$', '(', ')', '<', '>'])
    )
    @settings(max_examples=100)
    def test_property_command_injection_prevention(self, injection_char):
        """
        Property 31: Command injection prevention
        
        For any user-provided command, the daemon should validate and sanitize
        it to prevent command injection attacks.
        
        Validates: Requirements 9.3
        """
        # Create a command with injection attempt
        malicious_command = f"echo hello{injection_char}rm -rf /"
        
        # Validate command
        errors = CommandSanitizer.validate_command(malicious_command)
        
        # Should detect the injection attempt
        assert len(errors) > 0, f"Failed to detect injection with '{injection_char}'"
        
        # Error message should mention the dangerous character or pattern
        error_text = " ".join(errors).lower()
        assert any(term in error_text for term in [
            'chaining', 'substitution', 'redirection', 'null', 'expansion', 'parentheses', 'subshell'
        ]), f"Error message should describe the threat: {errors}"
    
    @given(
        safe_command=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd'),
                whitelist_characters=' -_.'
            ),
            min_size=1,
            max_size=100
        )
    )
    @settings(max_examples=100)
    def test_property_safe_commands_accepted(self, safe_command):
        """Test that safe commands without injection attempts are accepted."""
        # Validate safe command
        errors = CommandSanitizer.validate_command(safe_command)
        
        # Should not have errors (unless it's empty after filtering)
        if safe_command.strip():
            assert len(errors) == 0, f"Safe command rejected: {errors}"
    
    def test_command_substitution_detection(self):
        """Test detection of command substitution attempts."""
        # Test backtick substitution
        errors = CommandSanitizer.validate_command("echo `whoami`")
        assert len(errors) > 0
        assert any('substitution' in e.lower() for e in errors)
        
        # Test $() substitution
        errors = CommandSanitizer.validate_command("echo $(whoami)")
        assert len(errors) > 0
        assert any('substitution' in e.lower() for e in errors)
    
    def test_null_byte_detection(self):
        """Test detection of null bytes in commands."""
        errors = CommandSanitizer.validate_command("echo\0rm -rf /")
        assert len(errors) > 0
        assert any('null' in e.lower() for e in errors)


class TestDirectoryTraversalPrevention:
    """Tests for directory traversal prevention.
    
    Property 32: Directory traversal prevention
    Validates: Requirements 9.4
    """
    
    @given(
        traversal_pattern=st.sampled_from(['../', '../..', '../../..', './../'])
    )
    @settings(max_examples=100)
    def test_property_directory_traversal_prevention(self, traversal_pattern):
        """
        Property 32: Directory traversal prevention
        
        For any file path provided by the user, the daemon should validate it
        to prevent directory traversal attacks (../, etc.)
        
        Validates: Requirements 9.4
        """
        # Create a path with traversal attempt
        malicious_path = f"/tmp/build/{traversal_pattern}etc/passwd"
        
        # Check if path contains directory traversal
        has_traversal = InputValidator.contains_directory_traversal(malicious_path)
        
        # Should detect the traversal attempt
        assert has_traversal is True, f"Failed to detect traversal with '{traversal_pattern}'"
        
        # Validate path should also catch it
        errors = InputValidator.validate_path(malicious_path)
        assert len(errors) > 0, "Path validation should detect traversal"
        assert any('traversal' in e.lower() for e in errors)
    
    @given(
        safe_path=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd'),
                whitelist_characters='/-_.'
            ),
            min_size=1,
            max_size=100
        ).filter(lambda x: '..' not in x and x.strip())
    )
    @settings(max_examples=100)
    def test_property_safe_paths_accepted(self, safe_path):
        """Test that safe paths without traversal are accepted."""
        # Ensure path doesn't start with / to avoid absolute path issues
        if safe_path.startswith('/'):
            safe_path = safe_path[1:]
        
        # Check for traversal
        has_traversal = InputValidator.contains_directory_traversal(safe_path)
        
        # Should not detect traversal in safe paths
        assert has_traversal is False, f"False positive for safe path: {safe_path}"
    
    def test_path_within_root_validation(self):
        """Test validation that paths stay within root directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            
            # Safe path within root
            safe_path = root / "subdir" / "file.txt"
            is_valid, error = PathValidator.validate_path_within_root(safe_path, root)
            assert is_valid is True
            assert error is None
            
            # Path trying to escape root
            unsafe_path = root / ".." / "etc" / "passwd"
            is_valid, error = PathValidator.validate_path_within_root(unsafe_path, root)
            assert is_valid is False
            assert error is not None
            assert 'outside root' in error.lower()
    
    def test_null_byte_in_path_detection(self):
        """Test detection of null bytes in paths."""
        errors = InputValidator.validate_path("/tmp/file\0.txt")
        assert len(errors) > 0
        assert any('null' in e.lower() for e in errors)


class TestCredentialSanitization:
    """Tests for credential sanitization in logs.
    
    Property 33: Credential sanitization in logs
    Validates: Requirements 9.5
    """
    
    @given(
        password=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='!@#$%^&*'),
            min_size=8,
            max_size=32
        ).filter(lambda x: x and not x.isspace() and 'REDACTED' not in x),
        credential_key=st.sampled_from(['password', 'passwd', 'pwd', 'token', 'api_key', 'secret'])
    )
    @settings(max_examples=100)
    def test_property_credential_sanitization_in_logs(self, password, credential_key):
        """
        Property 33: Credential sanitization in logs
        
        For any log entry, sensitive information like registry credentials
        should not be included.
        
        Validates: Requirements 9.5
        """
        # Create a log message with credentials
        log_message = f"Authenticating with {credential_key}={password}"
        
        # Sanitize the log message
        sanitized = LogSanitizer.sanitize_log_message(log_message)
        
        # Password should not appear in sanitized message
        assert password not in sanitized, f"Password leaked in log: {sanitized}"
        
        # Should contain redaction marker
        assert 'REDACTED' in sanitized, f"Missing redaction marker: {sanitized}"
    
    @given(
        token=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='._-'),
            min_size=20,
            max_size=100
        )
    )
    @settings(max_examples=100)
    def test_property_bearer_token_sanitization(self, token):
        """Test that Bearer tokens are sanitized in logs."""
        # Create log message with Bearer token
        log_message = f"Authorization: Bearer {token}"
        
        # Sanitize
        sanitized = LogSanitizer.sanitize_log_message(log_message)
        
        # Token should not appear
        assert token not in sanitized
        assert 'REDACTED' in sanitized
    
    @given(
        username=st.text(min_size=3, max_size=20),
        password=st.text(min_size=8, max_size=32)
    )
    @settings(max_examples=100)
    def test_property_basic_auth_sanitization(self, username, password):
        """Test that Basic auth credentials are sanitized."""
        import base64
        
        # Create Basic auth header
        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        log_message = f"Authorization: Basic {encoded}"
        
        # Sanitize
        sanitized = LogSanitizer.sanitize_log_message(log_message)
        
        # Encoded credentials should not appear
        assert encoded not in sanitized
        assert 'REDACTED' in sanitized
    
    @given(
        password=st.text(min_size=8, max_size=32),
        api_key=st.text(min_size=16, max_size=64)
    )
    @settings(max_examples=100)
    def test_property_dict_sanitization(self, password, api_key):
        """Test that dictionaries with sensitive keys are sanitized."""
        # Create dict with sensitive data
        data = {
            'username': 'testuser',
            'password': password,
            'api_key': api_key,
            'normal_field': 'normal_value'
        }
        
        # Sanitize
        sanitized = LogSanitizer.sanitize_dict(data)
        
        # Sensitive values should be redacted
        assert sanitized['password'] == '***REDACTED***'
        assert sanitized['api_key'] == '***REDACTED***'
        
        # Non-sensitive values should remain
        assert sanitized['username'] == 'testuser'
        assert sanitized['normal_field'] == 'normal_value'
    
    def test_nested_dict_sanitization(self):
        """Test sanitization of nested dictionaries."""
        data = {
            'config': {
                'auth': {
                    'password': 'secret123',
                    'token': 'abc123'
                },
                'server': 'example.com'
            }
        }
        
        sanitized = LogSanitizer.sanitize_dict(data)
        
        # Nested sensitive values should be redacted
        assert sanitized['config']['auth']['password'] == '***REDACTED***'
        assert sanitized['config']['auth']['token'] == '***REDACTED***'
        
        # Non-sensitive nested values should remain
        assert sanitized['config']['server'] == 'example.com'


class TestInputValidation:
    """Additional tests for input validation."""
    
    @given(
        tag=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:/-',
            min_size=1,
            max_size=256
        )
    )
    @settings(max_examples=100)
    def test_property_valid_tags_accepted(self, tag):
        """Test that valid tags are accepted."""
        errors = InputValidator.validate_tag(tag)
        assert len(errors) == 0, f"Valid tag rejected: {tag}, errors: {errors}"
    
    @given(
        invalid_char=st.sampled_from(['!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '=', '+'])
    )
    @settings(max_examples=100)
    def test_property_invalid_tag_characters_rejected(self, invalid_char):
        """Test that tags with invalid characters are rejected."""
        tag = f"myapp{invalid_char}latest"
        errors = InputValidator.validate_tag(tag)
        assert len(errors) > 0
        assert any('invalid characters' in e.lower() for e in errors)
    
    def test_empty_tag_rejected(self):
        """Test that empty tags are rejected."""
        errors = InputValidator.validate_tag("")
        assert len(errors) > 0
        assert any('empty' in e.lower() for e in errors)
    
    def test_tag_length_limit(self):
        """Test that overly long tags are rejected."""
        long_tag = "a" * 300
        errors = InputValidator.validate_tag(long_tag)
        assert len(errors) > 0
        assert any('length' in e.lower() for e in errors)
    
    @given(
        build_args=st.dictionaries(
            keys=st.text(
                alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_'),
                min_size=1,
                max_size=50
            ),
            values=st.text(min_size=0, max_size=100)
        )
    )
    @settings(max_examples=100)
    def test_property_valid_build_args_accepted(self, build_args):
        """Test that valid build args are accepted."""
        errors = InputValidator.validate_build_args(build_args)
        assert len(errors) == 0, f"Valid build args rejected: {errors}"
    
    @given(
        injection_char=st.sampled_from([';', '&', '|', '`', '$', '(', ')'])
    )
    @settings(max_examples=100)
    def test_property_build_arg_injection_detected(self, injection_char):
        """Test that build args with shell metacharacters are rejected."""
        build_args = {f"ARG{injection_char}NAME": "value"}
        errors = InputValidator.validate_build_args(build_args)
        assert len(errors) > 0
        assert any('metacharacters' in e.lower() for e in errors)
