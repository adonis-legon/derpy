# Derpy Daemon (derpyd)

## Overview

The Derpy daemon (derpyd) is a privileged background service that eliminates the need for sudo when running container build operations. It runs with root privileges and communicates with the unprivileged Derpy CLI via a Unix domain socket, providing a secure and convenient alternative to using sudo for every build command.

**Key Benefits:**

- No sudo required for build operations
- Secure group-based access control
- Concurrent build support
- Real-time output streaming
- Automatic fallback when unavailable
- Systemd integration for service management

**Platform Support:**

- **Linux**: Full support with systemd
- **macOS**: Not supported (no chroot, different service management)
- **Windows**: Not supported (no Unix sockets, different architecture)

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

1. **User runs command**: User executes `derpy build` without sudo
2. **Daemon detection**: CLI checks if daemon is available by attempting socket connection
3. **Request serialization**: CLI serializes build request as JSON
4. **Socket communication**: CLI sends request over Unix socket at `/var/run/derpy.sock`
5. **Credential validation**: Daemon verifies user is in `derpy` group using socket credentials
6. **Request processing**: Daemon validates request format and parameters
7. **Build execution**: Daemon executes build with root privileges and isolation
8. **Output streaming**: Daemon streams build output back to CLI in real-time
9. **Result display**: CLI displays output to user as it arrives
10. **Final response**: Daemon sends completion status and exit code

### Security Model

The daemon implements multiple layers of security:

**Socket Permissions:**

- Socket path: `/var/run/derpy.sock`
- Permissions: `0660` (owner: root, group: derpy)
- Only users in `derpy` group can connect

**Credential Validation:**

- Uses `SO_PEERCRED` to get client process credentials
- Verifies client user is in `derpy` group
- Logs all authentication attempts (success and failure)

**Request Validation:**

- All requests validated before execution
- JSON schema validation for message format
- Path validation to prevent directory traversal
- Command sanitization to prevent injection

**Privilege Separation:**

- Daemon runs as root but drops privileges for non-critical operations
- Temporary directories created with restrictive permissions (0700)
- Build isolation uses chroot for filesystem containment

**Audit Logging:**

- All authentication attempts logged
- All operations logged with user context
- Sensitive data (credentials) sanitized from logs
- Logs written to systemd journal

## Communication Protocol

### Message Format

All messages are JSON-encoded and newline-delimited:

```
<JSON message>\n
```

### Request Types

#### BuildRequest

Request to build a container image:

```json
{
  "type": "build",
  "context_path": "/absolute/path/to/context",
  "dockerfile_path": "/absolute/path/to/Dockerfile",
  "tag": "myapp:latest",
  "build_args": {
    "ARG_NAME": "value"
  }
}
```

**Fields:**

- `type`: Always "build"
- `context_path`: Absolute path to build context directory
- `dockerfile_path`: Absolute path to Dockerfile
- `tag`: Image tag (name:version)
- `build_args`: Optional build arguments (key-value pairs)

#### ListRequest

Request to list local images:

```json
{
  "type": "list"
}
```

#### RemoveRequest

Request to remove a specific image:

```json
{
  "type": "remove",
  "tag": "myapp:latest"
}
```

**Fields:**

- `type`: Always "remove"
- `tag`: Image tag to remove

#### PurgeRequest

Request to remove all images:

```json
{
  "type": "purge",
  "force": false
}
```

**Fields:**

- `type`: Always "purge"
- `force`: Whether to force removal (default: false)

### Response Types

#### BuildResponse

Response from build operation:

```json
{
  "success": true,
  "exit_code": 0,
  "error_message": null,
  "image_digest": "sha256:abc123..."
}
```

**Fields:**

- `success`: Whether build succeeded
- `exit_code`: Exit code from build process
- `error_message`: Error description if failed (null if successful)
- `image_digest`: SHA256 digest of built image (null if failed)

#### OutputMessage

Streaming output during build:

```json
{
  "type": "output",
  "content": "Step 1/5 : FROM alpine:latest\n",
  "timestamp": 1234567890.123
}
```

**Fields:**

- `type`: Message type ("output", "error", "progress")
- `content`: Output text
- `timestamp`: Unix timestamp with milliseconds

#### ListResponse

Response from list operation:

```json
{
  "images": [
    {
      "tag": "myapp:latest",
      "digest": "sha256:abc123...",
      "size": 12345678,
      "created": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### RemoveResponse

Response from remove operation:

```json
{
  "success": true,
  "removed_tag": "myapp:latest",
  "error_message": null
}
```

#### ErrorResponse

Generic error response:

```json
{
  "error": "Invalid request format",
  "details": "Missing required field: context_path"
}
```

### Message Framing

Messages are framed using newline delimiters:

- Each message is a single line of JSON
- Messages are terminated with `\n`
- Receiver reads until newline, then parses JSON
- Large messages (>1MB) are chunked with continuation markers

## Service Management

### Starting the Daemon

**Using systemd:**

```bash
# Start daemon
sudo systemctl start derpyd

# Check status
sudo systemctl status derpyd

# View logs
sudo journalctl -u derpyd -f
```

**Manual start (for testing):**

```bash
# Start in foreground
sudo derpyd --socket /var/run/derpy.sock

# Start with debug logging
sudo derpyd --socket /var/run/derpy.sock --log-level DEBUG
```

### Stopping the Daemon

**Graceful shutdown:**

```bash
# Stop daemon (completes in-progress operations)
sudo systemctl stop derpyd
```

The daemon will:

1. Stop accepting new connections
2. Wait for in-progress operations to complete
3. Clean up resources (remove socket file)
4. Exit

**Force stop (not recommended):**

```bash
# Kill daemon immediately
sudo systemctl kill derpyd
```

### Restarting the Daemon

```bash
# Restart daemon
sudo systemctl restart derpyd

# Reload configuration (if supported)
sudo systemctl reload derpyd
```

### Enabling Auto-Start

```bash
# Enable daemon to start on boot
sudo systemctl enable derpyd

# Disable auto-start
sudo systemctl disable derpyd
```

### Checking Daemon Status

```bash
# Check if daemon is running
sudo systemctl status derpyd

# Check if socket exists
ls -l /var/run/derpy.sock

# Test daemon connectivity (as regular user)
derpy build --help  # Will use daemon if available
```

## Example Configurations

The `examples/daemon/` directory contains example configuration files and scripts that demonstrate various daemon setup scenarios. These examples are fully commented and can be customized for your specific needs.

### Available Examples

1. **derpyd.service.example** - Comprehensive systemd service file with detailed comments
2. **daemon-config.yaml.example** - Reference configuration showing all available options
3. **setup-user.sh.example** - Customizable user setup script with automation examples

See [examples/daemon/README.md](../examples/daemon/README.md) for detailed documentation and usage instructions.

### Quick Example: Custom Service Configuration

```bash
# Copy and customize the example service file
sudo cp examples/daemon/derpyd.service.example /etc/systemd/system/derpyd.service
sudo nano /etc/systemd/system/derpyd.service

# Reload and start
sudo systemctl daemon-reload
sudo systemctl enable derpyd
sudo systemctl start derpyd
```

### Quick Example: Batch User Setup

```bash
# Use the example script to add multiple users
sudo bash examples/daemon/setup-user.sh.example alice bob charlie
```

For more examples including Ansible, Docker, and cloud-init integration, see the [examples directory](../examples/daemon/).

## Configuration Options

### Daemon Configuration

The daemon can be configured via command-line arguments or environment variables.

**Command-line Arguments:**

```bash
derpyd [OPTIONS]

Options:
  --socket PATH          Socket path (default: /var/run/derpy.sock)
  --group NAME          Group name for access control (default: derpy)
  --max-workers N       Maximum concurrent builds (default: 4)
  --log-level LEVEL     Logging level (DEBUG, INFO, WARNING, ERROR)
  --version             Show version and exit
  --help                Show help message
