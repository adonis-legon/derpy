"""Tests for daemon server.

Property 5: Socket creation with correct permissions
Property 6: Socket group ownership
Property 17: Graceful shutdown with operation completion
Property 18: Socket cleanup on shutdown

Feature: daemon-socket-support
Validates: Requirements 2.2, 2.3, 5.2, 5.3
"""

import os
import socket
import stat
import grp
import time
import threading
import tempfile
import pytest
from pathlib import Path
from hypothesis import given, strategies as st, settings

from derpy.daemon.server import DaemonServer, DaemonError


def get_test_group():
    """Get a valid group name for testing."""
    import pwd
    current_user = pwd.getpwuid(os.getuid())
    primary_gid = current_user.pw_gid
    primary_group = grp.getgrgid(primary_gid).gr_name
    return primary_group


class TestDaemonServerBasic:
    """Basic unit tests for DaemonServer."""
    
    def test_create_daemon_server(self):
        """Test creating a daemon server instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            server = DaemonServer(
                socket_path=socket_path,
                group_name="derpy",
                max_workers=4
            )
            assert server.socket_path == socket_path
            assert server.group_name == "derpy"
            assert server.max_workers == 4
            assert not server._running
    
    def test_daemon_server_already_running(self):
        """Test starting daemon when already running raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            test_group = get_test_group()
            server = DaemonServer(socket_path=socket_path, group_name=test_group)
            
            try:
                server.start()
                
                # Try to start again
                with pytest.raises(DaemonError, match="already running"):
                    server.start()
                
            finally:
                server.stop()


class TestSocketCreation:
    """Tests for socket creation and permissions.
    
    Property 5: Socket creation with correct permissions
    Property 6: Socket group ownership
    """
    
    def test_socket_created_at_path(self):
        """Test that socket is created at specified path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            test_group = get_test_group()
            server = DaemonServer(socket_path=socket_path, group_name=test_group)
            
            try:
                server.start()
                
                # Verify socket exists
                assert socket_path.exists()
                
                # Verify it's a socket
                assert stat.S_ISSOCK(socket_path.stat().st_mode)
                
            finally:
                server.stop()
    
    def test_socket_permissions_0660(self):
        """Test that socket has 0660 permissions.
        
        Property 5: Socket creation with correct permissions
        Validates: Requirements 2.2
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            test_group = get_test_group()
            server = DaemonServer(socket_path=socket_path, group_name=test_group)
            
            try:
                server.start()
                
                # Get socket permissions
                mode = socket_path.stat().st_mode
                perms = stat.S_IMODE(mode)
                
                # Verify permissions are 0660
                assert perms == 0o660, f"Expected 0660, got {oct(perms)}"
                
            finally:
                server.stop()
    
    def test_socket_group_ownership(self):
        """Test that socket has correct group ownership.
        
        Property 6: Socket group ownership
        Validates: Requirements 2.3
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            
            # Get current user's primary group for testing
            # In real deployment, this would be 'derpy' group
            import pwd
            current_user = pwd.getpwuid(os.getuid())
            primary_gid = current_user.pw_gid
            primary_group = grp.getgrgid(primary_gid).gr_name
            
            server = DaemonServer(
                socket_path=socket_path,
                group_name=primary_group  # Use existing group for test
            )
            
            try:
                server.start()
                
                # Get socket group
                socket_gid = socket_path.stat().st_gid
                
                # Verify group ownership
                assert socket_gid == primary_gid, \
                    f"Expected gid {primary_gid}, got {socket_gid}"
                
            finally:
                server.stop()
    
    def test_socket_removes_existing_file(self):
        """Test that existing socket file is removed before creating new one."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            
            # Create a dummy file at socket path
            socket_path.touch()
            assert socket_path.exists()
            
            test_group = get_test_group()
            server = DaemonServer(socket_path=socket_path, group_name=test_group)
            
            try:
                server.start()
                
                # Verify socket exists and is a socket (not regular file)
                assert socket_path.exists()
                assert stat.S_ISSOCK(socket_path.stat().st_mode)
                
            finally:
                server.stop()
    
    def test_socket_creation_nonexistent_group(self):
        """Test that socket creation fails with nonexistent group."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            server = DaemonServer(
                socket_path=socket_path,
                group_name="nonexistent_group_12345"
            )
            
            with pytest.raises(DaemonError, match="does not exist"):
                server.start()


class TestGracefulShutdown:
    """Tests for graceful shutdown behavior.
    
    Property 17: Graceful shutdown with operation completion
    Property 18: Socket cleanup on shutdown
    """
    
    def test_stop_when_not_running(self):
        """Test that stop() is safe to call when not running."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            server = DaemonServer(socket_path=socket_path)
            
            # Should not raise error
            server.stop()
    
    def test_socket_cleanup_on_shutdown(self):
        """Test that socket file is removed on shutdown.
        
        Property 18: Socket cleanup on shutdown
        Validates: Requirements 5.3
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            test_group = get_test_group()
            server = DaemonServer(socket_path=socket_path, group_name=test_group)
            
            server.start()
            assert socket_path.exists()
            
            server.stop()
            
            # Verify socket is removed
            assert not socket_path.exists()
    
    def test_graceful_shutdown_waits_for_operations(self):
        """Test that shutdown waits for in-progress operations.
        
        Property 17: Graceful shutdown with operation completion
        Validates: Requirements 5.2
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            test_group = get_test_group()
            server = DaemonServer(socket_path=socket_path, group_name=test_group, max_workers=2)
            
            operation_completed = threading.Event()
            operation_started = threading.Event()
            
            def long_running_operation():
                """Simulate a long-running operation."""
                operation_started.set()
                time.sleep(0.5)  # Simulate work
                operation_completed.set()
            
            try:
                server.start()
                
                # Submit a long-running operation
                if server._executor:
                    future = server._executor.submit(long_running_operation)
                    
                    # Wait for operation to start
                    operation_started.wait(timeout=1.0)
                    
                    # Stop server (should wait for operation)
                    server.stop()
                    
                    # Verify operation completed
                    assert operation_completed.is_set(), \
                        "Operation should have completed before shutdown"
                    
            finally:
                # Ensure cleanup
                if server._running:
                    server.stop()
    
    def test_accept_thread_stops_on_shutdown(self):
        """Test that accept thread stops when server is shut down."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            test_group = get_test_group()
            server = DaemonServer(socket_path=socket_path, group_name=test_group)
            
            server.start()
            
            # Verify accept thread is running
            assert server._accept_thread is not None
            assert server._accept_thread.is_alive()
            
            server.stop()
            
            # Give thread time to stop
            time.sleep(0.1)
            
            # Verify accept thread has stopped
            assert not server._accept_thread.is_alive()
    
    def test_multiple_stop_calls_safe(self):
        """Test that multiple stop() calls are safe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            test_group = get_test_group()
            server = DaemonServer(socket_path=socket_path, group_name=test_group)
            
            server.start()
            server.stop()
            
            # Should not raise error
            server.stop()
            server.stop()


