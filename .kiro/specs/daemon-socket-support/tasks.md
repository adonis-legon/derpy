# Implementation Plan

- [x] 1. Set up project structure for daemon components

  - Create `derpy/daemon/` directory structure
  - Create `__init__.py` files for daemon modules
  - Create `scripts/systemd/` directory for service files
  - Update `pyproject.toml` to include daemon entry point
  - _Requirements: 2.1, 2.2_

- [x] 2. Implement protocol message classes and serialization

  - Create `derpy/daemon/protocol.py` with base message classes
  - Implement `BuildRequest`, `ListRequest`, `RemoveRequest`, `PurgeRequest` dataclasses
  - Implement `BuildResponse`, `ListResponse`, `RemoveResponse`, `PurgeResponse` dataclasses
  - Implement `OutputMessage` for streaming output
  - Add `to_json()` and `from_json()` methods for all message types
  - Add validation methods for request messages
  - _Requirements: 4.1, 3.1_

- [x] 2.1 Write property test for message serialization round-trip

  - **Property 12: JSON request serialization**
  - **Validates: Requirements 4.1**

- [x] 3. Implement message framing for socket communication

  - Create `derpy/daemon/framing.py` with `MessageFramer` class
  - Implement `send_message()` for sending JSON messages over socket
  - Implement `receive_message()` for receiving and parsing JSON messages
  - Handle newline-delimited message framing
  - Handle partial message buffering
  - Add error handling for malformed messages
  - _Requirements: 4.1, 4.5_

- [x] 3.1 Write property test for message framing

  - **Property 12: JSON request serialization**
  - **Validates: Requirements 4.1**

- [x] 4. Implement daemon server core

  - Create `derpy/daemon/server.py` with `DaemonServer` class
  - Implement `__init__()` with socket path and configuration
  - Implement `start()` to create socket and listen for connections
  - Implement `stop()` for graceful shutdown
  - Implement `_create_socket()` to create Unix domain socket
  - Implement `_set_socket_permissions()` to set 0660 permissions and derpy group
  - Implement `_accept_connections()` loop for handling clients
  - Add signal handlers for SIGTERM and SIGINT
  - _Requirements: 2.2, 2.3, 5.1, 5.2, 5.3_

- [x] 4.1 Write property test for socket creation

  - **Property 5: Socket creation with correct permissions**
  - **Property 6: Socket group ownership**
  - **Validates: Requirements 2.2, 2.3**

- [x] 4.2 Write property test for graceful shutdown

  - **Property 17: Graceful shutdown with operation completion**
  - **Property 18: Socket cleanup on shutdown**
  - **Validates: Requirements 5.2, 5.3**

- [x] 5. Implement client credential validation

  - Add `validate_client_credentials()` method to `DaemonServer`
  - Use `SO_PEERCRED` to get client process credentials
  - Verify client user is in derpy group using `grp.getgrnam()`
  - Return validation result with error message if unauthorized
  - Log authentication attempts (success and failure)
  - _Requirements: 3.2, 9.1_

- [x] 5.1 Write property test for credential validation

  - **Property 2: Unauthorized user error message**
  - **Property 8: Connection credential validation**
  - **Validates: Requirements 1.2, 3.2, 10.2**

- [x] 6. Implement request handling infrastructure

  - Create `derpy/daemon/handlers.py` with `RequestHandler` class
  - Implement `handle_request()` dispatcher based on request type
  - Implement `handle_build_request()` method stub
  - Implement `handle_list_request()` method stub
  - Implement `handle_remove_request()` method stub
  - Implement `handle_purge_request()` method stub
  - Add request validation before dispatching
  - Add error handling and response generation
  - _Requirements: 3.1, 3.4_

- [x] 6.1 Write property test for request validation

  - **Property 7: Request format validation**
  - **Property 10: Invalid request rejection**
  - **Validates: Requirements 3.1, 3.4**

- [x] 7. Implement build request handler with output streaming

  - Implement `handle_build_request()` in `RequestHandler`
  - Create `BuildContext` from request parameters
  - Validate build context and Dockerfile paths
  - Instantiate `BuildEngine` with isolation enabled
  - Execute build with output streaming to client
  - Capture stdout/stderr and send as `OutputMessage` instances
  - Send final `BuildResponse` with success/failure status
  - Handle build errors and exceptions
  - _Requirements: 1.1, 3.3, 4.2, 4.4_

- [x] 7.1 Write property test for build isolation equivalence

  - **Property 9: Build isolation equivalence**
  - **Validates: Requirements 3.3**

- [x] 7.2 Write property test for output streaming

  - **Property 13: Real-time output streaming**
  - **Validates: Requirements 4.2**

- [x] 7.3 Write property test for final response

  - **Property 15: Final response with exit status**
  - **Validates: Requirements 4.4**

