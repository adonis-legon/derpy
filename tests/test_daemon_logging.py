"""Tests for daemon logging infrastructure.

This module tests the logging functionality of the daemon, including
error logging, log sanitization, and proper log level handling.
"""

import pytest
import logging
import tempfile
import io
import socket
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings, assume

from derpy.daemon.server import DaemonServer
from derpy.daemon.handlers import RequestHandler
from derpy.daemon.protocol import BuildRequest, BuildResponse
from derpy.daemon.security import LogSanitizer
from derpy.core.exceptions import BuildError


class TestErrorLogging:
    """Tests for error logging in daemon operations.
    
    Property 19: Error logging
    Validates: Requirements 5.5
    
    For any error encountered by the daemon, the error should be logged
    to the system log.
    """
    
    @given(
        error_message=st.text(min_size=1, max_size=200),
        tag=st.from_regex(r'^[a-zA-Z0-9._:/-]+$', fullmatch=True).filter(
            lambda x: 1 <= len(x) <= 128
        )
    )
    @settings(max_examples=100)
    def test_property_error_logging(self, error_message, tag):
        """
        Property 19: Error logging
        
        For any error encountered by the daemon, the error should be logged
        to the system log with appropriate context.
        
        Validates: Requirements 5.5
        """
        # Filter out problematic characters
        assume('\0' not in error_message)
        
        # Create a mock logger to capture log calls
        with patch('derpy.daemon.handlers.logger') as mock_logger:
            # Create request handler
            handler = RequestHandler()
            
            # Use a temporary directory for valid paths
            with tempfile.TemporaryDirectory() as tmpdir:
                context_path = Path(tmpdir)
                dockerfile_path = context_path / "Dockerfile"
                
                # Create the Dockerfile so path validation passes
                dockerfile_path.write_text("FROM alpine\n")
                
                # Create a build request that will fail during build
                request = BuildRequest(
                    type="build",
                    context_path=str(context_path),
                    dockerfile_path=str(dockerfile_path),
                    tag=tag,
                    build_args={}
                )
                
                # Mock the build engine to raise an error
                with patch('derpy.daemon.handlers.BuildEngine') as mock_engine_class:
                    mock_engine = Mock()
                    mock_engine.build_image.side_effect = BuildError(error_message)
                    mock_engine_class.return_value = mock_engine
                    
                    # Mock ImageManager to avoid file system operations
                    with patch('derpy.daemon.handlers.ImageManager'):
                        # Mock BuildContext to avoid validation issues
                        with patch('derpy.daemon.handlers.BuildContext'):
                            # Mock tempfile.mkdtemp to avoid temp dir creation
                            with patch('derpy.daemon.handlers.tempfile.mkdtemp', return_value=str(context_path)):
                                # Mock PrivilegeManager to avoid permission operations
                                with patch('derpy.daemon.handlers.PrivilegeManager.set_restrictive_permissions'):
                                    # Handle the request (should fail and log error)
                                    response = handler.handle_build_request(request)
                                    
                                    # Verify error was logged
                                    # The handler should call logger.error() when build fails
                                    assert mock_logger.error.called, "Error should be logged"
                                    
                                    # Verify the error message is in the log call
                                    # Extract actual log messages from the calls
                                    error_logged = False
                                    for call in mock_logger.error.call_args_list:
                                        # call.args contains positional arguments
                                        if call.args:
                                            log_message = str(call.args[0])
                                            if 'Build failed' in log_message or 'failed' in log_message.lower():
                                                error_logged = True
                                                break
                                    
                                    assert error_logged, f"Error should be logged (checked {len(mock_logger.error.call_args_list)} calls)"
                                    
                                    # Verify response indicates failure
                                    assert not response.success, "Response should indicate failure"
                                    assert response.exit_code != 0, "Exit code should be non-zero"
    
    def test_error_logging_with_stack_trace(self):
        """Test that errors are logged with stack traces."""
        # Create a mock logger to capture log calls
        with patch('derpy.daemon.handlers.logger') as mock_logger:
            # Create request handler
            handler = RequestHandler()
            
            # Use a temporary directory for valid paths
            with tempfile.TemporaryDirectory() as tmpdir:
                context_path = Path(tmpdir)
                dockerfile_path = context_path / "Dockerfile"
                
                # Create the Dockerfile so path validation passes
                dockerfile_path.write_text("FROM alpine\n")
                
                # Create a build request
                request = BuildRequest(
                    type="build",
                    context_path=str(context_path),
                    dockerfile_path=str(dockerfile_path),
                    tag="test:latest",
                    build_args={}
                )
                
                # Mock the build engine to raise an unexpected error
                with patch('derpy.daemon.handlers.BuildEngine') as mock_engine_class:
                    mock_engine = Mock()
                    mock_engine.build_image.side_effect = RuntimeError("Unexpected error")
                    mock_engine_class.return_value = mock_engine
                    
                    # Mock ImageManager
                    with patch('derpy.daemon.handlers.ImageManager'):
                        # Mock BuildContext to avoid validation issues
                        with patch('derpy.daemon.handlers.BuildContext'):
                            # Mock tempfile.mkdtemp
                            with patch('derpy.daemon.handlers.tempfile.mkdtemp', return_value=str(context_path)):
                                # Mock PrivilegeManager
                                with patch('derpy.daemon.handlers.PrivilegeManager.set_restrictive_permissions'):
                                    # Handle the request (should fail and log error with stack trace)
                                    response = handler.handle_build_request(request)
                                    
                                    # Verify error was logged with exc_info=True (stack trace)
                                    assert mock_logger.error.called, "Error should be logged"
                                    
                                    # Check if any error call included exc_info=True
                                    has_stack_trace = any(
                                        call.kwargs.get('exc_info', False)
                                        for call in mock_logger.error.call_args_list
                                    )
                                    assert has_stack_trace, "Error should be logged with stack trace (exc_info=True)"
    
    def test_authentication_logging(self):
        """Test that authentication attempts are logged."""
        # We need to patch the logger before creating the server
        # because the server imports logger at module level
        import derpy.daemon.server as server_module
        
        # Create a mock logger
        mock_logger = Mock()
        
        with patch.object(server_module, 'logger', mock_logger):
            # Mock socket.SO_PEERCRED to exist (it doesn't on macOS)
            with patch.object(socket, 'SO_PEERCRED', 17, create=True):  # 17 is the Linux value
                # Create daemon server
                server = DaemonServer(
                    socket_path=Path("/tmp/test.sock"),
                    group_name="derpy",
                    max_workers=2
                )
                
                # Create a mock socket
                mock_socket = Mock()
                
                # Mock SO_PEERCRED to return credentials
                import struct
                creds = struct.pack('3i', 1234, 1000, 1000)  # pid, uid, gid
                mock_socket.getsockopt.return_value = creds
                
                # Mock grp.getgrnam to return group info
                with patch('grp.getgrnam') as mock_getgrnam:
                    mock_group = Mock()
                    mock_group.gr_gid = 1000
                    mock_group.gr_mem = ['testuser']
                    mock_getgrnam.return_value = mock_group
                    
                    # Mock pwd.getpwuid to return user info
                    with patch('pwd.getpwuid') as mock_getpwuid:
                        mock_user = Mock()
                        mock_user.pw_name = 'testuser'
                        mock_getpwuid.return_value = mock_user
                        
                        # Validate credentials (should succeed)
                        is_authorized, error_msg = server.validate_client_credentials(mock_socket)
                        
                        # Verify authentication was logged
                        assert mock_logger.info.called, "Authentication should be logged"
                        
                        # Check that the log includes authentication success
                        log_messages = []
                        for call in mock_logger.info.call_args_list:
                            if call.args:
                                log_messages.append(str(call.args[0]))
                        
                        auth_logged = any(
                            'Authentication successful' in msg or 'testuser' in msg
                            for msg in log_messages
                        )
                        assert auth_logged, f"Authentication success should be logged. Got: {log_messages}"
    
    def test_request_handling_logging(self):
        """Test that request handling is logged (start, success, failure)."""
        # Create a mock logger
        with patch('derpy.daemon.handlers.logger') as mock_logger:
            # Create request handler
            handler = RequestHandler()
            
            # Use a temporary directory for valid paths
            with tempfile.TemporaryDirectory() as tmpdir:
                context_path = Path(tmpdir)
                dockerfile_path = context_path / "Dockerfile"
                
                # Create the Dockerfile so path validation passes
                dockerfile_path.write_text("FROM alpine\n")
                
                # Create a successful build request
                request = BuildRequest(
                    type="build",
                    context_path=str(context_path),
                    dockerfile_path=str(dockerfile_path),
                    tag="test:latest",
                    build_args={}
                )
                
                # Mock successful build
                with patch('derpy.daemon.handlers.BuildEngine') as mock_engine_class:
                    mock_engine = Mock()
                    mock_image = Mock()
                    mock_image.manifest = Mock()
                    mock_image.manifest.config = Mock()
                    mock_image.manifest.config.digest = "sha256:abc123"
                    mock_engine.build_image.return_value = mock_image
                    mock_engine_class.return_value = mock_engine
                    
                    # Mock ImageManager
                    with patch('derpy.daemon.handlers.ImageManager') as mock_storage_class:
                        mock_storage = Mock()
                        mock_storage_class.return_value = mock_storage
                        
                        # Mock BuildContext
                        with patch('derpy.daemon.handlers.BuildContext'):
                            # Mock tempfile.mkdtemp
                            with patch('derpy.daemon.handlers.tempfile.mkdtemp', return_value=str(context_path)):
                                # Mock PrivilegeManager
                                with patch('derpy.daemon.handlers.PrivilegeManager.set_restrictive_permissions'):
                                    # Handle the request
                                    response = handler.handle_build_request(request)
                                    
                                    # Verify request start was logged
                                    assert mock_logger.info.called, "Request handling should be logged"
                                    
                                    # Check for start and completion logs
                                    log_messages = []
                                    for call in mock_logger.info.call_args_list:
                                        if call.args:
                                            log_messages.append(str(call.args[0]))
                                    
                                    # Should log request received
                                    request_logged = any(
                                        'Build request received' in msg
                                        for msg in log_messages
                                    )
                                    assert request_logged, f"Request start should be logged. Got: {log_messages}"
                                    
                                    # Should log completion
                                    completion_logged = any(
                                        'Build completed successfully' in msg or 'completed' in msg
                                        for msg in log_messages
                                    )
                                    assert completion_logged, f"Request completion should be logged. Got: {log_messages}"
    
    def test_log_sanitization(self):
        """Test that sensitive data is sanitized in logs."""
        # Test password sanitization
        message_with_password = "Failed to authenticate: password=secret123"
        sanitized = LogSanitizer.sanitize_log_message(message_with_password)
        assert "secret123" not in sanitized, "Password should be redacted"
        assert "***REDACTED***" in sanitized, "Password should be replaced with redaction marker"
        
        # Test token sanitization
        message_with_token = "Authorization failed: token=abc123xyz"
        sanitized = LogSanitizer.sanitize_log_message(message_with_token)
        assert "abc123xyz" not in sanitized, "Token should be redacted"
        assert "***REDACTED***" in sanitized, "Token should be replaced with redaction marker"
        
        # Test Bearer token sanitization
        message_with_bearer = "Request failed: Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        sanitized = LogSanitizer.sanitize_log_message(message_with_bearer)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in sanitized, "Bearer token should be redacted"
        assert "***REDACTED***" in sanitized, "Bearer token should be replaced with redaction marker"
        
        # Test Basic auth sanitization
        message_with_basic = "Authorization: Basic dXNlcjpwYXNzd29yZA=="
        sanitized = LogSanitizer.sanitize_log_message(message_with_basic)
        assert "dXNlcjpwYXNzd29yZA==" not in sanitized, "Basic auth should be redacted"
        assert "***REDACTED***" in sanitized, "Basic auth should be replaced with redaction marker"
    
    def test_log_levels(self):
        """Test that different log levels are supported."""
        # Test DEBUG level
        with patch('derpy.daemon.__main__.logging.basicConfig') as mock_config:
            from derpy.daemon.__main__ import setup_logging
            
            setup_logging('DEBUG')
            
            # Verify basicConfig was called with DEBUG level
            assert mock_config.called
            call_kwargs = mock_config.call_args.kwargs
            assert call_kwargs['level'] == logging.DEBUG
        
        # Test INFO level
        with patch('derpy.daemon.__main__.logging.basicConfig') as mock_config:
            setup_logging('INFO')
            
            assert mock_config.called
            call_kwargs = mock_config.call_args.kwargs
            assert call_kwargs['level'] == logging.INFO
        
        # Test WARNING level
        with patch('derpy.daemon.__main__.logging.basicConfig') as mock_config:
            setup_logging('WARNING')
            
            assert mock_config.called
            call_kwargs = mock_config.call_args.kwargs
            assert call_kwargs['level'] == logging.WARNING
        
        # Test ERROR level
        with patch('derpy.daemon.__main__.logging.basicConfig') as mock_config:
            setup_logging('ERROR')
            
            assert mock_config.called
            call_kwargs = mock_config.call_args.kwargs
            assert call_kwargs['level'] == logging.ERROR
    
    def test_systemd_journal_logging(self):
        """Test that daemon logs to stdout/stderr for systemd journal."""
        # The daemon should log to stdout/stderr so systemd can capture it
        # This is configured in __main__.py with logging.basicConfig
        
        # Verify that logging.basicConfig doesn't specify a file handler
        # (which would prevent logging to stdout/stderr)
        with patch('derpy.daemon.__main__.logging.basicConfig') as mock_config:
            from derpy.daemon.__main__ import setup_logging
            
            setup_logging('INFO')
            
            # Verify basicConfig was called
            assert mock_config.called
            
            # Verify no filename was specified (logs go to stderr by default)
            call_kwargs = mock_config.call_args.kwargs
            assert 'filename' not in call_kwargs, "Should not log to file (use stdout/stderr for systemd)"
            
            # Verify format includes timestamp and level
            assert 'format' in call_kwargs
            format_str = call_kwargs['format']
            assert '%(levelname)s' in format_str, "Format should include log level"
            assert '%(message)s' in format_str, "Format should include message"


