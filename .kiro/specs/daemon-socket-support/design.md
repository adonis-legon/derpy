# Design Document: Daemon Socket Support

## Overview

This design document specifies the architecture for Derpy version 0.2.0, which introduces a daemon-based architecture to eliminate the need for root privileges when running privileged operations. The system consists of two main components:

1. **Derpyd (Daemon)**: A privileged background service that executes operations requiring elevated permissions
2. **Derpy CLI (Client)**: An unprivileged command-line client that communicates with the daemon via Unix domain socket

The daemon runs with root privileges and listens on `/var/run/derpy.sock`. Users gain access by being added to the `derpy` system group, which has read/write permissions on the socket. This architecture provides a secure, convenient alternative to using sudo for every build command while maintaining proper isolation and security boundaries.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         User Space                          │
│                                                             │
│  ┌──────────────┐                    ┌─────────────────┐  │
│  │  Derpy CLI   │◄──────────────────►│    Derpyd       │  │
│  │ (Unprivileged│   Unix Socket      │  (Privileged)   │  │
│  │    Client)   │  /var/run/derpy.   │    Daemon       │  │
│  └──────────────┘      sock           └─────────────────┘  │
│         │                                      │            │
│         │                                      │            │
│         ▼                                      ▼            │
│  ┌──────────────┐                    ┌─────────────────┐  │
│  │ CLI Commands │                    │ Build Engine    │  │
│  │ (ls, rm,     │                    │ Isolation       │  │
│  │  push, etc.) │                    │ Base Image Mgr  │  │
│  └──────────────┘                    └─────────────────┘  │
│                                               │            │
│                                               ▼            │
│                                      ┌─────────────────┐  │
│                                      │ Storage Manager │  │
│                                      │ Registry Client │  │
│                                      └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Communication Flow

1. User runs `derpy build` command
2. CLI checks if daemon is available by attempting to connect to socket
3. If daemon available:
   - CLI serializes build request as JSON
   - CLI sends request over Unix socket
   - Daemon validates request and user permissions
   - Daemon executes build operation with root privileges
   - Daemon streams output back to CLI in real-time
   - CLI displays output to user
   - Daemon sends final response with exit status
4. If daemon unavailable:
   - CLI falls back to direct execution (requires sudo)
   - CLI displays warning about daemon unavailability

### Security Model

- **Socket Permissions**: `/var/run/derpy.sock` has 0660 permissions (owner: root, group: derpy)
- **Group-Based Access**: Only users in the `derpy` group can connect to the socket
- **Credential Validation**: Daemon verifies connecting user's group membership using `SO_PEERCRED`
- **Request Validation**: All requests are validated before execution
- **Privilege Separation**: Daemon drops privileges for non-critical operations
- **Input Sanitization**: All user-provided inputs are validated and sanitized

## Components and Interfaces

### 1. Daemon (derpyd)

**Location**: `derpy/daemon/server.py`

**Responsibilities**:

- Listen on Unix domain socket for client connections
- Validate client credentials using socket peer credentials
- Parse and validate incoming requests
- Execute privileged operations (build, etc.)
- Stream output back to clients in real-time
- Manage concurrent client connections
- Handle graceful shutdown

**Key Classes**:

```python
class DaemonServer:
    """Main daemon server that handles client connections."""

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

    def start(self) -> None:
        """Start the daemon server."""

    def stop(self) -> None:
        """Stop the daemon server gracefully."""

    def handle_client(self, connection: socket.socket) -> None:
        """Handle a client connection."""

    def validate_client_credentials(self, connection: socket.socket) -> bool:
        """Validate client has permission to connect."""
```

```python
class RequestHandler:
    """Handles execution of client requests."""

    def handle_build_request(
        self,
        request: BuildRequest,
        output_stream: OutputStreamWriter
    ) -> BuildResponse:
        """Execute a build request."""

    def handle_list_request(self, request: ListRequest) -> ListResponse:
        """Execute a list images request."""

    def handle_remove_request(self, request: RemoveRequest) -> RemoveResponse:
        """Execute a remove image request."""
```

### 2. Client Protocol

**Location**: `derpy/daemon/client.py`

**Responsibilities**:

- Detect daemon availability
- Serialize requests to JSON
- Send requests over Unix socket
- Receive and display streaming output
- Handle connection errors gracefully
- Fall back to direct execution when daemon unavailable