- [x] 8. Implement list, remove, and purge request handlers

  - Implement `handle_list_request()` using `ImageManager.list_local_images()`
  - Implement `handle_remove_request()` using `ImageManager.remove_image()`
  - Implement `handle_purge_request()` using `ImageManager.remove_all_images()`
  - Return appropriate response objects with results
  - Handle errors and return error responses
  - _Requirements: 7.4_

- [x] 9. Implement concurrent request handling

  - Add thread pool executor to `DaemonServer` for concurrent requests
  - Implement `handle_client()` to run in thread pool
  - Add request queue for resource management
  - Implement max concurrent builds limit
  - Add locks for shared resources (base image cache, storage)
  - Ensure each client gets isolated output stream
  - _Requirements: 3.5, 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 9.1 Write property test for concurrent request safety

  - **Property 11: Concurrent request safety**
  - **Property 24: Concurrent connection acceptance**
  - **Property 25: Concurrent build filesystem isolation**
  - **Property 26: Base image cache coordination**
  - **Property 27: Output isolation for concurrent builds**
  - **Property 28: Request queueing at resource limits**
  - **Validates: Requirements 3.5, 8.1, 8.2, 8.3, 8.4, 8.5**

- [x] 10. Implement security features

  - Add input validation for all request fields
  - Implement path validation to prevent directory traversal
  - Implement command sanitization to prevent injection
  - Add privilege dropping for non-critical operations
  - Set restrictive permissions (0700) on temporary directories
  - Implement log sanitization to remove credentials
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 10.1 Write property test for security features

  - **Property 29: Privilege dropping for non-critical operations**
  - **Property 30: Restrictive temporary directory permissions**
  - **Property 31: Command injection prevention**
  - **Property 32: Directory traversal prevention**
  - **Property 33: Credential sanitization in logs**
  - **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**

- [x] 11. Implement daemon client

  - Create `derpy/daemon/client.py` with `DaemonClient` class
  - Implement `__init__()` with socket path
  - Implement `is_available()` to check if daemon is running
  - Implement `_connect()` to establish socket connection
  - Implement `send_build_request()` with output callback
  - Implement `send_list_request()`
  - Implement `send_remove_request()`
  - Implement `send_purge_request()`
  - Add timeout handling for unresponsive daemon
  - Add error handling for connection failures
  - _Requirements: 1.1, 4.3, 4.5, 10.3, 10.5_

- [x] 11.1 Write property test for daemon availability check

  - **Property 1: Authorized user socket communication**
  - **Validates: Requirements 1.1**

- [x] 11.2 Write property test for timeout handling

  - **Property 34: Daemon timeout handling**
  - **Validates: Requirements 10.3**

- [x] 11.3 Write property test for disconnection detection

  - **Property 16: Socket disconnection detection**
  - **Validates: Requirements 4.5, 10.5**

- [x] 12. Integrate daemon client into CLI build command

  - Modify `derpy/cli/main.py` `build()` command
  - Import `DaemonClient` at module level
  - Check daemon availability with `daemon_client.is_available()`
  - If available, use `daemon_client.send_build_request()`
  - Pass output callback to display streaming output
  - Handle daemon responses and display results
  - If unavailable, fall back to current direct execution
  - Display warning when falling back
  - _Requirements: 1.1, 1.3, 7.2, 7.3, 7.5_

- [x] 12.1 Write property test for daemon preference

  - **Property 21: Daemon preference with sudo**
  - **Validates: Requirements 7.2**

- [x] 12.2 Write property test for fallback behavior

  - **Property 22: Fallback to direct execution**
  - **Validates: Requirements 7.3, 7.5**

- [x] 13. Integrate daemon client into other CLI commands

  - Modify `ls` command to use daemon if available
  - Modify `rm` command to use daemon if available
  - Modify `purge` command to use daemon if available
  - Ensure non-privileged commands still work directly
  - Add fallback logic for all commands
  - _Requirements: 7.4_

- [x] 13.1 Write property test for non-privileged command routing

  - **Property 23: Non-privileged command direct execution**
  - **Validates: Requirements 7.4**

- [x] 14. Implement error handling and user-friendly messages

  - Add error message for socket not found (daemon not running)
  - Add error message for permission denied (not in derpy group)
  - Add error message for connection timeout
  - Add error message for protocol errors
  - Ensure error messages include context about failed operation
  - Add suggestions for fixing common errors
  - _Requirements: 1.2, 1.3, 10.1, 10.2, 10.4_

- [x] 14.1 Write property test for error messages

  - **Property 35: Error message context**
  - **Validates: Requirements 10.4**

- [x] 15. Create daemon entry point and CLI command

  - Create `derpy/daemon/__main__.py` for daemon entry point
  - Add `derpyd` console script to `pyproject.toml`
  - Implement command-line argument parsing (socket path, log level, etc.)
  - Add `--version` flag
  - Add `--help` flag
  - Implement daemon startup logic
  - _Requirements: 5.1_

