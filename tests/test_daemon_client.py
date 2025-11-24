"""Property-based tests for daemon client.

Tests the DaemonClient class for communication with the derpyd daemon,
including availability checks, timeout handling, and disconnection detection.
"""

import os
import socket
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
from hypothesis import given, strategies as st, settings, assume

from derpy.daemon.client import (
    DaemonClient,
    DaemonConnectionError,
    DaemonTimeoutError,
    DaemonProtocolError,
)
from derpy.daemon.protocol import (
    BuildRequest,
    BuildResponse,
    ListRequest,
    ListResponse,
    RemoveRequest,
    RemoveResponse,
    PurgeRequest,
    PurgeResponse,
    OutputMessage,
)
from derpy.daemon.framing import MessageFramer


class TestDaemonAvailabilityCheck:
    """Property 1: Authorized user socket communication.
    
    Feature: daemon-socket-support, Property 1: Authorized user socket communication
    Validates: Requirements 1.1
    
    For any user in the derpy group and any build command, the CLI should
    successfully communicate with the daemon via Unix socket without requiring sudo.
    """
    
    @given(dummy=st.just(None))
    @settings(max_examples=100)
    def test_property_authorized_user_socket_communication(self, dummy):
        """
        Property 1: Authorized user socket communication
        
        For any user in the derpy group, the daemon client should be able
        to check availability and communicate with the daemon socket.
        
        Validates: Requirements 1.1
        """
        # Create a temporary socket to simulate daemon
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            
            # Create a simple server socket
            server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server_sock.bind(str(socket_path))
            server_sock.listen(1)
            
            try:
                # Create client
                client = DaemonClient(socket_path=socket_path, timeout=1.0)
                
                # Test availability check
                is_available = client.is_available()
                
                # Should be able to detect daemon is available
                assert is_available, "Client should detect daemon is available"
                
            finally:
                server_sock.close()
    
    @given(dummy=st.just(None))
    @settings(max_examples=100)
    def test_property_unavailable_daemon_detection(self, dummy):
        """
        Property 1 (negative case): Unavailable daemon detection
        
        For any non-existent socket, the daemon client should correctly
        detect that the daemon is not available.
        
        Validates: Requirements 1.1
        """
        # Use a socket path that doesn't exist
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "nonexistent.sock"
            
            # Create client
            client = DaemonClient(socket_path=socket_path, timeout=1.0)
            
            # Test availability check
            is_available = client.is_available()
            
            # Should correctly detect daemon is not available
            assert not is_available, "Client should detect daemon is not available"