**Key Classes**:

```python
class DaemonClient:
    """Client for communicating with derpyd."""

    def __init__(self, socket_path: Path = Path("/var/run/derpy.sock")):
        """Initialize daemon client."""

    def is_available(self) -> bool:
        """Check if daemon is running and accessible."""

    def send_build_request(
        self,
        context_path: Path,
        dockerfile_path: Path,
        tag: str,
        output_callback: Callable[[str], None]
    ) -> BuildResponse:
        """Send build request to daemon."""

    def send_list_request(self) -> ListResponse:
        """Send list images request to daemon."""

    def send_remove_request(self, tag: str) -> RemoveResponse:
        """Send remove image request to daemon."""
```

### 3. Protocol Messages

**Location**: `derpy/daemon/protocol.py`

**Message Format**: JSON over Unix socket with newline delimiters

**Request Types**:

```python
@dataclass
class BuildRequest:
    """Request to build an image."""
    type: str = "build"  # Request type identifier
    context_path: str    # Absolute path to build context
    dockerfile_path: str # Absolute path to Dockerfile
    tag: str            # Image tag
    build_args: Dict[str, str] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize to JSON string."""

    @classmethod
    def from_json(cls, json_str: str) -> "BuildRequest":
        """Deserialize from JSON string."""
```

```python
@dataclass
class ListRequest:
    """Request to list images."""
    type: str = "list"

@dataclass
class RemoveRequest:
    """Request to remove an image."""
    type: str = "remove"
    tag: str

@dataclass
class PurgeRequest:
    """Request to purge all images."""
    type: str = "purge"
    force: bool = False
```

**Response Types**:

```python
@dataclass
class BuildResponse:
    """Response from build operation."""
    success: bool
    exit_code: int
    error_message: Optional[str] = None
    image_digest: Optional[str] = None

@dataclass
class OutputMessage:
    """Streaming output message."""
    type: str = "output"  # "output", "error", "progress"
    content: str
    timestamp: float
```

### 4. CLI Integration

**Location**: `derpy/cli/main.py` (modifications)

**Changes**:

- Import `DaemonClient` at module level
- Modify `build()` command to check daemon availability
- If daemon available, use `DaemonClient.send_build_request()`
- If daemon unavailable, fall back to current direct execution
- Display appropriate warnings/errors for daemon communication issues

**Example Integration**:

```python
@cli.command()
@click.argument('context', type=click.Path(...))
@click.option('-f', '--file', 'dockerfile', ...)
@click.option('-t', '--tag', required=True, ...)
@click.pass_context
def build(ctx, context: Path, dockerfile: Path, tag: str):
    """Build a container image from a Dockerfile."""

    # Try daemon first
    daemon_client = DaemonClient()

    if daemon_client.is_available():
        # Use daemon
        try:
            response = daemon_client.send_build_request(
                context_path=context.resolve(),
                dockerfile_path=dockerfile.resolve(),
                tag=tag,
                output_callback=lambda line: click.echo(line, nl=False)
            )

            if response.success:
                click.echo(f"✓ Successfully built image: {tag}")
            else:
                click.echo(f"Build failed: {response.error_message}", err=True)
                ctx.exit(response.exit_code)

        except DaemonConnectionError as e:
            click.echo(f"Daemon communication error: {e}", err=True)
            ctx.exit(1)
    else:
        # Fall back to direct execution
        click.echo("Warning: Daemon not available, falling back to direct execution")
        click.echo("This requires sudo privileges for build isolation.")

        # Current implementation (requires sudo)
        # ... existing build code ...
```

### 5. Service Management

**Location**: `scripts/install-daemon.sh`, `scripts/systemd/derpyd.service`

**Systemd Service File** (`/etc/systemd/system/derpyd.service`):

```ini
[Unit]
Description=Derpy Container Daemon
Documentation=https://github.com/yourusername/derpy
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/derpyd --socket /var/run/derpy.sock
ExecStop=/bin/kill -SIGTERM $MAINPID
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=false
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/run /var/lib/derpy /root/.derpy

[Install]
WantedBy=multi-user.target
```

**Installation Script**:

