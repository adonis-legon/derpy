# Derpy Daemon Installation Guide

This guide covers the installation and configuration of the Derpy daemon (derpyd) for version 0.2.0 and later. The daemon enables unprivileged users to build container images without using sudo for every command.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation Steps](#installation-steps)
- [Group Creation and User Management](#group-creation-and-user-management)
- [Service Configuration](#service-configuration)
- [Verification Steps](#verification-steps)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Before installing the Derpy daemon, ensure your system meets the following requirements:

### Operating System

- **Linux**: Required (Ubuntu 22.04+, Debian 12+, Fedora 39+, Arch Linux, or similar)
- **macOS**: Not supported (daemon functionality unavailable, CLI falls back to direct execution)
- **Windows**: Not supported (daemon functionality unavailable, CLI falls back to direct execution)

### Software Requirements

- **Python**: 3.10 or later (3.10, 3.11, 3.12, 3.13 supported)
- **systemd**: Required for service management
- **Root access**: Required for installation and daemon operation

### System Resources

- **Disk space**: ~50MB for daemon and dependencies
- **Memory**: ~50MB for daemon process
- **Network**: Internet access for downloading base images

## Installation Steps

### Step 1: Install Derpy Package

First, install the Derpy package. On modern Linux distributions (Ubuntu 23.04+, Debian 12+), use `pipx` for isolated installation:

**Option A: Using pipx (Recommended for Ubuntu 23.04+, Debian 12+)**

```bash
# Install pipx if not already installed
sudo apt update
sudo apt install -y pipx

# Ensure pipx binaries are in PATH
pipx ensurepath

# Install derpy-tool
pipx install derpy-tool
```

**Option B: Using pip with sudo (Ubuntu 22.04, older distributions)**

```bash
# Install from PyPI
sudo pip install derpy-tool
```

**Option C: Using pip with --break-system-packages (Not recommended)**

```bash
# Only use if you understand the risks
pip install --break-system-packages derpy-tool
```

Verify the installation:

```bash
derpy --version
derpyd --version
```

### Step 2: View Setup Instructions

Display the daemon setup instructions:

```bash
derpy daemon setup-info
```

This command will show you the exact steps needed to download and install the daemon.

### Step 3: Download Installation Script

Download the installation script from GitHub:

```bash
# Download the installation script
curl -O https://raw.githubusercontent.com/adonis-legon/derpy/main/scripts/install-daemon.sh

# Make the script executable
chmod +x install-daemon.sh
```

**Alternative: Clone the Repository**

If you prefer to have all scripts and examples:

```bash
git clone https://github.com/adonis-legon/derpy.git
cd derpy
```

### Step 4: Run Installation Script

Run the automated installation script that handles group creation, service installation, and initial configuration:

```bash
# If you downloaded the script directly
sudo bash install-daemon.sh

# Or if you cloned the repository
sudo bash scripts/install-daemon.sh
```

The script performs the following actions:

1. Creates the `derpy` system group (if it doesn't exist)
2. Installs the derpyd binary
3. Copies the systemd service file to `/etc/systemd/system/`
4. Reloads systemd configuration
5. Enables the derpyd service to start on boot
6. Starts the derpyd service
7. Verifies the socket is created with correct permissions

**Alternative: Custom Installation**

For custom configurations, you can use the example files in `examples/daemon/`:

```bash
# Copy and customize the service file
sudo cp examples/daemon/derpyd.service.example /etc/systemd/system/derpyd.service
sudo nano /etc/systemd/system/derpyd.service

# Reload and start
sudo systemctl daemon-reload
sudo systemctl enable derpyd
sudo systemctl start derpyd
```

See [examples/daemon/README.md](../examples/daemon/README.md) for detailed configuration examples including high-performance, development, and production scenarios.

### Step 3: Verify Installation

After the installation script completes, verify the daemon is running:

```bash
# Check service status
sudo systemctl status derpyd

# Verify socket exists
ls -l /var/run/derpy.sock
```

Expected output for the socket:

```
srw-rw---- 1 root derpy 0 Nov 22 10:00 /var/run/derpy.sock
```

The socket should have:

- Type: Unix domain socket (indicated by `s` at the start)
- Permissions: `0660` (read/write for owner and group)
- Owner: `root`
- Group: `derpy`

## Group Creation and User Management

### Understanding the Derpy Group

The `derpy` group controls access to the daemon socket. Users must be members of this group to run derpy commands without sudo.

### Adding Users to the Derpy Group

#### Using the Helper Script

Derpy provides a helper script for adding users:

```bash
sudo bash scripts/add-user-to-derpy.sh <username>
```

For example, to add the user `alice`:

```bash
sudo bash scripts/add-user-to-derpy.sh alice
```

#### Using the Example Script

For more advanced scenarios (batch user setup, automation, integration with LDAP/AD), use the customizable example script:

```bash
# Single user
sudo bash examples/daemon/setup-user.sh.example alice

# Multiple users
sudo bash examples/daemon/setup-user.sh.example alice bob charlie
```

The example script includes templates for:

- Batch user setup from files
- LDAP/Active Directory integration
- Cloud-init configuration
- Ansible playbook integration
- Docker container initialization

See [examples/daemon/README.md](../examples/daemon/README.md) for customization details.

#### Manual User Addition

Alternatively, add users manually using `usermod`:

```bash
sudo usermod -aG derpy <username>
```

### Applying Group Changes

**Important**: Group membership changes require the user to log out and log back in to take effect.

```bash
# After being added to the group, log out and back in
# Then verify group membership:
groups
# Should include "derpy" in the output

# Or check specifically:
id -nG | grep derpy
```

### Removing Users from the Derpy Group

To revoke a user's access to the daemon:

```bash
sudo gpasswd -d <username> derpy
```

The user must log out and back in for the change to take effect.

## Service Configuration

### Systemd Service File

The daemon is managed by systemd using the service file at `/etc/systemd/system/derpyd.service`:

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

### Service Management Commands

```bash
# Start the daemon
sudo systemctl start derpyd

# Stop the daemon
sudo systemctl stop derpyd

# Restart the daemon
sudo systemctl restart derpyd

# Check daemon status
sudo systemctl status derpyd

# Enable daemon to start on boot
sudo systemctl enable derpyd

# Disable daemon from starting on boot
sudo systemctl disable derpyd

# View daemon logs
sudo journalctl -u derpyd

# Follow daemon logs in real-time
sudo journalctl -u derpyd -f
```

### Configuration Options

The daemon accepts the following command-line options (configured in the systemd service file):

- `--socket PATH`: Unix socket path (default: `/var/run/derpy.sock`)
- `--log-level LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `--max-workers N`: Maximum concurrent build operations (default: 4)

To customize these options, edit the service file:

```bash
sudo systemctl edit derpyd
```

Add your overrides:

```ini
[Service]
ExecStart=
ExecStart=/usr/local/bin/derpyd --socket /var/run/derpy.sock --max-workers 8 --log-level INFO
```

Then reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart derpyd
```

### Automatic Startup

The daemon is configured to start automatically on system boot. To verify:

```bash
sudo systemctl is-enabled derpyd
# Should output: enabled
```

## Verification Steps

### Step 1: Verify Daemon is Running

```bash
sudo systemctl status derpyd
```

Expected output should show:

- Active: `active (running)`
- Main PID: A process ID number
- No error messages in recent logs

### Step 2: Verify Socket Permissions

```bash
ls -l /var/run/derpy.sock
```

Should show:

- Permissions: `srw-rw----` (0660)
- Owner: `root`
- Group: `derpy`

### Step 3: Verify Group Membership

As a user who was added to the derpy group (after logging out and back in):

```bash
groups | grep derpy
```

Should include `derpy` in the output.

### Step 4: Test Build Command

As a regular user (in the derpy group):

```bash
# Create a simple test Dockerfile
mkdir -p /tmp/derpy-test
cd /tmp/derpy-test
cat > Dockerfile << 'EOF'
FROM alpine:latest
RUN echo "Hello from Derpy daemon!"
CMD ["/bin/sh"]
EOF

# Build without sudo
derpy build . -f Dockerfile -t test:latest
```

Expected behavior:

- Build should succeed without requiring sudo
- Output should stream in real-time
- No permission errors

### Step 5: Verify Daemon Logs

Check that the daemon logged the build operation:

```bash
sudo journalctl -u derpyd -n 50
```

Should show:

- Connection accepted from your user
- Build request received
- Build completed successfully

## Troubleshooting

### Issue: "Daemon not running" Error

**Symptoms**: CLI displays "Daemon not running. Start with: sudo systemctl start derpyd"

**Causes**:

- Daemon service is not started
- Daemon crashed or failed to start
- Socket file was deleted

**Solutions**:

1. Check daemon status:

   ```bash
   sudo systemctl status derpyd
   ```

2. If inactive, start the daemon:

   ```bash
   sudo systemctl start derpyd
   ```

3. If failed, check logs for errors:

   ```bash
   sudo journalctl -u derpyd -n 100
   ```

4. Common startup failures:
   - **Port/socket already in use**: Another process is using the socket path
     ```bash
     sudo rm /var/run/derpy.sock
     sudo systemctl start derpyd
     ```
   - **Permission errors**: Check that `/var/run` is writable by root
   - **Missing dependencies**: Reinstall derpy package

### Issue: "Permission denied" Error

**Symptoms**: CLI displays "Access denied. Add yourself to derpy group: sudo usermod -aG derpy $USER"

**Causes**:

- User is not in the derpy group
- User hasn't logged out/in after being added to group
- Socket permissions are incorrect

**Solutions**:

1. Verify group membership:

   ```bash
   groups | grep derpy
   ```

2. If not in group, add yourself:

   ```bash
   sudo usermod -aG derpy $USER
   ```

3. **Log out and log back in** (this is required!)

4. Verify socket permissions:

   ```bash
   ls -l /var/run/derpy.sock
   ```

   Should show group `derpy` with `rw-` permissions.

5. If socket permissions are wrong, restart daemon:
   ```bash
   sudo systemctl restart derpyd
   ```

### Issue: "Connection timeout" Error

**Symptoms**: CLI displays "Daemon not responding. Check logs: sudo journalctl -u derpyd"

**Causes**:

- Daemon is hung or overloaded
- Daemon is processing too many concurrent requests
- System resource exhaustion

**Solutions**:

1. Check daemon logs:

   ```bash
   sudo journalctl -u derpyd -n 100
   ```

2. Check system resources:

   ```bash
   top
   df -h
   ```

3. Restart the daemon:

   ```bash
   sudo systemctl restart derpyd
   ```

4. If problem persists, increase max workers:
   ```bash
   sudo systemctl edit derpyd
   ```
   Add:
   ```ini
   [Service]
   ExecStart=
   ExecStart=/usr/local/bin/derpyd --max-workers 8
   ```

### Issue: Build Fails with Daemon but Works with Sudo

**Symptoms**: `derpy build` fails when using daemon, but `sudo derpy build` works

**Causes**:

- Daemon lacks access to build context or Dockerfile
- File permissions prevent daemon from reading files
- Path resolution issues

**Solutions**:

1. Ensure build context is readable:

   ```bash
   chmod -R o+r /path/to/build/context
   ```

2. Use absolute paths:

   ```bash
   derpy build $(pwd) -f $(pwd)/Dockerfile -t myapp:latest
   ```

3. Check daemon logs for specific errors:
   ```bash
   sudo journalctl -u derpyd -n 50
   ```

### Issue: Socket File Missing After Reboot

**Symptoms**: Socket file doesn't exist after system restart

**Causes**:

- Daemon service not enabled for automatic startup
- Daemon failed to start on boot

**Solutions**:

1. Enable daemon to start on boot:

   ```bash
   sudo systemctl enable derpyd
   ```

2. Check if daemon is running:

   ```bash
   sudo systemctl status derpyd
   ```

3. If not running, check boot logs:
   ```bash
   sudo journalctl -u derpyd -b
   ```

### Issue: Multiple Users Building Concurrently Causes Errors

**Symptoms**: Builds fail or produce errors when multiple users build simultaneously

**Causes**:

- Resource contention
- Insufficient max workers setting
- Disk space exhaustion

**Solutions**:

1. Increase max workers:

   ```bash
   sudo systemctl edit derpyd
   ```

   Add:

   ```ini
   [Service]
   ExecStart=
   ExecStart=/usr/local/bin/derpyd --max-workers 8
   ```

2. Check disk space:

   ```bash
   df -h ~/.derpy
   ```

3. Monitor daemon logs during concurrent builds:
   ```bash
   sudo journalctl -u derpyd -f
   ```

### Issue: Daemon Logs Show "Command injection attempt blocked"

**Symptoms**: Build fails with security error in daemon logs

**Causes**:

- Dockerfile contains commands that trigger security validation
- False positive from input sanitization

**Solutions**:

1. Review the Dockerfile for unusual characters or patterns
2. Check daemon logs for the specific command that was blocked:
   ```bash
   sudo journalctl -u derpyd | grep "injection"
   ```
3. If it's a false positive, report it as a bug
4. As a workaround, use direct execution:
   ```bash
   sudo derpy build . -f Dockerfile -t myapp:latest
   ```

### Getting Help

If you encounter issues not covered here:

1. Check daemon logs: `sudo journalctl -u derpyd -n 100`
2. Check daemon status: `sudo systemctl status derpyd`
3. Verify configuration: `derpy config show`
4. Review the [daemon documentation](daemon.md)
5. Check the [troubleshooting guide](troubleshooting.md)
6. Report issues on GitHub: https://github.com/yourusername/derpy/issues

### Uninstallation

To completely remove the daemon:

```bash
# Stop and disable the service
sudo systemctl stop derpyd
sudo systemctl disable derpyd

# Remove service file
sudo rm /etc/systemd/system/derpyd.service
sudo systemctl daemon-reload

# Remove socket file
sudo rm -f /var/run/derpy.sock

# Optionally remove the derpy group
sudo groupdel derpy

# Uninstall the package
sudo pip uninstall derpy
```

## Next Steps

After successful installation:

1. Read the [daemon documentation](daemon.md) to understand the architecture
2. Review the [user guide](../README.md) for build command examples
3. Configure build settings: `derpy config set build_settings.enable_isolation true`
4. Start building containers: `derpy build . -f Dockerfile -t myapp:latest`

## Distribution-Specific Notes

### Tested Distributions

Derpy daemon has been tested on the following Linux distributions:

- **Ubuntu 22.04 LTS** - Fully supported
- **Debian 12 (Bookworm)** - Fully supported
- **Fedora 39** - Fully supported
- **Arch Linux** (rolling) - Fully supported

For detailed testing procedures and results, see [Distribution Testing Guide](distribution-testing.md).

### Ubuntu/Debian

- Python 3.10+ may need to be installed from deadsnakes PPA on older versions
- systemd is included by default
- Use `apt` package manager for prerequisites

**Installation:**

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
```

### Fedora

- Python 3.10+ is available in default repositories
- systemd is included by default
- Use `dnf` package manager for prerequisites

**Installation:**

```bash
sudo dnf update -y
sudo dnf install -y python3 python3-pip git
```

### Arch Linux

- Python 3.10+ is available in default repositories
- systemd is included by default
- May need to install `python-pip` separately
- Use `pacman` package manager for prerequisites

**Installation:**

```bash
sudo pacman -Syu --noconfirm
sudo pacman -S --noconfirm python python-pip git
```

### Other Distributions

The daemon should work on any Linux distribution with:

- Python 3.10+
- systemd
- Standard Unix utilities (groupadd, usermod, etc.)

If you encounter distribution-specific issues, please report them on GitHub.

### Testing on Your Distribution

To verify Derpy daemon works correctly on your distribution, use the automated testing script:

```bash
# After installing Derpy
sudo bash scripts/test-distribution.sh
```

This will run a comprehensive test suite and generate a results file at `~/derpy-test-results.txt`.

For manual testing procedures, see the [Distribution Testing Guide](distribution-testing.md).