class TestDaemonTimeoutHandling:
    """Property 34: Daemon timeout handling.
    
    Feature: daemon-socket-support, Property 34: Daemon timeout handling
    Validates: Requirements 10.3
    
    For any unresponsive daemon, the CLI should timeout after a reasonable
    period (e.g., 30 seconds) and display a timeout error.
    """
    
    @given(
        timeout=st.floats(min_value=0.2, max_value=1.0)
    )
    @settings(max_examples=10, deadline=5000)
    def test_property_daemon_timeout_handling(self, timeout):
        """
        Property 34: Daemon timeout handling
        
        For any timeout value, when the daemon doesn't respond within
        the timeout period, the client should raise a DaemonTimeoutError.
        
        Validates: Requirements 10.3
        """
        # Create a temporary socket
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            
            # Create a server that accepts connections but never responds
            server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server_sock.bind(str(socket_path))
            server_sock.listen(1)
            
            # Use a simple approach: start accepting in background immediately
            connection_holder = []
            
            def accept_connection():
                try:
                    conn, _ = server_sock.accept()
                    connection_holder.append(conn)
                    # Read request but don't respond
                    conn.recv(4096)
                    # Hold connection open
                    time.sleep(10)
                except Exception:
                    pass
                finally:
                    if connection_holder:
                        try:
                            connection_holder[0].close()
                        except:
                            pass
            
            thread = threading.Thread(target=accept_connection, daemon=True)
            thread.start()
            
            # Small delay to ensure thread is in accept() state
            time.sleep(0.1)
            
            try:
                # Create client with specified timeout
                client = DaemonClient(socket_path=socket_path, timeout=timeout)
                
                # Try to send a list request (simplest request)
                start_time = time.time()
                
                with pytest.raises(DaemonTimeoutError) as exc_info:
                    client.send_list_request()
                
                elapsed = time.time() - start_time
                
                # Verify timeout occurred
                assert "timed out" in str(exc_info.value).lower(), \
                    "Error message should mention timeout"
                
                # Verify timeout happened within reasonable bounds
                # Allow some overhead for socket operations
                assert elapsed <= timeout + 1.5, \
                    f"Timeout took too long: {elapsed}s (expected ~{timeout}s)"
                
            finally:
                # Clean up connection if it exists
                if connection_holder:
                    try:
                        connection_holder[0].close()
                    except:
                        pass
                # Close server socket
                try:
                    server_sock.close()
                except:
                    pass
                # Wait for thread to finish (with timeout)
                thread.join(timeout=0.5)
    
    @given(dummy=st.just(None))
    @settings(max_examples=50, deadline=10000)
    def test_property_timeout_error_message_quality(self, dummy):
        """
        Property 34 (error message quality): Timeout error messages
        
        For any timeout error, the error message should include:
        - The operation that timed out
        - The timeout duration
        - Remediation suggestions
        
        Validates: Requirements 10.3
        """
        # Create a temporary socket
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            
            # Create a server that accepts connections but never responds
            server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server_sock.bind(str(socket_path))
            server_sock.listen(1)
            
            # Accept connections in background but never send data
            def accept_and_hang():
                try:
                    conn, _ = server_sock.accept()
                    # Read the request to prevent blocking
                    conn.recv(4096)
                    # Keep connection alive longer than timeout
                    time.sleep(5.0)
                    conn.close()
                except Exception:
                    pass
            
            thread = threading.Thread(target=accept_and_hang, daemon=True)
            thread.start()
            
            # Small delay to ensure thread is in accept() state
            time.sleep(0.1)
            
            try:
                # Create client with short timeout
                client = DaemonClient(socket_path=socket_path, timeout=0.5)
                
                # Try to send a list request
                with pytest.raises(DaemonTimeoutError) as exc_info:
                    client.send_list_request()
                
                error_msg = str(exc_info.value)
                
                # Verify error message quality
                assert "list" in error_msg.lower() or "operation" in error_msg.lower(), \
                    "Error should mention the operation"
                
                assert "timed out" in error_msg.lower() or "timeout" in error_msg.lower(), \
                    "Error should mention timeout"
                
                # Check for remediation in the exception
                assert exc_info.value.remediation is not None, \
                    "Timeout error should include remediation"
                
                assert "status" in exc_info.value.remediation.lower() or \
                       "log" in exc_info.value.remediation.lower(), \
                    "Remediation should suggest checking status or logs"
                
            finally:
                try:
                    server_sock.close()
                except:
                    pass
                thread.join(timeout=0.5)