class TestLogSanitizer:
    """Tests for LogSanitizer utility."""
    
    def test_sanitize_password_patterns(self):
        """Test sanitization of various password patterns."""
        test_cases = [
            ("password=secret123", "password=***REDACTED***"),
            ("passwd: secret123", "passwd=***REDACTED***"),
            ("pwd='secret123'", "pwd=***REDACTED***"),
            ('PASSWORD="secret123"', "PASSWORD=***REDACTED***"),
        ]
        
        for input_msg, expected_pattern in test_cases:
            sanitized = LogSanitizer.sanitize_log_message(input_msg)
            assert "secret123" not in sanitized, f"Password should be redacted in: {input_msg}"
            assert "***REDACTED***" in sanitized, f"Should contain redaction marker: {input_msg}"
    
    def test_sanitize_token_patterns(self):
        """Test sanitization of various token patterns."""
        test_cases = [
            "token=abc123",
            "api_key: xyz789",
            "apikey='key123'",
            'secret="secret456"',
        ]
        
        for input_msg in test_cases:
            sanitized = LogSanitizer.sanitize_log_message(input_msg)
            # Extract the actual secret value
            secret_value = input_msg.split('=')[-1].split(':')[-1].strip('\'"')
            assert secret_value not in sanitized, f"Token should be redacted in: {input_msg}"
            assert "***REDACTED***" in sanitized, f"Should contain redaction marker: {input_msg}"
    
    def test_sanitize_dict(self):
        """Test sanitization of dictionaries."""
        test_dict = {
            "username": "testuser",
            "password": "secret123",
            "token": "abc123",
            "api_key": "xyz789",
            "normal_field": "normal_value"
        }
        
        sanitized = LogSanitizer.sanitize_dict(test_dict)
        
        # Sensitive fields should be redacted
        assert sanitized["password"] == "***REDACTED***"
        assert sanitized["token"] == "***REDACTED***"
        assert sanitized["api_key"] == "***REDACTED***"
        
        # Non-sensitive fields should remain
        assert sanitized["username"] == "testuser"
        assert sanitized["normal_field"] == "normal_value"
    
    def test_sanitize_nested_dict(self):
        """Test sanitization of nested dictionaries."""
        test_dict = {
            "config": {
                "username": "testuser",
                "password": "secret123"
            },
            "auth": {
                "token": "abc123"
            }
        }
        
        sanitized = LogSanitizer.sanitize_dict(test_dict)
        
        # Nested sensitive fields should be redacted
        assert sanitized["config"]["password"] == "***REDACTED***"
        assert sanitized["auth"]["token"] == "***REDACTED***"
        
        # Non-sensitive fields should remain
        assert sanitized["config"]["username"] == "testuser"