```bash
#!/bin/bash
# scripts/install-daemon.sh

set -e

echo "Installing Derpy daemon..."

# Create derpy group if it doesn't exist
if ! getent group derpy > /dev/null 2>&1; then
    echo "Creating derpy group..."
    groupadd -r derpy
fi

# Install derpyd binary
echo "Installing derpyd binary..."
pip install -e .

# Install systemd service
echo "Installing systemd service..."
cp scripts/systemd/derpyd.service /etc/systemd/system/
systemctl daemon-reload

# Enable and start service
echo "Enabling and starting derpyd service..."
systemctl enable derpyd
systemctl start derpyd

# Wait for socket to be created
sleep 2

# Verify socket exists and has correct permissions
if [ -S /var/run/derpy.sock ]; then
    echo "✓ Daemon socket created successfully"
    ls -l /var/run/derpy.sock
else
    echo "✗ Failed to create daemon socket"
    exit 1
fi

echo ""
echo "Installation complete!"
echo ""
echo "To grant a user access to derpy, add them to the derpy group:"
echo "  sudo usermod -aG derpy <username>"
echo ""
echo "The user will need to log out and back in for the change to take effect."
```

## Data Models

### Request/Response Models

All models use Python dataclasses with JSON serialization support:

```python
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
import json

@dataclass
class BaseMessage:
    """Base class for protocol messages."""

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, json_str: str):
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls(**data)
```

### Socket Message Framing

Messages are framed using newline delimiters:

- Each message is a single line of JSON
- Messages are terminated with `\n`
- Large messages (>1MB) are chunked with continuation markers

```python
class MessageFramer:
    """Handles message framing over socket."""

    @staticmethod
    def send_message(sock: socket.socket, message: BaseMessage) -> None:
        """Send a message over socket."""
        json_str = message.to_json()
        sock.sendall((json_str + "\n").encode('utf-8'))

    @staticmethod
    def receive_message(sock: socket.socket) -> Optional[BaseMessage]:
        """Receive a message from socket."""
        # Read until newline
        buffer = b""
        while b"\n" not in buffer:
            chunk = sock.recv(4096)
            if not chunk:
                return None
            buffer += chunk

        # Parse JSON
        json_str = buffer.decode('utf-8').strip()
        # Determine message type and deserialize
        data = json.loads(json_str)
        msg_type = data.get('type')

        if msg_type == 'build':
            return BuildRequest.from_json(json_str)
        elif msg_type == 'output':
            return OutputMessage.from_json(json_str)
        # ... other types
```

## Correctness Properties

_A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees._

### Property 1: Authorized user socket communication

_For any_ user in the derpy group and any build command, the CLI should successfully communicate with the daemon via Unix socket without requiring sudo
**Validates: Requirements 1.1**

### Property 2: Unauthorized user error message

_For any_ user not in the derpy group, attempting to run a build command should result in a clear error message indicating they need to be added to the derpy group
**Validates: Requirements 1.2, 10.2**

### Property 3: Output equivalence for successful builds

_For any_ successful build operation, the output displayed by the daemon-based CLI should match the output from the current sudo-based implementation
**Validates: Requirements 1.4**

### Property 4: Error message equivalence for failed builds

_For any_ failed build operation, the error messages displayed by the daemon-based CLI should contain the same detail as the current sudo-based implementation
**Validates: Requirements 1.5**

### Property 5: Socket creation with correct permissions

_For any_ daemon start operation, the Unix socket should be created at /var/run/derpy.sock with 0660 permissions
**Validates: Requirements 2.2**

### Property 6: Socket group ownership

_For any_ Unix socket creation, the socket group ownership should be set to the derpy group
**Validates: Requirements 2.3**

### Property 7: Request format validation

_For any_ request received by the daemon, the request format should be validated before processing
**Validates: Requirements 3.1**

### Property 8: Connection credential validation

_For any_ socket connection attempt, the daemon should verify the connecting user is in the derpy group using socket credentials
**Validates: Requirements 3.2**

### Property 9: Build isolation equivalence

_For any_ build operation executed by the daemon, the build isolation mechanisms used should produce the same results as the current sudo-based implementation
**Validates: Requirements 3.3**

### Property 10: Invalid request rejection

_For any_ invalid request, the daemon should reject it and return a descriptive error message
**Validates: Requirements 3.4**

### Property 11: Concurrent request safety

_For any_ set of concurrent requests, the daemon should handle them without race conditions or data corruption
**Validates: Requirements 3.5**

### Property 12: JSON request serialization

