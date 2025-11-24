"""Tests for daemon credential validation.

Property 2: Unauthorized user error message
Property 8: Connection credential validation

Feature: daemon-socket-support
Validates: Requirements 1.2, 3.2, 10.2
"""

import os
import sys
import socket
import grp
import pwd
import tempfile
import time
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings, assume

from derpy.daemon.server import DaemonServer, DaemonError


# Check if we're on Linux (daemon only supported on Linux)
IS_LINUX = sys.platform.startswith('linux')

# Check if SO_PEERCRED is available
HAS_SO_PEERCRED = hasattr(socket, 'SO_PEERCRED')

# For non-Linux platforms, we need to mock SO_PEERCRED
if not HAS_SO_PEERCRED:
    # Define SO_PEERCRED constant for testing on non-Linux platforms
    socket.SO_PEERCRED = 17  # Linux value


def get_test_group():
    """Get a valid group name for testing."""
    current_user = pwd.getpwuid(os.getuid())
    primary_gid = current_user.pw_gid
    primary_group = grp.getgrgid(primary_gid).gr_name
    return primary_group


def get_current_user_info():
    """Get current user information."""
    uid = os.getuid()
    user_info = pwd.getpwuid(uid)
    gid = user_info.pw_gid
    username = user_info.pw_name
    return uid, gid, username


class TestCredentialValidation:
    """Unit tests for credential validation."""
    
    def test_validate_authorized_user(self):
        """Test that authorized user passes validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            test_group = get_test_group()
            server = DaemonServer(socket_path=socket_path, group_name=test_group)
            
            # Create a mock socket with valid credentials
            mock_socket = Mock(spec=socket.socket)
            
            # Get current user's credentials
            uid, gid, username = get_current_user_info()
            pid = os.getpid()
            
            # Mock SO_PEERCRED to return current user's credentials
            import struct
            creds = struct.pack('3i', pid, uid, gid)
            mock_socket.getsockopt.return_value = creds
            
            # Mock SO_PEERCRED constant if not on Linux
            with patch.object(socket, 'SO_PEERCRED', 17, create=True):
                # Validate credentials
                is_authorized, error_message = server.validate_client_credentials(mock_socket)
                
                # Should be authorized (current user is in their primary group)
                assert is_authorized
                assert error_message is None
    
    def test_validate_unauthorized_user(self):
        """Test that unauthorized user fails validation.
        
        Property 2: Unauthorized user error message
        Validates: Requirements 1.2, 10.2
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            
            # Use a group that the current user is NOT in
            # We'll use a non-existent group for testing
            server = DaemonServer(socket_path=socket_path, group_name="derpy")
            
            # Create a mock socket with valid credentials but wrong group
            mock_socket = Mock(spec=socket.socket)
            
            # Get current user's credentials
            uid, gid, username = get_current_user_info()
            pid = os.getpid()
            
            # Mock SO_PEERCRED to return current user's credentials
            import struct
            creds = struct.pack('3i', pid, uid, gid)
            mock_socket.getsockopt.return_value = creds
            
            # Mock SO_PEERCRED constant if not on Linux
            with patch.object(socket, 'SO_PEERCRED', 17, create=True):
                # Mock grp.getgrnam to return a group the user is not in
                with patch('grp.getgrnam') as mock_getgrnam:
                    # Create a mock group with a different GID and no members
                    mock_group = Mock()
                    mock_group.gr_gid = 9999  # Different from user's GID
                    mock_group.gr_mem = []  # User not in members list
                    mock_getgrnam.return_value = mock_group
                    
                    # Validate credentials
                    is_authorized, error_message = server.validate_client_credentials(mock_socket)
                    
                    # Should NOT be authorized
                    assert not is_authorized
                    assert error_message is not None
                    assert "Access denied" in error_message
                    assert "derpy" in error_message
                    assert "usermod -aG" in error_message
    
    def test_validate_user_in_supplementary_group(self):
        """Test that user in supplementary group is authorized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            server = DaemonServer(socket_path=socket_path, group_name="derpy")
            
            # Create a mock socket
            mock_socket = Mock(spec=socket.socket)
            
            # Get current user's credentials
            uid, gid, username = get_current_user_info()
            pid = os.getpid()
            
            # Mock SO_PEERCRED
            import struct
            creds = struct.pack('3i', pid, uid, gid)
            mock_socket.getsockopt.return_value = creds
            
            # Mock SO_PEERCRED constant if not on Linux
            with patch.object(socket, 'SO_PEERCRED', 17, create=True):
                # Mock grp.getgrnam to return a group with user in members
                with patch('grp.getgrnam') as mock_getgrnam:
                    mock_group = Mock()
                    mock_group.gr_gid = 9999  # Different from user's primary GID
                    mock_group.gr_mem = [username]  # User IS in members list
                    mock_getgrnam.return_value = mock_group
                    
                    # Validate credentials
                    is_authorized, error_message = server.validate_client_credentials(mock_socket)
                    
                    # Should be authorized (user in supplementary group)
                    assert is_authorized
                    assert error_message is None
    
    def test_validate_nonexistent_group(self):
        """Test validation when group doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            server = DaemonServer(socket_path=socket_path, group_name="nonexistent_group_12345")
            
            # Create a mock socket
            mock_socket = Mock(spec=socket.socket)
            
            # Get current user's credentials
            uid, gid, username = get_current_user_info()
            pid = os.getpid()
            
            # Mock SO_PEERCRED
            import struct
            creds = struct.pack('3i', pid, uid, gid)
            mock_socket.getsockopt.return_value = creds
            
            # Mock SO_PEERCRED constant if not on Linux
            with patch.object(socket, 'SO_PEERCRED', 17, create=True):
                # Validate credentials (grp.getgrnam will raise KeyError)
                is_authorized, error_message = server.validate_client_credentials(mock_socket)
                
                # Should NOT be authorized
                assert not is_authorized
                assert error_message is not None
                assert "does not exist" in error_message
    
    def test_validate_socket_error(self):
        """Test validation when socket operation fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            test_group = get_test_group()
            server = DaemonServer(socket_path=socket_path, group_name=test_group)
            
            # Create a mock socket that raises OSError
            mock_socket = Mock(spec=socket.socket)
            mock_socket.getsockopt.side_effect = OSError("Socket error")
            
            # Mock SO_PEERCRED constant if not on Linux
            with patch.object(socket, 'SO_PEERCRED', 17, create=True):
                # Validate credentials
                is_authorized, error_message = server.validate_client_credentials(mock_socket)
                
                # Should NOT be authorized
                assert not is_authorized
                assert error_message is not None
                assert "Failed to get client credentials" in error_message
    
    def test_validate_platform_not_supported(self):
        """Test validation on non-Linux platform."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            test_group = get_test_group()
            server = DaemonServer(socket_path=socket_path, group_name=test_group)
            
            # Create a mock socket
            mock_socket = Mock(spec=socket.socket)
            
            # Ensure SO_PEERCRED is not available
            with patch.object(socket, 'SO_PEERCRED', side_effect=AttributeError, create=True):
                # Delete the attribute to simulate non-Linux platform
                if hasattr(socket, 'SO_PEERCRED'):
                    delattr(socket, 'SO_PEERCRED')
                
                # Validate credentials
                is_authorized, error_message = server.validate_client_credentials(mock_socket)
                
                # Should NOT be authorized
                assert not is_authorized
                assert error_message is not None
                assert "not supported on this platform" in error_message or "Linux" in error_message