```

**Environment Variables:**

```bash
# Socket path
export DERPYD_SOCKET_PATH=/var/run/derpy.sock

# Group name
export DERPYD_GROUP_NAME=derpy

# Max concurrent builds
export DERPYD_MAX_WORKERS=4

# Log level
export DERPYD_LOG_LEVEL=INFO
```

### Systemd Service Configuration

Edit `/etc/systemd/system/derpyd.service`:

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

# Environment variables
Environment="DERPYD_MAX_WORKERS=8"
Environment="DERPYD_LOG_LEVEL=INFO"

# Security settings
NoNewPrivileges=false
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/run /var/lib/derpy /root/.derpy

[Install]
WantedBy=multi-user.target
```

After editing, reload systemd:

```bash
sudo systemctl daemon-reload
sudo systemctl restart derpyd
```

### Build Configuration

Users can configure build settings in `~/.derpy/config.yaml`:

```yaml
build_settings:
  enable_isolation: true
  base_image_cache_dir: /home/user/.derpy/cache/base-images
  chroot_timeout: 600
```

These settings are used by the daemon when executing builds.

## Logging and Debugging

### Log Locations

**Systemd Journal:**

The daemon logs to the systemd journal by default:

```bash
# View all daemon logs
sudo journalctl -u derpyd

# Follow logs in real-time
sudo journalctl -u derpyd -f

# View logs since last boot
sudo journalctl -u derpyd -b

# View logs for specific time range
sudo journalctl -u derpyd --since "2024-01-15 10:00" --until "2024-01-15 11:00"

# View logs with specific priority
sudo journalctl -u derpyd -p err  # Errors only
sudo journalctl -u derpyd -p warning  # Warnings and above
```

### Log Levels

The daemon supports four log levels:

- **DEBUG**: Detailed information for diagnosing problems
- **INFO**: General informational messages (default)
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error messages for failures

Set log level via command-line or environment variable:

```bash
# Command-line
sudo derpyd --log-level DEBUG

# Environment variable
export DERPYD_LOG_LEVEL=DEBUG
sudo systemctl restart derpyd
```

### Log Format

Logs include:

- Timestamp
- Log level
- Component name
- Message
- Context (user, operation, etc.)

Example log entries:

```
2024-01-15 10:30:15 INFO [server] Daemon started, listening on /var/run/derpy.sock
2024-01-15 10:30:20 INFO [auth] User 'alice' (uid=1000) authenticated successfully
2024-01-15 10:30:21 INFO [handler] Build request received: tag=myapp:latest
2024-01-15 10:32:45 INFO [handler] Build completed successfully: tag=myapp:latest
2024-01-15 10:35:10 WARNING [auth] Authentication failed for user 'bob' (uid=1001): not in derpy group
2024-01-15 10:40:00 ERROR [handler] Build failed: tag=webapp:v1, error=Dockerfile not found
```

### Debugging Common Issues

#### Socket Permission Denied

**Symptom:**

```
Error: Permission denied connecting to /var/run/derpy.sock
```

**Solution:**

```bash
# Check if user is in derpy group
groups $USER

# Add user to derpy group
sudo usermod -aG derpy $USER

# Log out and back in for changes to take effect
```

#### Daemon Not Running

**Symptom:**

```
Error: Daemon not running. Start with: sudo systemctl start derpyd
```

**Solution:**

```bash
# Check daemon status
sudo systemctl status derpyd

# Start daemon
sudo systemctl start derpyd

# Check logs for errors
sudo journalctl -u derpyd -n 50
```

#### Socket File Missing

**Symptom:**

```
Error: Socket file /var/run/derpy.sock does not exist
```

**Solution:**

