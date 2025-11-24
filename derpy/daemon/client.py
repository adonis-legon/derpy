"""Daemon client for communicating with derpyd.

This module implements the client-side communication with the derpyd daemon
over Unix domain sockets. It provides methods for checking daemon availability,
sending requests, and handling responses.
"""

import socket
import time
from pathlib import Path
from typing import Optional, Callable, List
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
from derpy.core.exceptions import DerpyError


class DaemonConnectionError(DerpyError):
    """Error connecting to daemon.
    
    Raised when the daemon socket is not available or connection fails.
    """
    
    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(
            message=f"Daemon connection error: {message}",
            remediation=(
                "Ensure the daemon is running with 'sudo systemctl status derpyd'. "
                "If not running, start it with 'sudo systemctl start derpyd'. "
                "If you're not in the 'derpy' group, add yourself with "
                "'sudo usermod -aG derpy $USER' and log out/in."
            ),
            cause=cause
        )


class DaemonTimeoutError(DerpyError):
    """Daemon operation timed out.
    
    Raised when the daemon does not respond within the timeout period.
    """
    
    def __init__(self, operation: str, timeout: float):
        super().__init__(
            message=f"Daemon operation '{operation}' timed out after {timeout} seconds",
            remediation=(
                "The daemon may be unresponsive or overloaded. "
                "Check daemon status with 'sudo systemctl status derpyd' "
                "and logs with 'sudo journalctl -u derpyd'."
            )
        )


class DaemonProtocolError(DerpyError):
    """Protocol error during daemon communication.
    
    Raised when there are issues with message format or protocol violations.
    """
    
    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(
            message=f"Daemon protocol error: {message}",
            remediation=(
                "This may indicate a version mismatch between client and daemon. "
                "Ensure both are from the same derpy version."
            ),
            cause=cause
        )