class TestConnectionAcceptance:
    """Tests for connection acceptance."""
    
    def test_accepts_client_connections(self):
        """Test that server accepts client connections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            test_group = get_test_group()
            server = DaemonServer(socket_path=socket_path, group_name=test_group)
            
            try:
                server.start()
                
                # Give server time to start accepting
                time.sleep(0.1)
                
                # Connect as client
                client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                client_socket.connect(str(socket_path))
                
                # Connection should succeed
                assert client_socket.fileno() != -1
                
                client_socket.close()
                
            finally:
                server.stop()
    
    def test_accepts_multiple_connections(self):
        """Test that server accepts multiple client connections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            test_group = get_test_group()
            server = DaemonServer(socket_path=socket_path, group_name=test_group)
            
            try:
                server.start()
                time.sleep(0.1)
                
                # Connect multiple clients
                clients = []
                for _ in range(3):
                    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    client.connect(str(socket_path))
                    clients.append(client)
                
                # All connections should succeed
                assert len(clients) == 3
                for client in clients:
                    assert client.fileno() != -1
                
                # Clean up
                for client in clients:
                    client.close()
                
            finally:
                server.stop()


# Property-Based Tests

class TestPropertyBasedSocketCreation:
    """Property-based tests for socket creation.
    
    Feature: daemon-socket-support, Property 5: Socket creation with correct permissions
    Feature: daemon-socket-support, Property 6: Socket group ownership
    Validates: Requirements 2.2, 2.3
    """
    
    @given(
        max_workers=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=20, deadline=5000)
    def test_socket_always_has_correct_permissions(self, max_workers):
        """
        Property 5: Socket creation with correct permissions
        For any daemon configuration, the created socket should always have
        0660 permissions.
        
        Validates: Requirements 2.2
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            
            # Use current user's primary group for testing
            import pwd
            current_user = pwd.getpwuid(os.getuid())
            primary_gid = current_user.pw_gid
            primary_group = grp.getgrgid(primary_gid).gr_name
            
            server = DaemonServer(
                socket_path=socket_path,
                group_name=primary_group,
                max_workers=max_workers
            )
            
            try:
                server.start()
                
                # Verify socket has 0660 permissions
                mode = socket_path.stat().st_mode
                perms = stat.S_IMODE(mode)
                
                assert perms == 0o660, \
                    f"Socket permissions should be 0660, got {oct(perms)}"
                
            finally:
                server.stop()
    
    @given(
        max_workers=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=20, deadline=5000)
    def test_socket_always_has_correct_group(self, max_workers):
        """
        Property 6: Socket group ownership
        For any daemon configuration, the created socket should always have
        the specified group ownership.
        
        Validates: Requirements 2.3
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            
            # Use current user's primary group for testing
            import pwd
            current_user = pwd.getpwuid(os.getuid())
            primary_gid = current_user.pw_gid
            primary_group = grp.getgrgid(primary_gid).gr_name
            
            server = DaemonServer(
                socket_path=socket_path,
                group_name=primary_group,
                max_workers=max_workers
            )
            
            try:
                server.start()
                
                # Verify socket has correct group
                socket_gid = socket_path.stat().st_gid
                
                assert socket_gid == primary_gid, \
                    f"Socket group should be {primary_gid}, got {socket_gid}"
                
            finally:
                server.stop()