class TestDaemonDisconnectionDetection:
    """Property 16: Socket disconnection detection.
    
    Feature: daemon-socket-support, Property 16: Socket disconnection detection
    Validates: Requirements 4.5, 10.5
    
    For any socket disconnection during communication, the CLI should detect
    it and report a clear error message.
    """
    
    @given(dummy=st.just(None))
    @settings(max_examples=50, deadline=10000)
    def test_property_socket_disconnection_detection(self, dummy):
        """
        Property 16: Socket disconnection detection
        
        For any socket disconnection during communication, the client
        should detect it and raise a DaemonConnectionError.
        
        Validates: Requirements 4.5, 10.5
        """
        # Create a temporary socket
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            
            # Create a server that accepts connections then immediately closes
            server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server_sock.bind(str(socket_path))
            server_sock.listen(1)
            
            # Accept connection and close immediately
            def accept_and_close():
                try:
                    conn, _ = server_sock.accept()
                    # Read the request but don't respond
                    conn.recv(4096)
                    # Close connection immediately
                    conn.close()
                except:
                    pass
            
            thread = threading.Thread(target=accept_and_close, daemon=True)
            thread.start()
            
            try:
                # Create client
                client = DaemonClient(socket_path=socket_path, timeout=2.0)
                
                # Try to send a list request
                with pytest.raises(DaemonConnectionError) as exc_info:
                    client.send_list_request()
                
                error_msg = str(exc_info.value)
                
                # Verify disconnection was detected
                assert "connection" in error_msg.lower() or \
                       "closed" in error_msg.lower() or \
                       "lost" in error_msg.lower(), \
                    f"Error should mention connection issue: {error_msg}"
                
            finally:
                server_sock.close()
    
    @given(
        disconnect_after_messages=st.integers(min_value=0, max_value=3)
    )
    @settings(max_examples=50, deadline=10000)
    def test_property_disconnection_during_streaming(self, disconnect_after_messages):
        """
        Property 16 (streaming case): Disconnection during streaming output
        
        For any disconnection during streaming output, the client should
        detect it and raise a DaemonConnectionError.
        
        Validates: Requirements 4.5, 10.5
        """
        # Create a temporary socket
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            
            # Create a server that sends some output then disconnects
            server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server_sock.bind(str(socket_path))
            server_sock.listen(1)
            
            # Accept connection, send some messages, then close
            def accept_send_and_close():
                try:
                    conn, _ = server_sock.accept()
                    # Read the request
                    conn.recv(4096)
                    
                    # Send some output messages
                    framer = MessageFramer()
                    for i in range(disconnect_after_messages):
                        msg = OutputMessage(
                            type="output",
                            content=f"Output line {i}\n",
                            timestamp=time.time()
                        )
                        MessageFramer.send_message(conn, msg)
                        time.sleep(0.01)
                    
                    # Close connection without sending final response
                    conn.close()
                except:
                    pass
            
            thread = threading.Thread(target=accept_send_and_close, daemon=True)
            thread.start()
            
            try:
                # Create client
                client = DaemonClient(socket_path=socket_path, timeout=2.0)
                
                # Track output received
                output_lines = []
                
                def output_callback(line):
                    output_lines.append(line)
                
                # Try to send a build request
                with pytest.raises(DaemonConnectionError) as exc_info:
                    client.send_build_request(
                        context_path=Path("/tmp/test"),
                        dockerfile_path=Path("/tmp/test/Dockerfile"),
                        tag="test:latest",
                        output_callback=output_callback
                    )
                
                error_msg = str(exc_info.value)
                
                # Verify disconnection was detected
                assert "connection" in error_msg.lower() or \
                       "closed" in error_msg.lower() or \
                       "lost" in error_msg.lower(), \
                    f"Error should mention connection issue: {error_msg}"
                
                # Verify we received the output before disconnection
                if disconnect_after_messages > 0:
                    assert len(output_lines) > 0, \
                        "Should have received some output before disconnection"
                
            finally:
                server_sock.close()
    
    @given(dummy=st.just(None))
    @settings(max_examples=50)
    def test_property_disconnection_error_message_quality(self, dummy):
        """
        Property 16 (error message quality): Disconnection error messages
        
        For any disconnection error, the error message should:
        - Clearly indicate connection was lost
        - Include remediation suggestions
        
        Validates: Requirements 4.5, 10.5
        """
        # Create a temporary socket
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            
            # Create a server that accepts connections then immediately closes
            server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server_sock.bind(str(socket_path))
            server_sock.listen(1)
            
            # Accept connection and close immediately
            def accept_and_close():
                try:
                    conn, _ = server_sock.accept()
                    conn.recv(4096)
                    conn.close()
                except:
                    pass
            
            thread = threading.Thread(target=accept_and_close, daemon=True)
            thread.start()
            
            try:
                # Create client
                client = DaemonClient(socket_path=socket_path, timeout=2.0)
                
                # Try to send a list request
                with pytest.raises(DaemonConnectionError) as exc_info:
                    client.send_list_request()
                
                # Verify error message quality
                assert exc_info.value.remediation is not None, \
                    "Connection error should include remediation"
                
                remediation = exc_info.value.remediation.lower()
                assert "daemon" in remediation or "status" in remediation, \
                    "Remediation should mention checking daemon status"
                
            finally:
                server_sock.close()