class DaemonClient:
    """Client for communicating with derpyd daemon.
    
    Provides methods for checking daemon availability and sending requests
    for build, list, remove, and purge operations.
    
    Attributes:
        socket_path: Path to Unix domain socket
        timeout: Default timeout for operations in seconds
    """
    
    DEFAULT_TIMEOUT = 30.0  # 30 seconds default timeout
    
    def __init__(
        self,
        socket_path: Path = Path("/var/run/derpy.sock"),
        timeout: float = DEFAULT_TIMEOUT
    ):
        """Initialize daemon client.
        
        Args:
            socket_path: Path to Unix domain socket (default: /var/run/derpy.sock)
            timeout: Default timeout for operations in seconds (default: 30)
        """
        self.socket_path = socket_path
        self.timeout = timeout
    
    def is_available(self) -> bool:
        """Check if daemon is running and accessible.
        
        Attempts to connect to the daemon socket to verify availability.
        Does not send any requests, just checks connectivity.
        
        Returns:
            True if daemon is available, False otherwise
        """
        # Check if socket file exists
        if not self.socket_path.exists():
            return False
        
        # Try to connect
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(1.0)  # Short timeout for availability check
            sock.connect(str(self.socket_path))
            sock.close()
            return True
        except (OSError, socket.error):
            return False
    
    def _connect(self) -> socket.socket:
        """Establish connection to daemon socket.
        
        Returns:
            Connected socket
            
        Raises:
            DaemonConnectionError: If connection fails
        """
        # Check if socket exists
        if not self.socket_path.exists():
            raise DaemonConnectionError(
                f"Daemon socket not found: {self.socket_path}. "
                "Daemon is not running."
            )
        
        # Create socket
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
        except OSError as e:
            raise DaemonConnectionError(
                f"Failed to create socket: {e}",
                cause=e
            )
        
        # Connect to daemon
        try:
            sock.connect(str(self.socket_path))
        except PermissionError as e:
            sock.close()
            raise DaemonConnectionError(
                f"Permission denied connecting to daemon socket. "
                f"You may not be in the 'derpy' group.",
                cause=e
            )
        except socket.timeout as e:
            sock.close()
            raise DaemonTimeoutError("connect", self.timeout)
        except OSError as e:
            sock.close()
            raise DaemonConnectionError(
                f"Failed to connect to daemon: {e}",
                cause=e
            )
        
        return sock
    
    def send_build_request(
        self,
        context_path: Path,
        dockerfile_path: Path,
        tag: str,
        build_args: Optional[dict] = None,
        output_callback: Optional[Callable[[str], None]] = None
    ) -> BuildResponse:
        """Send build request to daemon.
        
        Sends a build request and streams output back to the caller via
        the output_callback. Blocks until build completes.
        
        Args:
            context_path: Absolute path to build context directory
            dockerfile_path: Absolute path to Dockerfile
            tag: Image tag (e.g., "myapp:latest")
            build_args: Optional build arguments
            output_callback: Optional callback for streaming output
            
        Returns:
            BuildResponse with build results
            
        Raises:
            DaemonConnectionError: If connection fails
            DaemonTimeoutError: If operation times out
            DaemonProtocolError: If protocol error occurs
        """
        # Create request
        request = BuildRequest(
            context_path=str(context_path.resolve()),
            dockerfile_path=str(dockerfile_path.resolve()),
            tag=tag,
            build_args=build_args or {}
        )
        
        # Validate request
        errors = request.validate()
        if errors:
            raise DaemonProtocolError(f"Invalid build request: {', '.join(errors)}")
        
        # Connect to daemon
        sock = self._connect()
        framer = MessageFramer()
        
        try:
            # Send request
            try:
                MessageFramer.send_message(sock, request)
            except (OSError, ValueError) as e:
                raise DaemonProtocolError(f"Failed to send request: {e}", cause=e)
            
            # Receive streaming output and final response
            while True:
                try:
                    message = framer.receive_message(sock)
                except socket.timeout:
                    raise DaemonTimeoutError("build", self.timeout)
                except ValueError as e:
                    raise DaemonProtocolError(f"Invalid message from daemon: {e}", cause=e)
                except OSError as e:
                    # Check if this is actually a timeout error wrapped in OSError
                    if "timed out" in str(e).lower() or isinstance(e.__cause__, socket.timeout):
                        raise DaemonTimeoutError("build", self.timeout)
                    raise DaemonConnectionError(
                        "Connection lost during build",
                        cause=e
                    )
                
                # Socket closed
                if message is None:
                    raise DaemonConnectionError(
                        "Daemon closed connection unexpectedly"
                    )
                
                # Handle output messages
                if isinstance(message, OutputMessage):
                    if output_callback:
                        output_callback(message.content)
                    continue
                
                # Handle build response (final message)
                if isinstance(message, BuildResponse):
                    return message
                
                # Unexpected message type
                raise DaemonProtocolError(
                    f"Unexpected message type: {type(message).__name__}"
                )
        
        finally:
            sock.close()
    
    def send_list_request(self) -> ListResponse:
        """Send list images request to daemon.
        
        Returns:
            ListResponse with list of images
            
        Raises:
            DaemonConnectionError: If connection fails
            DaemonTimeoutError: If operation times out
            DaemonProtocolError: If protocol error occurs
        """
        # Create request
        request = ListRequest()
        
        # Connect to daemon
        sock = self._connect()
        framer = MessageFramer()
        
        try:
            # Send request
            try:
                MessageFramer.send_message(sock, request)
            except (OSError, ValueError) as e:
                raise DaemonProtocolError(f"Failed to send request: {e}", cause=e)
            
            # Receive response
            try:
                message = framer.receive_message(sock)
            except socket.timeout:
                raise DaemonTimeoutError("list", self.timeout)
            except ValueError as e:
                raise DaemonProtocolError(f"Invalid message from daemon: {e}", cause=e)
            except OSError as e:
                # Check if this is actually a timeout error wrapped in OSError
                if "timed out" in str(e).lower() or isinstance(e.__cause__, socket.timeout):
                    raise DaemonTimeoutError("list", self.timeout)
                raise DaemonConnectionError(
                    "Connection lost during list operation",
                    cause=e
                )
            
            # Socket closed
            if message is None:
                raise DaemonConnectionError(
                    "Daemon closed connection unexpectedly"
                )
            
            # Validate response type
            if not isinstance(message, ListResponse):
                raise DaemonProtocolError(
                    f"Unexpected message type: {type(message).__name__}, expected ListResponse"
                )
            
            return message
        
        finally:
            sock.close()
    
    def send_remove_request(self, tag: str) -> RemoveResponse:
        """Send remove image request to daemon.
        
        Args:
            tag: Image tag to remove
            
        Returns:
            RemoveResponse with removal results
            
        Raises:
            DaemonConnectionError: If connection fails
            DaemonTimeoutError: If operation times out
            DaemonProtocolError: If protocol error occurs
        """
        # Create request
        request = RemoveRequest(tag=tag)
        
        # Validate request
        errors = request.validate()
        if errors:
            raise DaemonProtocolError(f"Invalid remove request: {', '.join(errors)}")
        
        # Connect to daemon
        sock = self._connect()
        framer = MessageFramer()
        
        try:
            # Send request
            try:
                MessageFramer.send_message(sock, request)
            except (OSError, ValueError) as e:
                raise DaemonProtocolError(f"Failed to send request: {e}", cause=e)
            
            # Receive response
            try:
                message = framer.receive_message(sock)
            except socket.timeout:
                raise DaemonTimeoutError("remove", self.timeout)
            except ValueError as e:
                raise DaemonProtocolError(f"Invalid message from daemon: {e}", cause=e)
            except OSError as e:
                # Check if this is actually a timeout error wrapped in OSError
                if "timed out" in str(e).lower() or isinstance(e.__cause__, socket.timeout):
                    raise DaemonTimeoutError("remove", self.timeout)
                raise DaemonConnectionError(
                    "Connection lost during remove operation",
                    cause=e
                )
            
            # Socket closed
            if message is None:
                raise DaemonConnectionError(
                    "Daemon closed connection unexpectedly"
                )
            
            # Validate response type
            if not isinstance(message, RemoveResponse):
                raise DaemonProtocolError(
                    f"Unexpected message type: {type(message).__name__}, expected RemoveResponse"
                )
            
            return message
        
        finally:
            sock.close()
    
    def send_purge_request(self, force: bool = False) -> PurgeResponse:
        """Send purge all images request to daemon.
        
        Args:
            force: Whether to force removal without confirmation
            
        Returns:
            PurgeResponse with purge results
            
        Raises:
            DaemonConnectionError: If connection fails
            DaemonTimeoutError: If operation times out
            DaemonProtocolError: If protocol error occurs
        """
        # Create request
        request = PurgeRequest(force=force)
        
        # Connect to daemon
        sock = self._connect()
        framer = MessageFramer()
        
        try:
            # Send request
            try:
                MessageFramer.send_message(sock, request)
            except (OSError, ValueError) as e:
                raise DaemonProtocolError(f"Failed to send request: {e}", cause=e)
            
            # Receive response
            try:
                message = framer.receive_message(sock)
            except socket.timeout:
                raise DaemonTimeoutError("purge", self.timeout)
            except ValueError as e:
                raise DaemonProtocolError(f"Invalid message from daemon: {e}", cause=e)
            except OSError as e:
                # Check if this is actually a timeout error wrapped in OSError
                if "timed out" in str(e).lower() or isinstance(e.__cause__, socket.timeout):
                    raise DaemonTimeoutError("purge", self.timeout)
                raise DaemonConnectionError(
                    "Connection lost during purge operation",
                    cause=e
                )
            
            # Socket closed
            if message is None:
                raise DaemonConnectionError(
                    "Daemon closed connection unexpectedly"
                )
            
            # Validate response type
            if not isinstance(message, PurgeResponse):
                raise DaemonProtocolError(
                    f"Unexpected message type: {type(message).__name__}, expected PurgeResponse"
                )
            
            return message
        
        finally:
            sock.close()