- [x] 16. Create systemd service file

  - Create `scripts/systemd/derpyd.service`
  - Set `Type=simple` for service type
  - Set `ExecStart` to derpyd binary path
  - Set `ExecStop` to graceful shutdown signal
  - Configure `Restart=on-failure`
  - Add security settings (PrivateTmp, ProtectSystem, etc.)
  - Set `WantedBy=multi-user.target`
  - _Requirements: 2.5, 5.1_

- [x] 17. Create installation script

  - Create `scripts/install-daemon.sh`
  - Check if running as root
  - Create derpy group if it doesn't exist
  - Install derpy package with pip
  - Copy systemd service file to /etc/systemd/system/
  - Run `systemctl daemon-reload`
  - Enable and start derpyd service
  - Verify socket is created with correct permissions
  - Display success message with instructions
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 18. Create user management helper script

  - Create `scripts/add-user-to-derpy.sh`
  - Accept username as argument
  - Add user to derpy group with `usermod -aG`
  - Display message about logging out and back in
  - Verify user was added successfully
  - _Requirements: 2.4_

- [x] 19. Add logging infrastructure

  - Configure Python logging for daemon
  - Log to systemd journal (stdout/stderr)
  - Log authentication attempts
  - Log request handling (start, success, failure)
  - Log errors with stack traces
  - Sanitize sensitive data in logs
  - Add log levels (DEBUG, INFO, WARNING, ERROR)
  - _Requirements: 5.5, 9.5_

- [x] 19.1 Write property test for error logging

  - **Property 19: Error logging**
  - **Validates: Requirements 5.5**

- [x] 20. Write installation documentation

  - Create `docs/installation.md`
  - Document prerequisites (Linux, Python 3.10+, systemd)
  - Document installation steps
  - Document group creation and user management
  - Document service configuration
  - Document verification steps
  - Add troubleshooting section
  - _Requirements: 6.1, 6.3_

- [x] 21. Write daemon documentation

  - Create `docs/daemon.md`
  - Document architecture with diagrams
  - Document communication protocol
  - Document security model
  - Document service management commands
  - Document configuration options
  - Document log locations and debugging
  - Add performance tuning section
  - _Requirements: 6.2, 6.5_

- [x] 22. Write troubleshooting documentation

  - Create `docs/troubleshooting.md` or update existing
  - Add "Daemon Issues" section
  - Document common socket permission issues
  - Document how to check daemon status
  - Document how to view daemon logs
  - Document how to restart daemon
  - Add solutions for common errors
  - _Requirements: 6.4_

- [x] 23. Update user guide

  - Update `docs/user-guide.md` or `README.md`
  - Add section on daemon vs direct execution
  - Explain when daemon is used vs fallback
  - Document group membership requirement
  - Update build command examples
  - Add daemon-related FAQ
  - _Requirements: 6.1, 6.3_

- [x] 24. Write API documentation

  - Create `docs/api/daemon-protocol.md`
  - Document protocol message formats with JSON schemas
  - Document request types and fields
  - Document response types and fields
  - Document error codes and messages
  - Document streaming output format
  - Add version compatibility notes
  - _Requirements: 6.5_

- [x] 25. Checkpoint - Ensure all tests pass

  - Ensure all tests pass, ask the user if questions arise.

- [x] 26. Test backward compatibility

  - Verify all existing CLI commands work unchanged
  - Verify existing scripts continue to work
  - Verify configuration file format unchanged
  - Verify image storage format unchanged
  - Test with and without daemon running
  - _Requirements: 7.1_

- [x] 26.1 Write property test for backward compatibility

  - **Property 20: Command-line flag backward compatibility**
  - **Validates: Requirements 7.1**

- [x] 27. Test on multiple Linux distributions

  - Test installation on Ubuntu 22.04
  - Test installation on Debian 12
  - Test installation on Fedora 39
  - Test installation on Arch Linux
  - Verify systemd integration works on all
  - Document any distribution-specific issues
  - _Requirements: 2.5_

- [x] 28. Perform security audit

  - Review all input validation code
  - Review privilege dropping implementation
  - Review log sanitization
  - Test with malicious inputs
  - Test with directory traversal attempts
  - Test with command injection attempts
  - Document security findings and fixes
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 29. Performance testing and optimization

  - Measure daemon overhead vs direct execution
  - Test with many concurrent clients (stress test)
  - Test with large build contexts
  - Test with many layers
  - Optimize bottlenecks if found
  - Document performance characteristics
  - _Requirements: 8.1, 8.5_

- [x] 30. Create example configurations

  - Create example systemd service file with comments
  - Create example daemon configuration file
  - Create example user setup script
  - Add examples to documentation
  - _Requirements: 6.2_

- [x] 31. Final integration testing

  - Test complete workflow: install → add user → build
  - Test daemon restart during build
  - Test multiple users building concurrently
  - Test fallback when daemon stopped
  - Test error scenarios
  - Verify all error messages are clear
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 31.1 Write property test for output equivalence

  - **Property 3: Output equivalence for successful builds**
  - **Property 4: Error message equivalence for failed builds**
  - **Validates: Requirements 1.4, 1.5**

- [x] 32. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