_For any_ build request sent by the CLI, the request should be serialized as valid JSON over the Unix socket
**Validates: Requirements 4.1**

### Property 13: Real-time output streaming

_For any_ build operation, the daemon should stream output back to the CLI incrementally, not all at once after completion
**Validates: Requirements 4.2**

### Property 14: Immediate output display

_For any_ output received from the daemon, the CLI should display it to the user without buffering delays
**Validates: Requirements 4.3**

### Property 15: Final response with exit status

_For any_ completed build operation, the daemon should send a final response containing the exit status
**Validates: Requirements 4.4**

### Property 16: Socket disconnection detection

_For any_ socket disconnection during communication, the CLI should detect it and report a clear error message
**Validates: Requirements 4.5, 10.5**

### Property 17: Graceful shutdown with operation completion

_For any_ daemon shutdown request while operations are in progress, the daemon should complete those operations before shutting down
**Validates: Requirements 5.2**

### Property 18: Socket cleanup on shutdown

_For any_ daemon shutdown, the Unix socket file should be removed
**Validates: Requirements 5.3**

### Property 19: Error logging

_For any_ error encountered by the daemon, the error should be logged to the system log
**Validates: Requirements 5.5**

### Property 20: Command-line flag backward compatibility

_For any_ existing command-line flag combination, the new CLI should accept it without changes
**Validates: Requirements 7.1**

### Property 21: Daemon preference with sudo

_For any_ invocation of derpy build with sudo, if the daemon is available, it should be used instead of direct execution
**Validates: Requirements 7.2**

### Property 22: Fallback to direct execution

_For any_ build command when the daemon is unavailable and the user has sudo privileges, the CLI should fall back to direct execution with a warning
**Validates: Requirements 7.3, 7.5**

### Property 23: Non-privileged command direct execution

_For any_ non-privileged command (ls, rm without isolation, etc.), the CLI should execute it directly without daemon communication
**Validates: Requirements 7.4**

### Property 24: Concurrent connection acceptance

_For any_ set of simultaneous client connection attempts, the daemon should accept all connections without blocking
**Validates: Requirements 8.1**

### Property 25: Concurrent build filesystem isolation

_For any_ set of concurrent build operations, each build's filesystem operations should be isolated to prevent conflicts
**Validates: Requirements 8.2**

### Property 26: Base image cache coordination

_For any_ set of concurrent builds accessing the same base image, the daemon should coordinate cache access to prevent corruption
**Validates: Requirements 8.3**

### Property 27: Output isolation for concurrent builds

_For any_ set of concurrent builds, each client should receive only its own build output, not mixed output from other builds
**Validates: Requirements 8.4**

### Property 28: Request queueing at resource limits

_For any_ situation where the daemon reaches resource limits, new requests should be queued and processed as resources become available
**Validates: Requirements 8.5**

### Property 29: Privilege dropping for non-critical operations

_For any_ non-critical operation, the daemon should drop root privileges before executing it
**Validates: Requirements 9.1**

### Property 30: Restrictive temporary directory permissions

_For any_ temporary directory created by the daemon, the permissions should be restrictive (0700) to prevent unauthorized access
**Validates: Requirements 9.2**

### Property 31: Command injection prevention

_For any_ user-provided command, the daemon should validate and sanitize it to prevent command injection attacks
**Validates: Requirements 9.3**

### Property 32: Directory traversal prevention

_For any_ file path provided by the user, the daemon should validate it to prevent directory traversal attacks (../, etc.)
**Validates: Requirements 9.4**

### Property 33: Credential sanitization in logs

_For any_ log entry, sensitive information like registry credentials should not be included
**Validates: Requirements 9.5**

### Property 34: Daemon timeout handling

_For any_ unresponsive daemon, the CLI should timeout after a reasonable period (e.g., 30 seconds) and display a timeout error
**Validates: Requirements 10.3**

### Property 35: Error message context

_For any_ error response from the daemon, the CLI should display the error message with context about the failed operation
**Validates: Requirements 10.4**

## Error Handling

### Client-Side Error Handling

**Connection Errors**:

- Socket doesn't exist → "Daemon not running. Start with: sudo systemctl start derpyd"
- Permission denied → "Access denied. Add yourself to derpy group: sudo usermod -aG derpy $USER"
- Connection refused → "Daemon not accepting connections. Check status: sudo systemctl status derpyd"
- Timeout → "Daemon not responding. Check logs: sudo journalctl -u derpyd"