```bash
# Check if daemon is running
sudo systemctl status derpyd

# Check daemon logs for startup errors
sudo journalctl -u derpyd -n 50

# Verify socket path in service file
sudo cat /etc/systemd/system/derpyd.service | grep ExecStart

# Restart daemon
sudo systemctl restart derpyd
```

#### Build Timeout

**Symptom:**

```
Error: Daemon not responding. Check logs: sudo journalctl -u derpyd
```

**Solution:**

```bash
# Check daemon logs
sudo journalctl -u derpyd -n 100

# Increase chroot timeout in config
derpy config set build_settings.chroot_timeout 1200

# Restart daemon
sudo systemctl restart derpyd
```

#### Concurrent Build Limit

**Symptom:**

```
Warning: Server busy, request queued
```

**Solution:**

```bash
# Increase max workers in service file
sudo nano /etc/systemd/system/derpyd.service
# Add: Environment="DERPYD_MAX_WORKERS=8"

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart derpyd
```

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
# Stop daemon
sudo systemctl stop derpyd

# Start in foreground with debug logging
sudo derpyd --socket /var/run/derpy.sock --log-level DEBUG

# In another terminal, run your build
derpy build . -f Dockerfile -t myapp:latest

# Observe detailed logs in daemon terminal
```

## Performance Tuning

### Concurrent Build Limits

The daemon can handle multiple concurrent builds. Adjust based on system resources:

```bash
# For systems with 4+ CPU cores and 8GB+ RAM
export DERPYD_MAX_WORKERS=8

# For systems with 2 CPU cores and 4GB RAM
export DERPYD_MAX_WORKERS=2

# For high-performance build servers
export DERPYD_MAX_WORKERS=16
```

**Guidelines:**

- 1 worker per 2 CPU cores
- Minimum 2GB RAM per worker
- Consider disk I/O capacity

### Base Image Cache

Configure base image cache location for optimal performance:

```bash
# Use fast SSD for cache
derpy config set build_settings.base_image_cache_dir /mnt/ssd/derpy-cache

# Use separate disk to avoid I/O contention
derpy config set build_settings.base_image_cache_dir /mnt/cache/derpy
```

### Socket Buffer Size

For high-throughput scenarios, increase socket buffer size:

```python
# In daemon configuration (future enhancement)
socket_buffer_size: 65536  # 64KB (default: 8KB)
```

### Memory Management

Monitor daemon memory usage:

```bash
# Check daemon memory usage
ps aux | grep derpyd

# Monitor in real-time
watch -n 1 'ps aux | grep derpyd'
```

Expected memory usage:

- Base daemon: ~50MB
- Per active build: ~100-500MB (depends on build complexity)
- Base image cache: Disk only, not in memory

### Performance Metrics

**Socket Communication Overhead:**

- Request serialization: <1ms
- Socket round-trip: 1-2ms
- Total overhead: ~2-3ms per request

**Build Performance:**

- No performance impact on build execution itself
- Concurrent builds limited by system resources, not daemon
- Build isolation overhead: ~50-100ms per RUN instruction

**Optimization Tips:**

1. Use local base image cache to avoid repeated downloads
2. Minimize number of RUN instructions in Dockerfile
3. Use multi-stage builds to reduce final image size
4. Run daemon on fast storage (SSD)
5. Ensure adequate RAM for concurrent builds

### Monitoring

Monitor daemon health and performance:

```bash
# Check daemon uptime
sudo systemctl status derpyd | grep Active

# Monitor system resources
htop  # Look for derpyd process

# Check socket connections
sudo lsof /var/run/derpy.sock