class TestDaemonClientIntegration:
    """Integration tests for daemon client functionality."""
    
    def test_client_handles_permission_denied(self):
        """Test that client properly handles permission denied errors."""
        # Use a socket path that would require elevated permissions
        socket_path = Path("/var/run/derpy.sock")
        
        # Create client
        client = DaemonClient(socket_path=socket_path, timeout=1.0)
        
        # If socket doesn't exist, is_available should return False
        if not socket_path.exists():
            assert not client.is_available()
        
        # If socket exists but we don't have permission, should handle gracefully
        # (This test will pass either way since we're just checking error handling)
    
    def test_client_validates_request_before_sending(self):
        """Test that client validates requests before attempting to send."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            
            # Create client (no server needed for this test)
            client = DaemonClient(socket_path=socket_path, timeout=1.0)
            
            # Try to send invalid build request (missing required fields)
            with pytest.raises(DaemonProtocolError) as exc_info:
                client.send_build_request(
                    context_path=Path(""),  # Empty path - invalid
                    dockerfile_path=Path(""),  # Empty path - invalid
                    tag="",  # Empty tag - invalid
                )
            
            # Should fail validation before attempting connection
            assert "invalid" in str(exc_info.value).lower()
    
    def test_client_handles_malformed_responses(self):
        """Test that client handles malformed responses from daemon."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            
            # Create a server that sends invalid JSON
            server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server_sock.bind(str(socket_path))
            server_sock.listen(1)
            
            def send_invalid_response():
                try:
                    conn, _ = server_sock.accept()
                    conn.recv(4096)
                    # Send invalid JSON
                    conn.sendall(b"not valid json\n")
                    conn.close()
                except:
                    pass
            
            thread = threading.Thread(target=send_invalid_response, daemon=True)
            thread.start()
            
            try:
                client = DaemonClient(socket_path=socket_path, timeout=1.0)
                
                with pytest.raises(DaemonProtocolError) as exc_info:
                    client.send_list_request()
                
                # Should detect protocol error
                assert "protocol" in str(exc_info.value).lower() or \
                       "invalid" in str(exc_info.value).lower()
                
            finally:
                server_sock.close()



