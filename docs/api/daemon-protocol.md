# Daemon Protocol API Documentation

## Overview

The Derpy daemon (derpyd) communicates with the Derpy CLI client over a Unix domain socket using a JSON-based protocol. This document specifies the complete protocol including message formats, request/response types, error codes, and streaming behavior.

**Protocol Version**: 1.0  
**Socket Path**: `/var/run/derpy.sock`  
**Transport**: Unix domain socket  
**Encoding**: UTF-8  
**Message Format**: Newline-delimited JSON

## Protocol Basics

### Message Framing

All messages are JSON objects terminated by a newline character (`\n`). Each message is a single line of JSON.

```
<JSON-OBJECT>\n
```

**Example**:

```json
{"type": "build", "context_path": "/path/to/context", "dockerfile_path": "/path/to/Dockerfile", "tag": "myapp:latest"}\n
```

### Message Flow

1. **Client → Server**: Request message (single JSON object)
2. **Server → Client**: Zero or more output messages (streaming)
3. **Server → Client**: Final response message

**Example Build Flow**:

```
Client → Server: BuildRequest
Server → Client: OutputMessage ("Step 1/3: FROM ubuntu:22.04")
Server → Client: OutputMessage ("Pulling base image...")
Server → Client: OutputMessage ("Step 2/3: RUN apt-get update")
Server → Client: OutputMessage ("...")
Server → Client: BuildResponse (success=true, exit_code=0)
```

### Authentication

Authentication is handled at the socket level using Unix socket credentials (`SO_PEERCRED`). The daemon verifies that the connecting user is a member of the `derpy` system group before processing any requests.

No authentication tokens or credentials are included in protocol messages.

## Request Types

All requests include a `type` field that identifies the request type.

### BuildRequest

Requests the daemon to build a container image from a Dockerfile.

**Type**: `build`

**JSON Schema**:

```json
{
  "type": "string", // Always "build"
  "context_path": "string", // Absolute path to build context directory
  "dockerfile_path": "string", // Absolute path to Dockerfile
  "tag": "string", // Image tag (e.g., "myapp:latest")
  "build_args": {
    // Optional build arguments
    "string": "string" // Key-value pairs for ARG substitution
  }
}
```

**Field Descriptions**:

- `type`: Request type identifier, must be `"build"`
- `context_path`: Absolute path to the build context directory. Must be a valid, accessible directory.
- `dockerfile_path`: Absolute path to the Dockerfile. Must be a valid, readable file.
- `tag`: Image tag in the format `[registry/]name[:tag]`. Must be a valid OCI image reference.
- `build_args`: Optional dictionary of build arguments for `ARG` instruction substitution. Defaults to empty object if omitted.

**Example**:

```json
{
  "type": "build",
  "context_path": "/home/user/myapp",
  "dockerfile_path": "/home/user/myapp/Dockerfile",
  "tag": "myapp:latest",
  "build_args": {
    "VERSION": "1.0.0",
    "BUILD_DATE": "2025-01-15"
  }
}
```

**Validation Rules**:

- `context_path` must be an absolute path
- `dockerfile_path` must be an absolute path
- `tag` must match OCI image reference format
- `build_args` keys and values must be strings
- Paths must not contain directory traversal sequences (`../`)

### ListRequest

Requests a list of all locally stored images.

**Type**: `list`

**JSON Schema**:

```json
{
  "type": "string" // Always "list"
}
```

**Field Descriptions**:

- `type`: Request type identifier, must be `"list"`

**Example**:

```json
{
  "type": "list"
}
```

**Validation Rules**:

- No additional fields required

### RemoveRequest

Requests removal of a specific image from local storage.

**Type**: `remove`

**JSON Schema**:

```json
{
  "type": "string", // Always "remove"
  "tag": "string" // Image tag to remove
}
```

**Field Descriptions**:

- `type`: Request type identifier, must be `"remove"`
- `tag`: Image tag to remove. Must match an existing local image.

**Example**:

```json
{
  "type": "remove",
  "tag": "myapp:latest"
}
```

**Validation Rules**:

- `tag` must be a valid OCI image reference
- `tag` must exist in local storage

### PurgeRequest

Requests removal of all images from local storage.

**Type**: `purge`

**JSON Schema**:

```json
{
  "type": "string", // Always "purge"
  "force": "boolean" // Optional, force removal even if images are in use
}
```

