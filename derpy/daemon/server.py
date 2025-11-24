"""Daemon server for handling privileged operations."""

import socket
import os
import grp
import signal
import threading
import logging
import struct
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

from derpy.core.exceptions import DerpyError
from derpy.daemon.handlers import RequestHandler
from derpy.daemon.framing import MessageFramer
from derpy.daemon.protocol import BaseMessage, BuildRequest
from derpy.daemon.security import LogSanitizer


logger = logging.getLogger(__name__)


class DaemonError(DerpyError):
    """Base exception for daemon errors."""
    pass


class DaemonServer:
    """Main daemon server that handles client connections.
    
    The daemon listens on a Unix domain socket and handles requests from
    unprivileged clients. Access is controlled via group membership.
    """

    def __init__(
        self,
        socket_path: Path = Path("/var/run/derpy.sock"),
        group_name: str = "derpy",
        max_workers: int = 4
    ):
        """Initialize daemon server.

        Args:
            socket_path: Path to Unix domain socket
            group_name: System group name for access control
            max_workers: Maximum concurrent build operations
        """
        self.socket_path = socket_path
        self.group_name = group_name
        self.max_workers = max_workers
        
        self._socket: Optional[socket.socket] = None
        self._running = False
        self._shutdown_event = threading.Event()
        self._executor: Optional[ThreadPoolExecutor] = None
        self._accept_thread: Optional[threading.Thread] = None
        
        # Request queue for resource management
        self._request_queue: Queue = Queue()
        
        # Locks for shared resources
        self._storage_lock = threading.Lock()
        self._base_image_cache_lock = threading.Lock()
        
        # Semaphore for limiting concurrent builds
        self._build_semaphore = threading.Semaphore(max_workers)
        
        # Active builds counter for monitoring
        self._active_builds = 0
        self._active_builds_lock = threading.Lock()
        
        # Request handler with locks for shared resources
        self._request_handler = RequestHandler(
            storage_lock=self._storage_lock,
            base_image_cache_lock=self._base_image_cache_lock
        )
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        self.stop()

    def start(self) -> None:
        """Start the daemon server.
        
        Creates the Unix socket, sets permissions, and begins accepting
        client connections.
        
        Raises:
            DaemonError: If socket creation or startup fails
        """
        if self._running:
            raise DaemonError("Daemon is already running")
        
        logger.info(f"Starting daemon server on {self.socket_path}")
        
        try:
            # Create the socket
            self._create_socket()
            
            # Set permissions
            self._set_socket_permissions()
            
            # Create thread pool for handling clients
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
            
            # Start accepting connections
            self._running = True
            self._accept_thread = threading.Thread(
                target=self._accept_connections,
                daemon=False
            )
            self._accept_thread.start()
            
            logger.info("Daemon server started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start daemon: {e}")
            self._cleanup()
            raise DaemonError(f"Failed to start daemon: {e}") from e

    def stop(self) -> None:
        """Stop the daemon server gracefully.
        
        Completes in-progress operations before shutting down and cleans up
        the socket file.
        """
        if not self._running:
            return
        
        logger.info("Stopping daemon server")
        self._running = False
        self._shutdown_event.set()
        
        # Close the listening socket to unblock accept()
        if self._socket:
            try:
                self._socket.close()
            except Exception as e:
                logger.warning(f"Error closing socket: {e}")
        
        # Wait for accept thread to finish
        if self._accept_thread and self._accept_thread.is_alive():
            self._accept_thread.join(timeout=5.0)
        
        # Shutdown executor and wait for in-progress operations
        if self._executor:
            logger.info("Waiting for in-progress operations to complete")
            self._executor.shutdown(wait=True)
        
        # Clean up socket file
        self._cleanup()
        
        logger.info("Daemon server stopped")

    def _create_socket(self) -> None:
        """Create Unix domain socket.
        
        Removes existing socket file if present and creates a new socket.
        
        Raises:
            DaemonError: If socket creation fails
        """
        # Remove existing socket file if it exists
        if self.socket_path.exists():
            logger.warning(f"Removing existing socket file: {self.socket_path}")
            try:
                self.socket_path.unlink()
            except OSError as e:
                raise DaemonError(f"Failed to remove existing socket: {e}") from e
        
        # Create Unix domain socket
        try:
            self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._socket.bind(str(self.socket_path))
            self._socket.listen(5)
            logger.info(f"Created Unix socket at {self.socket_path}")
        except OSError as e:
            raise DaemonError(f"Failed to create socket: {e}") from e

    def _set_socket_permissions(self) -> None:
        """Set socket permissions to 0660 and group ownership to derpy group.
        
        Raises:
            DaemonError: If permission setting fails
        """
        try:
            # Set permissions to 0660 (rw-rw----)
            os.chmod(self.socket_path, 0o660)
            logger.info(f"Set socket permissions to 0660")
            
            # Get derpy group ID
            try:
                group_info = grp.getgrnam(self.group_name)
                group_id = group_info.gr_gid
            except KeyError:
                raise DaemonError(
                    f"Group '{self.group_name}' does not exist. "
                    f"Create it with: sudo groupadd {self.group_name}"
                )
            
            # Set group ownership
            os.chown(self.socket_path, -1, group_id)
            logger.info(f"Set socket group ownership to {self.group_name} (gid={group_id})")
            
        except OSError as e:
            raise DaemonError(f"Failed to set socket permissions: {e}") from e

    def _accept_connections(self) -> None:
        """Accept and handle client connections.
        
        Runs in a separate thread and accepts connections until shutdown.
        """
        logger.info("Started accepting connections")
        
        while self._running and not self._shutdown_event.is_set():
            try:
                # Set timeout so we can check shutdown flag periodically
                self._socket.settimeout(1.0)
                
                try:
                    client_socket, _ = self._socket.accept()
                    logger.debug("Accepted new client connection")
                    
                    # Handle client in thread pool
                    if self._executor:
                        self._executor.submit(self._handle_client, client_socket)
                    
                except socket.timeout:
                    # Timeout is expected, just continue loop
                    continue
                    
            except Exception as e:
                if self._running:
                    logger.error(f"Error accepting connection: {e}")
        
        logger.info("Stopped accepting connections")

    def _handle_client(self, client_socket: socket.socket) -> None:
        """Handle a client connection.
        
        This method runs in the thread pool and handles a single client connection.
        It validates credentials, receives requests, and sends responses with proper
        resource management and output isolation.
        
        Args:
            client_socket: Connected client socket
        """
        try:
            # Validate client credentials
            is_authorized, error_message = self.validate_client_credentials(client_socket)
            
            if not is_authorized:
                logger.warning(f"Unauthorized connection attempt: {error_message}")
                # TODO: Send error response to client in future tasks
                return
            
            logger.info("Client authorized, processing requests")
            
            # Create message framer for this client
            framer = MessageFramer()
            
            # Receive request from client
            try:
                request = framer.receive_message(client_socket)
                if request is None:
                    logger.warning("Client disconnected before sending request")
                    return
            except Exception as e:
                # Sanitize error message before logging
                sanitized_error = LogSanitizer.sanitize_log_message(str(e))
                logger.error(f"Failed to receive request: {sanitized_error}")
                return
            
            # Check if this is a build request (requires resource management)
            is_build_request = isinstance(request, BuildRequest)
            
            if is_build_request:
                # For build requests, acquire semaphore to limit concurrent builds
                logger.debug(f"Acquiring build semaphore (active builds: {self._active_builds})")
                acquired = self._build_semaphore.acquire(timeout=300)  # 5 minute timeout
                
                if not acquired:
                    logger.warning("Build request timed out waiting for resources")
                    # TODO: Send timeout error response to client
                    return
                
                try:
                    # Increment active builds counter
                    with self._active_builds_lock:
                        self._active_builds += 1
                        logger.info(f"Starting build (active builds: {self._active_builds}/{self.max_workers})")
                    
                    # Handle build request with isolated output stream
                    self._handle_build_request_with_locks(client_socket, request)
                    
                finally:
                    # Decrement active builds counter
                    with self._active_builds_lock:
                        self._active_builds -= 1
                        logger.info(f"Build completed (active builds: {self._active_builds}/{self.max_workers})")
                    
                    # Release semaphore
                    self._build_semaphore.release()
            else:
                # Non-build requests don't need semaphore
                self._handle_non_build_request(client_socket, request)
            
        except Exception as e:
            # Sanitize error message before logging
            sanitized_error = LogSanitizer.sanitize_log_message(str(e))
            logger.error(f"Error handling client: {sanitized_error}", exc_info=True)
        finally:
            try:
                client_socket.close()
            except Exception as e:
                sanitized_error = LogSanitizer.sanitize_log_message(str(e))
                logger.warning(f"Error closing client socket: {sanitized_error}")
    
    def _handle_build_request_with_locks(
        self,
        client_socket: socket.socket,
        request: BuildRequest
    ) -> None:
        """Handle a build request with proper resource locking.
        
        This method coordinates access to shared resources (storage, base image cache)
        and ensures output is isolated to this specific client.
        
        Args:
            client_socket: Client socket for sending responses
            request: Build request to handle
        """
        # Create isolated output callback for this client
        def output_callback(message: str) -> None:
            """Send output message to this specific client."""
            try:
                MessageFramer.send_message_raw(client_socket, message)
            except Exception as e:
                logger.warning(f"Failed to send output to client: {e}")
        
        # Handle the request with locks
        # The request handler will internally use locks when accessing shared resources
        try:
            response = self._request_handler.handle_request(
                request,
                output_callback=output_callback
            )
            
            # Send final response
            MessageFramer.send_message(client_socket, response)
            
        except Exception as e:
            logger.error(f"Error handling build request: {e}", exc_info=True)
            # TODO: Send error response to client
    
    def _handle_non_build_request(
        self,
        client_socket: socket.socket,
        request: BaseMessage
    ) -> None:
        """Handle a non-build request (list, remove, purge).
        
        These requests are simpler and don't require the build semaphore,
        but still need proper locking for storage access.
        
        Args:
            client_socket: Client socket for sending responses
            request: Request to handle
        """
        try:
            response = self._request_handler.handle_request(request)
            
            # Send response
            MessageFramer.send_message(client_socket, response)
            
        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            # TODO: Send error response to client
    
    def get_storage_lock(self) -> threading.Lock:
        """Get the storage lock for coordinating storage access.
        
        Returns:
            Threading lock for storage operations
        """
        return self._storage_lock
    
    def get_base_image_cache_lock(self) -> threading.Lock:
        """Get the base image cache lock for coordinating cache access.
        
        Returns:
            Threading lock for base image cache operations
        """
        return self._base_image_cache_lock

    def _cleanup(self) -> None:
        """Clean up resources including socket file."""
        if self.socket_path.exists():
            try:
                self.socket_path.unlink()
                logger.info(f"Removed socket file: {self.socket_path}")
            except OSError as e:
                logger.warning(f"Failed to remove socket file: {e}")

    def validate_client_credentials(self, connection: socket.socket) -> tuple[bool, Optional[str]]:
        """Validate client has permission to connect.
        
        Uses SO_PEERCRED to get client process credentials and verifies
        the user is in the derpy group.
        
        Note: This only works on Linux. On other platforms, it will return
        an error indicating the platform is not supported.
        
        Args:
            connection: Client socket connection
            
        Returns:
            Tuple of (is_authorized, error_message). If authorized, error_message is None.
            If not authorized, error_message contains the reason.
        """
        # Check if SO_PEERCRED is available (Linux only)
        if not hasattr(socket, 'SO_PEERCRED'):
            error_msg = (
                "Credential validation not supported on this platform. "
                "Daemon mode is only supported on Linux."
            )
            logger.error(f"Authentication error: {error_msg}")
            return False, error_msg
        
        try:
            # Get peer credentials using SO_PEERCRED
            # SO_PEERCRED returns (pid, uid, gid) on Linux
            creds = connection.getsockopt(
                socket.SOL_SOCKET,
                socket.SO_PEERCRED,
                struct.calcsize('3i')
            )
            pid, uid, gid = struct.unpack('3i', creds)
            
            logger.debug(f"Client credentials: pid={pid}, uid={uid}, gid={gid}")
            
            # Get the derpy group information
            try:
                group_info = grp.getgrnam(self.group_name)
                derpy_gid = group_info.gr_gid
                derpy_members = group_info.gr_mem
            except KeyError:
                error_msg = f"Group '{self.group_name}' does not exist on system"
                logger.error(f"Authentication failed: {error_msg}")
                return False, error_msg
            
            # Get username for logging
            try:
                import pwd
                user_info = pwd.getpwuid(uid)
                username = user_info.pw_name
            except KeyError:
                username = f"uid:{uid}"
            
            # Check if user is in the derpy group
            # User is authorized if:
            # 1. Their primary group is derpy (gid matches)
            # 2. They are listed as a member of derpy group
            is_authorized = False
            
            # Check primary group
            if gid == derpy_gid:
                is_authorized = True
                logger.info(f"Authentication successful: user {username} (primary group matches)")
            # Check supplementary groups
            elif username in derpy_members:
                is_authorized = True
                logger.info(f"Authentication successful: user {username} (member of {self.group_name} group)")
            else:
                error_msg = (
                    f"Access denied. User {username} is not in the '{self.group_name}' group. "
                    f"Add yourself to the group with: sudo usermod -aG {self.group_name} {username}"
                )
                logger.warning(f"Authentication failed: {error_msg}")
                return False, error_msg
            
            return True, None
            
        except OSError as e:
            error_msg = f"Failed to get client credentials: {e}"
            logger.error(f"Authentication error: {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error during authentication: {e}"
            logger.error(f"Authentication error: {error_msg}")
            return False, error_msg