class TestCredentialValidationIntegration:
    """Integration tests for credential validation with real connections."""
    
    def test_authorized_connection_accepted(self):
        """Test that authorized connection is accepted.
        
        Property 8: Connection credential validation
        Validates: Requirements 3.2
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            test_group = get_test_group()
            server = DaemonServer(socket_path=socket_path, group_name=test_group)
            
            try:
                server.start()
                time.sleep(0.1)
                
                # Connect as client (current user should be authorized)
                client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                client_socket.connect(str(socket_path))
                
                # Give server time to validate credentials
                time.sleep(0.2)
                
                # Connection should be accepted (not immediately closed)
                # We can't easily test the validation result directly in integration,
                # but we can verify the connection was established
                assert client_socket.fileno() != -1
                
                client_socket.close()
                
            finally:
                server.stop()


# Property-Based Tests

class TestPropertyBasedCredentialValidation:
    """Property-based tests for credential validation.
    
    Feature: daemon-socket-support, Property 2: Unauthorized user error message
    Feature: daemon-socket-support, Property 8: Connection credential validation
    Validates: Requirements 1.2, 3.2, 10.2
    """
    
    @given(
        uid=st.integers(min_value=1000, max_value=65535),
        gid=st.integers(min_value=1000, max_value=65535),
        pid=st.integers(min_value=1, max_value=65535)
    )
    @settings(max_examples=50, deadline=2000)
    def test_unauthorized_user_gets_error_message(self, uid, gid, pid):
        """
        Property 2: Unauthorized user error message
        For any user not in the derpy group, attempting to connect should
        result in a clear error message indicating they need to be added
        to the derpy group.
        
        Validates: Requirements 1.2, 10.2
        """
        # Skip if uid/gid matches current user (they would be authorized)
        current_uid, current_gid, _ = get_current_user_info()
        assume(uid != current_uid or gid != current_gid)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            server = DaemonServer(socket_path=socket_path, group_name="derpy")
            
            # Create a mock socket
            mock_socket = Mock(spec=socket.socket)
            
            # Mock SO_PEERCRED with random credentials
            import struct
            creds = struct.pack('3i', pid, uid, gid)
            mock_socket.getsockopt.return_value = creds
            
            # Mock SO_PEERCRED constant if not on Linux
            with patch.object(socket, 'SO_PEERCRED', 17, create=True):
                # Mock grp.getgrnam to return a group the user is not in
                with patch('grp.getgrnam') as mock_getgrnam:
                    mock_group = Mock()
                    mock_group.gr_gid = 9999  # Different from user's GID
                    mock_group.gr_mem = []  # User not in members list
                    mock_getgrnam.return_value = mock_group
                    
                    # Mock pwd.getpwuid to return a username
                    with patch('pwd.getpwuid') as mock_getpwuid:
                        mock_user = Mock()
                        mock_user.pw_name = f"user{uid}"
                        mock_getpwuid.return_value = mock_user
                        
                        # Validate credentials
                        is_authorized, error_message = server.validate_client_credentials(mock_socket)
                        
                        # Should NOT be authorized
                        assert not is_authorized, \
                            "User not in derpy group should not be authorized"
                        
                        # Should have error message
                        assert error_message is not None, \
                            "Unauthorized user should receive error message"
                        
                        # Error message should contain helpful information
                        assert "Access denied" in error_message or "not in" in error_message, \
                            "Error message should indicate access denial"
                        
                        assert "derpy" in error_message, \
                            "Error message should mention the derpy group"
                        
                        assert "usermod" in error_message or "add" in error_message.lower(), \
                            "Error message should suggest how to fix the issue"
    
    @given(
        uid=st.integers(min_value=1000, max_value=65535),
        gid=st.integers(min_value=1000, max_value=65535),
        pid=st.integers(min_value=1, max_value=65535)
    )
    @settings(max_examples=50, deadline=2000)
    def test_connection_credential_validation(self, uid, gid, pid):
        """
        Property 8: Connection credential validation
        For any socket connection attempt, the daemon should verify the
        connecting user is in the derpy group using socket credentials.
        
        Validates: Requirements 3.2
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            server = DaemonServer(socket_path=socket_path, group_name="derpy")
            
            # Create a mock socket
            mock_socket = Mock(spec=socket.socket)
            
            # Mock SO_PEERCRED
            import struct
            creds = struct.pack('3i', pid, uid, gid)
            mock_socket.getsockopt.return_value = creds
            
            # Mock SO_PEERCRED constant if not on Linux
            with patch.object(socket, 'SO_PEERCRED', 17, create=True):
                # Mock grp.getgrnam
                with patch('grp.getgrnam') as mock_getgrnam:
                    mock_group = Mock()
                    mock_group.gr_gid = gid  # Match user's GID for authorization
                    mock_group.gr_mem = []
                    mock_getgrnam.return_value = mock_group
                    
                    # Validate credentials
                    is_authorized, error_message = server.validate_client_credentials(mock_socket)
                    
                    # Verify SO_PEERCRED was called to get credentials
                    mock_socket.getsockopt.assert_called_once()
                    call_args = mock_socket.getsockopt.call_args
                    assert call_args[0][0] == socket.SOL_SOCKET
                    assert call_args[0][1] == 17  # Mocked SO_PEERCRED value
                    
                    # Verify group lookup was performed
                    mock_getgrnam.assert_called_once_with("derpy")
                    
                    # If GID matches, should be authorized
                    if gid == mock_group.gr_gid:
                        assert is_authorized, \
                            "User with matching GID should be authorized"
                        assert error_message is None
    
    @given(
        username=st.text(min_size=1, max_size=32, alphabet=st.characters(
            whitelist_categories=('Ll', 'Lu', 'Nd'),
            whitelist_characters='_-'
        ))
    )
    @settings(max_examples=30, deadline=2000)
    def test_supplementary_group_authorization(self, username):
        """
        Property 8: Connection credential validation (supplementary groups)
        For any user listed in the derpy group members, they should be
        authorized even if derpy is not their primary group.
        
        Validates: Requirements 3.2
        """
        # Filter out invalid usernames
        assume(len(username) > 0)
        assume(username[0].isalpha() or username[0] == '_')
        
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            server = DaemonServer(socket_path=socket_path, group_name="derpy")
            
            # Create a mock socket
            mock_socket = Mock(spec=socket.socket)
            
            # Use different GID than derpy group
            uid = 5000
            gid = 5000  # Primary group, not derpy
            pid = 1234
            
            # Mock SO_PEERCRED
            import struct
            creds = struct.pack('3i', pid, uid, gid)
            mock_socket.getsockopt.return_value = creds
            
            # Mock SO_PEERCRED constant if not on Linux
            with patch.object(socket, 'SO_PEERCRED', 17, create=True):
                # Mock grp.getgrnam - user is in supplementary group
                with patch('grp.getgrnam') as mock_getgrnam:
                    mock_group = Mock()
                    mock_group.gr_gid = 9999  # Different from user's primary GID
                    mock_group.gr_mem = [username]  # User IS in members list
                    mock_getgrnam.return_value = mock_group
                    
                    # Mock pwd.getpwuid to return the username
                    with patch('pwd.getpwuid') as mock_getpwuid:
                        mock_user = Mock()
                        mock_user.pw_name = username
                        mock_getpwuid.return_value = mock_user
                        
                        # Validate credentials
                        is_authorized, error_message = server.validate_client_credentials(mock_socket)
                        
                        # Should be authorized (user in supplementary group)
                        assert is_authorized, \
                            f"User {username} in derpy group members should be authorized"
                        
                        assert error_message is None, \
                            "Authorized user should not receive error message"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