# Monitor build queue
# (Future enhancement: derpy daemon status)
```

## Security Considerations

### Access Control

- Only users in `derpy` group can connect to daemon
- Group membership verified using kernel-provided socket credentials
- Cannot be bypassed by manipulating client code

### Input Validation

- All request fields validated before execution
- Path validation prevents directory traversal (../, etc.)
- Command sanitization prevents injection attacks
- Build args validated for safe characters

### Privilege Management

- Daemon runs as root but drops privileges when possible
- Temporary directories created with 0700 permissions
- Build isolation uses chroot for filesystem containment
- No privilege escalation paths for unprivileged users

### Audit Trail

- All authentication attempts logged
- All operations logged with user context
- Failed operations logged with error details
- Sensitive data (credentials) sanitized from logs

### Best Practices

1. **Limit group membership**: Only add trusted users to `derpy` group
2. **Monitor logs**: Regularly review daemon logs for suspicious activity
3. **Keep updated**: Install security updates promptly
4. **Restrict socket**: Ensure socket permissions remain 0660
5. **Use HTTPS**: Always use HTTPS for registry communication
6. **Rotate credentials**: Periodically rotate registry credentials

## Troubleshooting

### Common Issues

#### "Permission denied" Error

**Cause**: User not in `derpy` group

**Solution**:

```bash
sudo usermod -aG derpy $USER
# Log out and back in
```

#### "Daemon not running" Error

**Cause**: Daemon service not started

**Solution**:

```bash
sudo systemctl start derpyd
sudo systemctl enable derpyd  # Auto-start on boot
```

#### "Connection timeout" Error

**Cause**: Daemon unresponsive or overloaded

**Solution**:

```bash
# Check daemon status
sudo systemctl status derpyd

# Check logs for errors
sudo journalctl -u derpyd -n 50

# Restart daemon
sudo systemctl restart derpyd
```

#### Build Fails with Daemon but Works with Sudo

**Cause**: Daemon configuration or permissions issue

**Solution**:

```bash
# Check daemon logs
sudo journalctl -u derpyd -f

# Verify build isolation enabled
derpy config show | grep enable_isolation

# Check base image cache permissions
ls -la ~/.derpy/cache/base-images/

# Try with debug logging
sudo systemctl stop derpyd
sudo derpyd --log-level DEBUG
```

### Getting Help

If you encounter issues not covered here:

1. Check daemon logs: `sudo journalctl -u derpyd -n 100`
2. Enable debug logging: `sudo derpyd --log-level DEBUG`
3. Check GitHub issues: https://github.com/yourusername/derpy/issues
4. File a bug report with logs and system information

## Version Compatibility

### Protocol Versioning

The daemon protocol is versioned to ensure compatibility:

- **v1.0**: Initial release (Derpy 0.2.0)
- Future versions will maintain backward compatibility
- Protocol version included in all messages

### Client-Daemon Compatibility

- CLI and daemon versions should match
- Older CLI may work with newer daemon (forward compatibility)
- Newer CLI may not work with older daemon (backward compatibility not guaranteed)

**Check versions**:

```bash
derpy --version
sudo derpyd --version
```

## Migration Guide

### Upgrading from Direct Execution (v0.1.0)

1. Install daemon: `sudo scripts/install-daemon.sh`
2. Add users to group: `sudo usermod -aG derpy $USER`
3. Users log out and back in
4. Existing commands work unchanged
5. No sudo required for builds

### Downgrading to Direct Execution

1. Stop daemon: `sudo systemctl stop derpyd`
2. Disable daemon: `sudo systemctl disable derpyd`
3. Use sudo for builds: `sudo derpy build ...`
4. All existing images and config preserved

## Future Enhancements

Planned features for future releases:

- **Remote daemon**: Connect to daemon on remote host
- **Build queue management**: View and manage queued builds
- **Resource limits**: Per-user build limits and quotas
- **Build caching**: Layer caching for faster rebuilds
- **Metrics API**: Prometheus-compatible metrics endpoint
- **Web UI**: Web-based dashboard for monitoring
- **Multi-platform**: macOS and Windows support (if feasible)

## References

- [Installation Guide](installation.md)
- [User Guide](../README.md)
- [Troubleshooting Guide](troubleshooting.md)
- [API Documentation](api/daemon-protocol.md)
- [Architecture Documentation](architecture/README.md)