**Field Descriptions**:

- `type`: Request type identifier, must be `"purge"`
- `force`: Optional boolean flag to force removal. Defaults to `false` if omitted.

**Example**:

```json
{
  "type": "purge",
  "force": true
}
```

**Validation Rules**:

- `force` must be a boolean if provided

## Response Types

### BuildResponse

Response to a BuildRequest, sent after all output messages.

**Type**: `build_response`

**JSON Schema**:

```json
{
  "type": "string", // Always "build_response"
  "success": "boolean", // Whether build succeeded
  "exit_code": "integer", // Exit code (0 for success)
  "error_message": "string", // Optional error message if failed
  "image_digest": "string" // Optional SHA256 digest of built image
}
```

**Field Descriptions**:

- `type`: Response type identifier, always `"build_response"`
- `success`: `true` if build completed successfully, `false` otherwise
- `exit_code`: Exit code of the build operation. `0` indicates success, non-zero indicates failure.
- `error_message`: Human-readable error message if `success` is `false`. Omitted if `success` is `true`.
- `image_digest`: SHA256 digest of the built image in format `sha256:<hex>`. Only present if `success` is `true`.

**Success Example**:

```json
{
  "type": "build_response",
  "success": true,
  "exit_code": 0,
  "image_digest": "sha256:abc123def456..."
}
```

**Failure Example**:

```json
{
  "type": "build_response",
  "success": false,
  "exit_code": 1,
  "error_message": "Failed to execute RUN command: apt-get update returned exit code 100"
}
```

### ListResponse

Response to a ListRequest containing all local images.

**Type**: `list_response`

**JSON Schema**:

```json
{
  "type": "string", // Always "list_response"
  "images": [
    // Array of image objects
    {
      "tag": "string", // Image tag
      "digest": "string", // SHA256 digest
      "created": "string", // ISO 8601 timestamp
      "size": "integer" // Size in bytes
    }
  ]
}
```

**Field Descriptions**:

- `type`: Response type identifier, always `"list_response"`
- `images`: Array of image objects, empty array if no images exist
  - `tag`: Image tag in format `[registry/]name[:tag]`
  - `digest`: SHA256 digest in format `sha256:<hex>`
  - `created`: ISO 8601 timestamp of when image was created
  - `size`: Total size of image in bytes (sum of all layers)

**Example**:

```json
{
  "type": "list_response",
  "images": [
    {
      "tag": "myapp:latest",
      "digest": "sha256:abc123...",
      "created": "2025-01-15T10:30:00Z",
      "size": 125829120
    },
    {
      "tag": "myapp:v1.0",
      "digest": "sha256:def456...",
      "created": "2025-01-14T15:20:00Z",
      "size": 125829120
    }
  ]
}
```

### RemoveResponse

Response to a RemoveRequest.

**Type**: `remove_response`

**JSON Schema**:

```json
{
  "type": "string", // Always "remove_response"
  "success": "boolean", // Whether removal succeeded
  "error_message": "string" // Optional error message if failed
}
```

**Field Descriptions**:

- `type`: Response type identifier, always `"remove_response"`
- `success`: `true` if image was removed successfully, `false` otherwise
- `error_message`: Human-readable error message if `success` is `false`. Omitted if `success` is `true`.

**Success Example**:

```json
{
  "type": "remove_response",
  "success": true
}
```

**Failure Example**:

```json
{
  "type": "remove_response",
  "success": false,
  "error_message": "Image not found: myapp:latest"
}
```

### PurgeResponse

Response to a PurgeRequest.

**Type**: `purge_response`

**JSON Schema**:

```json
{
  "type": "string", // Always "purge_response"
  "success": "boolean", // Whether purge succeeded
  "removed_count": "integer", // Number of images removed
  "error_message": "string" // Optional error message if failed
}
```

**Field Descriptions**:

- `type`: Response type identifier, always `"purge_response"`
- `success`: `true` if all images were removed successfully, `false` otherwise
- `removed_count`: Number of images successfully removed
- `error_message`: Human-readable error message if `success` is `false`. Omitted if `success` is `true`.

**Success Example**:

```json
{
  "type": "purge_response",
  "success": true,
  "removed_count": 5
}
```

**Failure Example**:

```json
{
  "type": "purge_response",
  "success": false,
  "removed_count": 3,
  "error_message": "Failed to remove 2 images due to permission errors"
}
```