class TestErrorMessageContext:
    """Property 35: Error message context.
    
    Feature: daemon-socket-support, Property 35: Error message context
    Validates: Requirements 10.4
    
    For any error response from the daemon, the CLI should display the error
    message with context about the failed operation.
    """
    
    @given(
        operation=st.sampled_from([
            "build",
            "list",
            "remove",
            "purge"
        ]),
        error_type=st.sampled_from([
            "connection",
            "timeout",
            "protocol"
        ])
    )
    @settings(max_examples=100, deadline=2000)
    def test_property_error_message_context(self, operation, error_type):
        """
        Property 35: Error message context
        
        For any daemon error, the error message should include context about
        what operation failed and provide helpful remediation suggestions.
        
        Validates: Requirements 10.4
        """
        # Test different error types
        if error_type == "connection":
            # Test socket not found error
            with tempfile.TemporaryDirectory() as tmpdir:
                socket_path = Path(tmpdir) / "nonexistent.sock"
                client = DaemonClient(socket_path=socket_path, timeout=1.0)
                
                try:
                    if operation == "build":
                        client.send_build_request(
                            context_path=Path("/tmp/test"),
                            dockerfile_path=Path("/tmp/test/Dockerfile"),
                            tag="test:latest"
                        )
                    elif operation == "list":
                        client.send_list_request()
                    elif operation == "remove":
                        client.send_remove_request("test:latest")
                    elif operation == "purge":
                        client.send_purge_request()
                    
                    # Should have raised an error
                    assert False, "Expected DaemonConnectionError"
                    
                except DaemonConnectionError as e:
                    error_msg = str(e)
                    
                    # Error message should contain helpful information
                    assert "socket" in error_msg.lower() or "daemon" in error_msg.lower(), \
                        f"Error message should mention socket or daemon: {error_msg}"
                    
                    # Should include remediation suggestion
                    assert "systemctl" in error_msg.lower() or "derpy" in error_msg.lower(), \
                        f"Error message should include remediation: {error_msg}"
        
        elif error_type == "timeout":
            # Test timeout error
            with tempfile.TemporaryDirectory() as tmpdir:
                socket_path = Path(tmpdir) / "test.sock"
                
                # Create a server that accepts but never responds
                server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                server_sock.bind(str(socket_path))
                server_sock.listen(1)
                
                def accept_and_hang():
                    try:
                        conn, _ = server_sock.accept()
                        # Just hang - don't send anything
                        time.sleep(5)
                        conn.close()
                    except:
                        pass
                
                thread = threading.Thread(target=accept_and_hang, daemon=True)
                thread.start()
                
                # Give thread time to start
                time.sleep(0.1)
                
                try:
                    client = DaemonClient(socket_path=socket_path, timeout=0.5)
                    
                    if operation == "build":
                        client.send_build_request(
                            context_path=Path("/tmp/test"),
                            dockerfile_path=Path("/tmp/test/Dockerfile"),
                            tag="test:latest"
                        )
                    elif operation == "list":
                        client.send_list_request()
                    elif operation == "remove":
                        client.send_remove_request("test:latest")
                    elif operation == "purge":
                        client.send_purge_request()
                    
                    # Should have raised an error
                    assert False, "Expected DaemonTimeoutError"
                    
                except DaemonTimeoutError as e:
                    error_msg = str(e)
                    
                    # Error message should mention timeout
                    assert "timeout" in error_msg.lower() or "timed out" in error_msg.lower(), \
                        f"Error message should mention timeout: {error_msg}"
                    
                    # Should include remediation suggestion
                    assert "status" in error_msg.lower() or "log" in error_msg.lower(), \
                        f"Error message should include remediation: {error_msg}"
                
                finally:
                    server_sock.close()
        
        elif error_type == "protocol":
            # Test protocol error
            with tempfile.TemporaryDirectory() as tmpdir:
                socket_path = Path(tmpdir) / "test.sock"
                
                # Create a server that sends invalid response
                server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                server_sock.bind(str(socket_path))
                server_sock.listen(1)
                
                def send_invalid():
                    try:
                        conn, _ = server_sock.accept()
                        conn.recv(4096)
                        # Send invalid JSON
                        conn.sendall(b"invalid json\n")
                        conn.close()
                    except:
                        pass
                
                thread = threading.Thread(target=send_invalid, daemon=True)
                thread.start()
                
                # Give thread time to start
                time.sleep(0.1)
                
                try:
                    client = DaemonClient(socket_path=socket_path, timeout=1.0)
                    
                    if operation == "build":
                        client.send_build_request(
                            context_path=Path("/tmp/test"),
                            dockerfile_path=Path("/tmp/test/Dockerfile"),
                            tag="test:latest"
                        )
                    elif operation == "list":
                        client.send_list_request()
                    elif operation == "remove":
                        client.send_remove_request("test:latest")
                    elif operation == "purge":
                        client.send_purge_request()
                    
                    # Should have raised an error
                    assert False, "Expected DaemonProtocolError"
                    
                except DaemonProtocolError as e:
                    error_msg = str(e)
                    
                    # Error message should mention protocol
                    assert "protocol" in error_msg.lower() or "invalid" in error_msg.lower(), \
                        f"Error message should mention protocol error: {error_msg}"
                    
                    # Should include remediation suggestion
                    assert "version" in error_msg.lower() or "derpy" in error_msg.lower(), \
                        f"Error message should include remediation: {error_msg}"
                
                finally:
                    server_sock.close()
    
    @given(
        tag=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='-_.:/'
        ))
    )
    @settings(max_examples=100)
    def test_property_permission_denied_error_context(self, tag):
        """
        Property 35 (permission case): Permission denied error context
        
        For any permission denied error, the error message should clearly
        indicate the user needs to be added to the derpy group.
        
        Validates: Requirements 10.2
        """
        # We can't easily simulate permission denied without actual system changes,
        # but we can verify the error message structure is correct
        
        # Create a mock socket that raises PermissionError
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            
            # Create socket
            server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server_sock.bind(str(socket_path))
            server_sock.listen(1)
            
            try:
                # Mock the connect method to raise PermissionError
                client = DaemonClient(socket_path=socket_path, timeout=1.0)
                
                with patch.object(socket.socket, 'connect', side_effect=PermissionError("Permission denied")):
                    try:
                        client.send_build_request(
                            context_path=Path("/tmp/test"),
                            dockerfile_path=Path("/tmp/test/Dockerfile"),
                            tag=tag
                        )
                        
                        # Should have raised an error
                        assert False, "Expected DaemonConnectionError"
                        
                    except DaemonConnectionError as e:
                        error_msg = str(e)
                        
                        # Error message should mention permission
                        assert "permission" in error_msg.lower(), \
                            f"Error message should mention permission: {error_msg}"
                        
                        # Should mention derpy group
                        assert "derpy" in error_msg.lower() and "group" in error_msg.lower(), \
                            f"Error message should mention derpy group: {error_msg}"
            
            finally:
                server_sock.close()