class TestPropertyBasedGracefulShutdown:
    """Property-based tests for graceful shutdown.
    
    Feature: daemon-socket-support, Property 17: Graceful shutdown with operation completion
    Feature: daemon-socket-support, Property 18: Socket cleanup on shutdown
    Validates: Requirements 5.2, 5.3
    """
    
    @given(
        num_operations=st.integers(min_value=0, max_value=5)
    )
    @settings(max_examples=10, deadline=10000)
    def test_shutdown_waits_for_all_operations(self, num_operations):
        """
        Property 17: Graceful shutdown with operation completion
        For any number of in-progress operations, shutdown should wait for
        all of them to complete before returning.
        
        Validates: Requirements 5.2
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            
            # Use current user's primary group for testing
            import pwd
            current_user = pwd.getpwuid(os.getuid())
            primary_gid = current_user.pw_gid
            primary_group = grp.getgrgid(primary_gid).gr_name
            
            server = DaemonServer(
                socket_path=socket_path,
                group_name=primary_group,
                max_workers=10
            )
            
            completed_operations = []
            operations_started = threading.Event()
            
            def operation(op_id):
                """Simulate an operation."""
                if op_id == 0:
                    operations_started.set()
                time.sleep(0.1)  # Simulate work
                completed_operations.append(op_id)
            
            try:
                server.start()
                
                # Submit operations
                if server._executor and num_operations > 0:
                    for i in range(num_operations):
                        server._executor.submit(operation, i)
                    
                    # Wait for at least one operation to start
                    operations_started.wait(timeout=1.0)
                
                # Stop server (should wait for all operations)
                server.stop()
                
                # Verify all operations completed
                if num_operations > 0:
                    assert len(completed_operations) == num_operations, \
                        f"Expected {num_operations} operations to complete, " \
                        f"got {len(completed_operations)}"
                
            finally:
                if server._running:
                    server.stop()
    
    @given(
        max_workers=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=20, deadline=5000)
    def test_socket_always_cleaned_up_on_shutdown(self, max_workers):
        """
        Property 18: Socket cleanup on shutdown
        For any daemon configuration, the socket file should always be
        removed when the daemon shuts down.
        
        Validates: Requirements 5.3
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            
            # Use current user's primary group for testing
            import pwd
            current_user = pwd.getpwuid(os.getuid())
            primary_gid = current_user.pw_gid
            primary_group = grp.getgrgid(primary_gid).gr_name
            
            server = DaemonServer(
                socket_path=socket_path,
                group_name=primary_group,
                max_workers=max_workers
            )
            
            server.start()
            
            # Verify socket exists
            assert socket_path.exists()
            
            server.stop()
            
            # Verify socket is removed
            assert not socket_path.exists(), \
                "Socket file should be removed after shutdown"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