**Communication Errors**:

- Invalid response format → "Protocol error: Invalid response from daemon"
- Unexpected disconnection → "Connection lost to daemon during operation"
- Serialization error → "Failed to serialize request: <details>"

**Fallback Behavior**:

- If daemon unavailable and user has sudo → Fall back to direct execution with warning
- If daemon unavailable and user lacks sudo → Display error and exit
- If daemon communication fails mid-operation → Display error and exit (don't retry automatically)

### Server-Side Error Handling

**Request Validation Errors**:

- Invalid JSON → Return error response with details
- Missing required fields → Return error response listing missing fields
- Invalid field values → Return error response with validation details
- Malicious input detected → Reject request and log security event

**Execution Errors**:

- Build failure → Stream error output to client, return failure response
- Resource exhaustion → Queue request or return "server busy" error
- Internal error → Log error, return generic error response to client

**Concurrency Errors**:

- Deadlock detection → Log error, terminate affected operations
- Resource contention → Use locks/semaphores to coordinate access
- Client disconnection during operation → Clean up resources, log event

### Error Recovery

**Client Recovery**:

- Connection lost → Display error, exit cleanly
- Timeout → Display error, suggest checking daemon status
- Invalid response → Display error, suggest checking daemon version

**Server Recovery**:

- Client disconnection → Clean up operation resources, continue serving other clients
- Operation failure → Log error, clean up resources, continue serving other clients
- Resource exhaustion → Queue requests, process when resources available
- Crash → Systemd restarts daemon automatically

## Testing Strategy

### Unit Testing

**Client Unit Tests**:

- Test `DaemonClient.is_available()` with socket present/absent
- Test request serialization for all request types
- Test response deserialization for all response types
- Test error handling for connection failures
- Test fallback logic when daemon unavailable

**Server Unit Tests**:

- Test credential validation with valid/invalid users
- Test request validation with valid/invalid requests
- Test request routing to appropriate handlers
- Test graceful shutdown logic
- Test socket creation and permission setting

**Protocol Unit Tests**:

- Test message serialization/deserialization
- Test message framing with various sizes
- Test handling of malformed messages
- Test handling of incomplete messages

### Integration Testing

**Client-Server Integration**:

- Test complete build request/response cycle
- Test streaming output from daemon to client
- Test concurrent client connections
- Test client disconnection during operation
- Test daemon restart while clients connected

**Build Integration**:

- Test daemon-based build produces same result as direct build
- Test daemon-based build with various Dockerfiles
- Test concurrent builds don't interfere
- Test build with base image caching

**Security Integration**:

- Test unauthorized user connection rejection
- Test command injection attempts are blocked
- Test directory traversal attempts are blocked
- Test privilege dropping works correctly

### Property-Based Testing

Property-based tests will use Python's `hypothesis` library to generate random test inputs and verify properties hold across all inputs.

**Configuration**:

- Minimum 100 iterations per property test
- Use `@given` decorator with appropriate strategies
- Tag tests with property number: `# Property 1: Authorized user socket communication`

**Test Strategies**:

- Generate random user IDs (in/out of derpy group)
- Generate random build contexts and Dockerfiles
- Generate random request payloads (valid/invalid)
- Generate random file paths (safe/malicious)
- Generate concurrent operation scenarios

**Example Property Test**:

```python
from hypothesis import given, strategies as st
import pytest

# Property 1: Authorized user socket communication
@given(
    user_id=st.integers(min_value=1000, max_value=65535),
    build_context=st.text(min_size=1),
    tag=st.text(min_size=1, max_size=128)
)
def test_authorized_user_socket_communication(user_id, build_context, tag):
    """
    Property 1: Authorized user socket communication
    For any user in the derpy group and any build command,
    the CLI should successfully communicate with the daemon.

    Validates: Requirements 1.1
    """
    # Add user to derpy group
    add_user_to_group(user_id, "derpy")

    # Create daemon client as that user
    client = DaemonClient(user_id=user_id)

    # Verify connection succeeds
    assert client.is_available()

    # Verify can send request without sudo
    response = client.send_build_request(
        context_path=build_context,
        dockerfile_path=f"{build_context}/Dockerfile",
        tag=tag
    )

    # Should not raise permission error
    assert response is not None
```

### End-to-End Testing

**Scenario Tests**:

- Install daemon, add user to group, run build successfully
- Run build without daemon, verify fallback works
- Run concurrent builds from multiple users
- Stop daemon during build, verify graceful handling
- Restart daemon, verify clients can reconnect

**Performance Tests**:

- Measure daemon overhead vs direct execution
- Test with many concurrent clients (stress test)
- Test with large build contexts
- Test with many layers

### Manual Testing Checklist

- [ ] Install daemon on fresh system
- [ ] Verify socket created with correct permissions
- [ ] Add user to derpy group, verify access works
- [ ] Remove user from group, verify access denied
- [ ] Run build as regular user (in group)
- [ ] Run build with sudo (should use daemon)
- [ ] Stop daemon, verify fallback works
- [ ] Start daemon while CLI running
- [ ] Run multiple concurrent builds
- [ ] Check logs for errors
- [ ] Verify systemd integration works
- [ ] Test on Ubuntu, Debian, Fedora, Arch

## Documentation Requirements

### Installation Documentation

**Location**: `docs/installation.md`

**Content**:

- Prerequisites (Linux, Python 3.10+, systemd)
- Installation steps (pip install, daemon setup)
- Group creation and user management
- Service configuration and startup
- Verification steps
- Troubleshooting common issues

### Daemon Documentation

**Location**: `docs/daemon.md`

**Content**:

- Architecture overview with diagrams
- Communication protocol specification
- Security model explanation
- Service management (start, stop, restart, status)
- Configuration options
- Log locations and debugging
- Performance tuning

### User Guide Updates

**Location**: `docs/user-guide.md`

**Updates**:

- Add section on daemon vs direct execution
- Explain when daemon is used vs fallback
- Document group membership requirement
- Add troubleshooting section for daemon issues
- Update build command examples

### API Documentation

**Location**: `docs/api/daemon-protocol.md`

**Content**:

- Protocol message formats (JSON schemas)
- Request types and fields
- Response types and fields
- Error codes and messages
- Streaming output format
- Version compatibility

### Troubleshooting Guide

**Location**: `docs/troubleshooting.md`

**New Section**: "Daemon Issues"

**Content**:

- "Permission denied" → Check group membership
- "Daemon not running" → Start service
- "Connection timeout" → Check daemon logs
- "Build fails with daemon but works with sudo" → Check daemon permissions
- Common socket permission issues
- How to check daemon status
- How to view daemon logs
- How to restart daemon

## Implementation Notes

### Phase 1: Core Protocol and Server

1. Implement protocol message classes (`daemon/protocol.py`)
2. Implement message framing (`daemon/framing.py`)
3. Implement daemon server (`daemon/server.py`)
4. Implement request handlers (`daemon/handlers.py`)
5. Add unit tests for protocol and server

### Phase 2: Client Integration

1. Implement daemon client (`daemon/client.py`)
2. Integrate client into CLI (`cli/main.py`)
3. Add fallback logic
4. Add unit tests for client

### Phase 3: Service Management

1. Create systemd service file
2. Create installation script
3. Add service management commands
4. Test on multiple Linux distributions

### Phase 4: Security Hardening

1. Implement credential validation
2. Implement input sanitization
3. Implement privilege dropping
4. Add security tests
5. Security audit

### Phase 5: Documentation and Polish

1. Write installation documentation
2. Write daemon documentation
3. Update user guide
4. Write troubleshooting guide
5. Add examples

### Backward Compatibility

- CLI commands remain unchanged
- Existing scripts continue to work
- Daemon is optional (fallback to direct execution)
- Configuration file format unchanged
- Image storage format unchanged

### Performance Considerations

- Socket communication overhead: ~1-2ms per request
- No performance impact on build execution itself
- Concurrent builds limited by system resources, not daemon
- Memory overhead: ~50MB for daemon process
- Disk overhead: None (no additional storage)

### Security Considerations

- Socket permissions prevent unauthorized access
- Group-based access control is standard Unix pattern
- Credential validation uses kernel-provided socket credentials
- Input validation prevents injection attacks
- Privilege dropping limits attack surface
- Audit logging for security events

### Platform Support

- **Linux**: Full support with systemd
- **macOS**: Not supported (no chroot, different service management)
- **Windows**: Not supported (no Unix sockets, different architecture)

For macOS and Windows, the CLI will continue to use direct execution mode (current v0.1.0 behavior).