## Streaming Output

### OutputMessage

Streaming output messages sent during long-running operations (primarily builds).

**Type**: `output`

**JSON Schema**:

```json
{
  "type": "string", // Always "output"
  "stream": "string", // Stream type: "stdout", "stderr", or "progress"
  "content": "string", // Output content
  "timestamp": "number" // Unix timestamp (seconds since epoch)
}
```

**Field Descriptions**:

- `type`: Message type identifier, always `"output"`
- `stream`: Output stream type
  - `"stdout"`: Standard output from build commands
  - `"stderr"`: Standard error from build commands
  - `"progress"`: Progress indicators (e.g., "Step 1/5")
- `content`: The actual output content. May contain newlines.
- `timestamp`: Unix timestamp (seconds since epoch) when the output was generated

**Example**:

```json
{
  "type": "output",
  "stream": "stdout",
  "content": "Step 1/3: FROM ubuntu:22.04\n",
  "timestamp": 1705315800.123
}
```

**Streaming Behavior**:

- Output messages are sent in real-time as the build progresses
- Multiple output messages may be sent before the final response
- Output messages preserve the order of execution
- Clients should display output immediately without buffering
- The final response (BuildResponse) is sent after all output messages

**Example Stream Sequence**:

```json
{"type": "output", "stream": "progress", "content": "Step 1/3: FROM ubuntu:22.04\n", "timestamp": 1705315800.0}
{"type": "output", "stream": "stdout", "content": "Pulling base image ubuntu:22.04...\n", "timestamp": 1705315800.5}
{"type": "output", "stream": "stdout", "content": "Downloaded 5 layers\n", "timestamp": 1705315802.1}
{"type": "output", "stream": "progress", "content": "Step 2/3: RUN apt-get update\n", "timestamp": 1705315802.2}
{"type": "output", "stream": "stdout", "content": "Get:1 http://archive.ubuntu.com/ubuntu jammy InRelease [270 kB]\n", "timestamp": 1705315803.0}
{"type": "output", "stream": "stdout", "content": "Fetched 25.2 MB in 2s\n", "timestamp": 1705315805.0}
{"type": "output", "stream": "progress", "content": "Step 3/3: CMD [\"/bin/bash\"]\n", "timestamp": 1705315805.1}
{"type": "build_response", "success": true, "exit_code": 0, "image_digest": "sha256:abc123..."}
```

## Error Handling

### Error Response Format

When a request cannot be processed, the daemon sends an error response.

**JSON Schema**:

```json
{
  "type": "error",
  "error_code": "string",
  "error_message": "string",
  "details": "object" // Optional additional error details
}
```

**Field Descriptions**:

- `type`: Always `"error"`
- `error_code`: Machine-readable error code (see Error Codes section)
- `error_message`: Human-readable error message
- `details`: Optional object with additional error context

### Error Codes

| Error Code            | Description                                              | HTTP Equivalent           |
| --------------------- | -------------------------------------------------------- | ------------------------- |
| `INVALID_REQUEST`     | Request format is invalid or missing required fields     | 400 Bad Request           |
| `UNAUTHORIZED`        | Client is not authorized (not in derpy group)            | 401 Unauthorized          |
| `FORBIDDEN`           | Operation is forbidden (e.g., path traversal attempt)    | 403 Forbidden             |
| `NOT_FOUND`           | Requested resource not found (e.g., image doesn't exist) | 404 Not Found             |
| `VALIDATION_ERROR`    | Request validation failed (e.g., invalid path)           | 422 Unprocessable Entity  |
| `INTERNAL_ERROR`      | Internal server error                                    | 500 Internal Server Error |
| `SERVICE_UNAVAILABLE` | Service is overloaded or shutting down                   | 503 Service Unavailable   |

### Error Examples

**Invalid Request Format**:

```json
{
  "type": "error",
  "error_code": "INVALID_REQUEST",
  "error_message": "Missing required field: context_path",
  "details": {
    "missing_fields": ["context_path"]
  }
}
```

**Unauthorized Access**:

```json
{
  "type": "error",
  "error_code": "UNAUTHORIZED",
  "error_message": "User 'john' is not in the derpy group. Run: sudo usermod -aG derpy john",
  "details": {
    "user": "john",
    "uid": 1000,
    "required_group": "derpy"
  }
}
```

**Validation Error**:

```json
{
  "type": "error",
  "error_code": "VALIDATION_ERROR",
  "error_message": "Invalid path: context_path contains directory traversal sequence",
  "details": {
    "field": "context_path",
    "value": "/home/user/../../etc",
    "reason": "Directory traversal not allowed"
  }
}
```

**Image Not Found**:

```json
{
  "type": "error",
  "error_code": "NOT_FOUND",
  "error_message": "Image not found: myapp:latest",
  "details": {
    "tag": "myapp:latest"
  }
}
```

**Service Unavailable**:

```json
{
  "type": "error",
  "error_code": "SERVICE_UNAVAILABLE",
  "error_message": "Maximum concurrent builds reached. Request queued.",
  "details": {
    "max_workers": 4,
    "current_workers": 4,
    "queue_position": 2
  }
}
```

## Connection Lifecycle

### Connection Establishment

1. Client opens Unix domain socket connection to `/var/run/derpy.sock`
2. Daemon validates client credentials using `SO_PEERCRED`
3. If unauthorized, daemon closes connection immediately
4. If authorized, daemon waits for request message

### Request Processing

1. Client sends request message (single JSON line)
2. Daemon validates request format and fields
3. If invalid, daemon sends error response and closes connection
4. If valid, daemon processes request:
   - For streaming operations (build): Sends output messages as they occur
   - For non-streaming operations (list, remove): Processes immediately
5. Daemon sends final response message
6. Connection remains open for additional requests (keep-alive)

### Connection Termination

**Normal Termination**:

- Client closes connection after receiving response
- Daemon detects EOF and cleans up resources

**Abnormal Termination**:

- Client disconnects during operation: Daemon cancels operation and cleans up
- Daemon shutdown: Daemon completes in-progress operations, then closes all connections
- Timeout: Daemon closes idle connections after 5 minutes

### Keep-Alive

Connections support keep-alive for multiple requests:

```
Client → Server: BuildRequest
Server → Client: OutputMessage (multiple)
Server → Client: BuildResponse
Client → Server: ListRequest
Server → Client: ListResponse
Client closes connection
```

## Timeouts

| Operation       | Timeout    | Behavior                                 |
| --------------- | ---------- | ---------------------------------------- |
| Connection idle | 5 minutes  | Daemon closes connection                 |
| Request read    | 30 seconds | Daemon sends error and closes connection |
| Build operation | None       | Builds can run indefinitely              |
| Response write  | 30 seconds | Daemon logs error and closes connection  |

## Concurrency

The daemon supports concurrent connections from multiple clients:

- **Maximum concurrent builds**: Configurable (default: 4)
- **Connection limit**: No hard limit (OS-dependent)
- **Request queueing**: Requests exceeding max workers are queued
- **Output isolation**: Each client receives only its own output

**Concurrent Build Example**:

```
Client A → Server: BuildRequest (myapp:v1)
Client B → Server: BuildRequest (myapp:v2)
Server → Client A: OutputMessage (myapp:v1 output)
Server → Client B: OutputMessage (myapp:v2 output)
Server → Client A: BuildResponse (myapp:v1 complete)
Server → Client B: BuildResponse (myapp:v2 complete)
```

## Version Compatibility

### Protocol Version 1.0

**Introduced**: Derpy v0.2.0  
**Status**: Current

**Features**:

- Build, list, remove, purge operations
- Streaming output
- Error responses
- Keep-alive connections

### Future Compatibility

**Backward Compatibility Promise**:

- Protocol v1.x will remain backward compatible
- New optional fields may be added to requests/responses
- Clients should ignore unknown fields
- New request/response types may be added

**Version Negotiation**:

- Currently not implemented (single version)
- Future versions may include version field in requests

**Deprecation Policy**:

- Deprecated features will be supported for at least 2 major versions
- Deprecation warnings will be included in responses
- Documentation will clearly mark deprecated features

## Client Implementation Guidelines

### Recommended Practices

1. **Connection Management**:

   - Reuse connections for multiple requests (keep-alive)
   - Implement connection pooling for concurrent operations
   - Handle connection failures gracefully with retries

2. **Request Handling**:

   - Validate request data before sending
   - Use absolute paths for all file references
   - Sanitize user input to prevent injection

3. **Response Handling**:

   - Parse JSON incrementally (line-by-line)
   - Display output messages immediately (don't buffer)
   - Handle error responses gracefully with user-friendly messages

4. **Error Handling**:

   - Implement exponential backoff for retries
   - Provide clear error messages to users
   - Log errors for debugging

5. **Timeout Handling**:
   - Set reasonable timeouts for operations
   - Allow users to cancel long-running operations
   - Handle timeout errors gracefully

### Example Client Code (Python)

```python
import socket
import json
from pathlib import Path

class DaemonClient:
    def __init__(self, socket_path="/var/run/derpy.sock"):
        self.socket_path = socket_path
        self.sock = None

    def connect(self):
        """Establish connection to daemon."""
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.socket_path)

    def send_request(self, request):
        """Send request to daemon."""
        json_str = json.dumps(request)
        self.sock.sendall((json_str + "\n").encode('utf-8'))

    def receive_message(self):
        """Receive a single message from daemon."""
        buffer = b""
        while b"\n" not in buffer:
            chunk = self.sock.recv(4096)
            if not chunk:
                return None
            buffer += chunk

        json_str = buffer.decode('utf-8').strip()
        return json.loads(json_str)

    def build(self, context_path, dockerfile_path, tag, output_callback=None):
        """Send build request and handle streaming output."""
        request = {
            "type": "build",
            "context_path": str(Path(context_path).resolve()),
            "dockerfile_path": str(Path(dockerfile_path).resolve()),
            "tag": tag
        }

        self.send_request(request)

        # Receive streaming output and final response
        while True:
            message = self.receive_message()
            if not message:
                raise ConnectionError("Connection closed unexpectedly")

            if message["type"] == "output":
                if output_callback:
                    output_callback(message["content"])
            elif message["type"] == "build_response":
                return message
            elif message["type"] == "error":
                raise RuntimeError(f"{message['error_code']}: {message['error_message']}")

    def close(self):
        """Close connection to daemon."""
        if self.sock:
            self.sock.close()
            self.sock = None

# Usage example
client = DaemonClient()
try:
    client.connect()
    response = client.build(
        context_path="/home/user/myapp",
        dockerfile_path="/home/user/myapp/Dockerfile",
        tag="myapp:latest",
        output_callback=lambda line: print(line, end='')
    )
    print(f"\nBuild {'succeeded' if response['success'] else 'failed'}")
finally:
    client.close()
```

## Security Considerations

### Authentication

- Authentication is handled at the OS level via Unix socket credentials
- No credentials are transmitted in protocol messages
- Daemon verifies group membership before processing any requests

### Input Validation

All user-provided inputs are validated:

- Paths are checked for directory traversal attempts
- Tags are validated against OCI reference format
- Build args are sanitized to prevent injection

### Privilege Separation

- Daemon runs as root but drops privileges for non-critical operations
- Build operations run in isolated chroot environments
- Temporary files have restrictive permissions (0700)

### Audit Logging

All security-relevant events are logged:

- Authentication attempts (success and failure)
- Authorization failures
- Suspicious input patterns
- Build operations (start, success, failure)

## Troubleshooting

### Common Issues

**"Connection refused"**:

- Daemon is not running: `sudo systemctl start derpyd`
- Socket file doesn't exist: Check `/var/run/derpy.sock`

**"Permission denied"**:

- User not in derpy group: `sudo usermod -aG derpy $USER`
- User needs to log out and back in for group change to take effect

**"Connection timeout"**:

- Daemon is overloaded: Check `sudo systemctl status derpyd`
- Check daemon logs: `sudo journalctl -u derpyd`

**"Invalid request"**:

- Check request format matches JSON schema
- Ensure all required fields are present
- Validate field types and values

### Debugging

**Enable debug logging**:

```bash
sudo systemctl edit derpyd
# Add: Environment="LOG_LEVEL=DEBUG"
sudo systemctl restart derpyd
```

**View daemon logs**:

```bash
sudo journalctl -u derpyd -f
```

**Test socket connectivity**:

```bash
# Check socket exists and has correct permissions
ls -l /var/run/derpy.sock

# Test connection with netcat
echo '{"type":"list"}' | nc -U /var/run/derpy.sock
```

## References

- [OCI Image Specification](https://github.com/opencontainers/image-spec)
- [Unix Domain Sockets](https://man7.org/linux/man-pages/man7/unix.7.html)
- [JSON Specification](https://www.json.org/)
- [Derpy Documentation](../README.md)
