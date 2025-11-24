# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with Derpy.

## Table of Contents

- [Daemon Issues](#daemon-issues)
  - [Checking Daemon Status](#checking-daemon-status)
  - [Viewing Daemon Logs](#viewing-daemon-logs)
  - [Restarting the Daemon](#restarting-the-daemon)
  - [Common Socket Permission Issues](#common-socket-permission-issues)
  - [Common Daemon Errors](#common-daemon-errors)
- [Build Issues](#build-issues)
- [Registry Issues](#registry-issues)
- [General Issues](#general-issues)

---

## Daemon Issues

The Derpy daemon (derpyd) runs as a privileged background service to handle container operations without requiring sudo for every command. This section covers common daemon-related issues.

### Checking Daemon Status

To check if the daemon is running:

```bash
# Check service status
sudo systemctl status derpyd

# Check if socket exists
ls -l /var/run/derpy.sock
```

**Expected output when running:**

```
● derpyd.service - Derpy Container Daemon
     Loaded: loaded (/etc/systemd/system/derpyd.service; enabled; vendor preset: enabled)
     Active: active (running) since Sat 2025-01-15 10:30:00 UTC; 2h 15min ago
```

**If daemon is not running:**

```
● derpyd.service - Derpy Container Daemon
     Loaded: loaded (/etc/systemd/system/derpyd.service; enabled; vendor preset: enabled)
     Active: inactive (dead)
```

### Viewing Daemon Logs

The daemon logs to the systemd journal. Use these commands to view logs:

```bash
# View recent logs
sudo journalctl -u derpyd

# Follow logs in real-time
sudo journalctl -u derpyd -f

# View logs from the last hour
sudo journalctl -u derpyd --since "1 hour ago"

# View logs with specific priority (errors only)
sudo journalctl -u derpyd -p err

# View logs from today
sudo journalctl -u derpyd --since today

# View last 100 lines
sudo journalctl -u derpyd -n 100
```

**Log locations:**

- Systemd journal: `journalctl -u derpyd`
- Syslog (if configured): `/var/log/syslog` or `/var/log/messages`

### Restarting the Daemon

To restart the daemon:

```bash
# Restart the daemon
sudo systemctl restart derpyd

# Stop the daemon
sudo systemctl stop derpyd

# Start the daemon
sudo systemctl start derpyd

# Reload systemd configuration (after editing service file)
sudo systemctl daemon-reload
sudo systemctl restart derpyd
```

**Graceful restart:**
The daemon completes in-progress operations before shutting down. If you need to force-stop:

```bash
# Force stop (not recommended during builds)
sudo systemctl kill derpyd
```

### Common Socket Permission Issues

#### Issue: "Permission denied" when running derpy commands

**Symptoms:**

```
Error: Permission denied connecting to /var/run/derpy.sock
```

**Cause:** Your user is not in the `derpy` group.

**Solution:**

```bash
# Add your user to the derpy group
sudo usermod -aG derpy $USER

# Verify group membership
groups $USER

# Log out and log back in for changes to take effect
# Or use: newgrp derpy
```

**Verification:**

```bash
# Check if you're in the derpy group
id | grep derpy

# Try running a derpy command
derpy ls
```

#### Issue: Socket file has wrong permissions

**Symptoms:**

```
Error: Cannot access /var/run/derpy.sock
```

**Cause:** Socket file permissions are incorrect.

**Solution:**

```bash
# Check current permissions
ls -l /var/run/derpy.sock

# Expected: srw-rw---- 1 root derpy 0 ... /var/run/derpy.sock

# If permissions are wrong, restart the daemon
sudo systemctl restart derpyd

# Verify permissions after restart
ls -l /var/run/derpy.sock
```

#### Issue: Socket file doesn't exist

**Symptoms:**

```
Error: Daemon not running. Socket not found at /var/run/derpy.sock
```

**Cause:** Daemon is not running or failed to start.

**Solution:**

```bash
# Check daemon status
sudo systemctl status derpyd

# If not running, start it
sudo systemctl start derpyd

# Check logs for startup errors
sudo journalctl -u derpyd -n 50

# Verify socket was created
ls -l /var/run/derpy.sock
```

#### Issue: Socket exists but daemon not responding

**Symptoms:**

```
Error: Connection timeout. Daemon not responding.
```

**Cause:** Daemon process is hung or crashed.

**Solution:**

```bash
# Check if daemon process is running
ps aux | grep derpyd

# Check daemon logs for errors
sudo journalctl -u derpyd -n 100

# Restart the daemon
sudo systemctl restart derpyd

# If restart fails, check for port conflicts
sudo lsof /var/run/derpy.sock
```

### Common Daemon Errors

#### Error: "Daemon not running"

**Full error message:**

```
Error: Daemon not running. Start with: sudo systemctl start derpyd
```

**Cause:** The derpyd service is not running.

**Solution:**

```bash
# Start the daemon
sudo systemctl start derpyd

# Enable daemon to start on boot
sudo systemctl enable derpyd

# Verify it's running
sudo systemctl status derpyd
```

**If daemon fails to start:**

```bash
# Check logs for startup errors
sudo journalctl -u derpyd -n 50

# Common startup issues:
# - Port/socket already in use
# - Permission issues with /var/run
# - Missing dependencies
# - Configuration errors
```

#### Error: "Access denied. Add yourself to derpy group"

**Full error message:**

```
Error: Access denied. Add yourself to derpy group: sudo usermod -aG derpy $USER
```

**Cause:** Your user account is not in the `derpy` group.

**Solution:**

```bash
# Add yourself to the derpy group
sudo usermod -aG derpy $USER

# Verify the change
groups $USER

# Log out and log back in
# Or start a new shell with the group: newgrp derpy

# Test access
derpy ls
```

#### Error: "Daemon not accepting connections"

**Full error message:**

```
Error: Daemon not accepting connections. Check status: sudo systemctl status derpyd
```

**Cause:** Daemon is running but not accepting new connections (possibly overloaded or misconfigured).

**Solution:**

```bash
# Check daemon status
sudo systemctl status derpyd

# Check daemon logs
sudo journalctl -u derpyd -n 100

# Look for errors like:
# - "Too many open files"
# - "Resource temporarily unavailable"
# - "Connection refused"

# Restart the daemon
sudo systemctl restart derpyd
```

#### Error: "Connection timeout"

**Full error message:**

```
Error: Daemon not responding. Check logs: sudo journalctl -u derpyd
```

**Cause:** Daemon is unresponsive (hung, crashed, or overloaded).

**Solution:**

```bash
# Check if daemon is actually running
sudo systemctl status derpyd

# Check system resources
top
df -h

# Check daemon logs for errors
sudo journalctl -u derpyd -n 100

# Restart the daemon
sudo systemctl restart derpyd

# If problem persists, check for:
# - Disk space issues
# - Memory exhaustion
# - Deadlocks in daemon code
```

#### Error: "Protocol error: Invalid response from daemon"

**Full error message:**

```
Error: Protocol error: Invalid response from daemon
```

**Cause:** Version mismatch between CLI and daemon, or corrupted communication.

**Solution:**

```bash
# Check CLI version
derpy --version

# Check daemon version (from logs)
sudo journalctl -u derpyd | grep version

# If versions don't match, reinstall
pip install --upgrade derpy

# Restart daemon after upgrade
sudo systemctl restart derpyd
```

#### Error: "Connection lost to daemon during operation"

**Full error message:**

```
Error: Connection lost to daemon during operation
```

**Cause:** Daemon crashed or was restarted during a build.

**Solution:**

```bash
# Check daemon logs for crash information
sudo journalctl -u derpyd -n 100

# Look for:
# - Segmentation faults
# - Out of memory errors
# - Unhandled exceptions

# Restart the daemon
sudo systemctl restart derpyd

# Retry your operation
derpy build . -f Dockerfile -t myapp:latest
```

#### Error: "Server busy" or request queueing

**Symptoms:**

```
Warning: Daemon at capacity, request queued
```

**Cause:** Too many concurrent operations.

**Solution:**

```bash
# Check how many builds are running
ps aux | grep derpy

# Wait for current operations to complete
# Or increase daemon worker limit in configuration

# Check daemon configuration
sudo systemctl cat derpyd

# Edit service file to increase workers
sudo systemctl edit derpyd

# Add:
# [Service]
# Environment="DERPY_MAX_WORKERS=8"

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart derpyd
```

---

## Build Issues

### Build fails with daemon but works with sudo

**Symptoms:**
Build succeeds when run with `sudo derpy build` but fails when using daemon.

**Cause:** Daemon may have different permissions or environment than direct execution.

**Solution:**

```bash
# Check daemon logs for specific error
sudo journalctl -u derpyd -f

# Run build again and watch logs
derpy build . -f Dockerfile -t myapp:latest

# Common issues:
# - Missing environment variables
# - Different PATH in daemon context
# - Permission issues with build context files
```

### Build isolation not working

**Symptoms:**

```
Error: Build isolation requires root privileges
```

**Cause:** Daemon not running with sufficient privileges.

**Solution:**

```bash
# Verify daemon is running as root
ps aux | grep derpyd

# Check service configuration
sudo systemctl cat derpyd

# Ensure service runs as root (default)
# Restart if needed
sudo systemctl restart derpyd
```

---

## Registry Issues

### Authentication fails through daemon

**Symptoms:**

```
Error: Failed to authenticate with registry
```

**Cause:** Daemon may not have access to your credentials.

**Solution:**

```bash
# Credentials are stored per-user
# Daemon uses root's credentials by default

# Option 1: Login as root
sudo derpy login

# Option 2: Ensure daemon reads user credentials
# (This depends on daemon configuration)

# Check credential file permissions
ls -l ~/.derpy/auth.json
```

---

## General Issues

### Fallback to direct execution

**Symptoms:**

```
Warning: Daemon not available, falling back to direct execution
This requires sudo privileges for build isolation.
```

**Cause:** Daemon is not running or not accessible.

**Solution:**

```bash
# Start the daemon
sudo systemctl start derpyd

# Verify it's accessible
derpy ls

# If you want to use direct execution, that's fine too
# Just use sudo:
sudo derpy build . -f Dockerfile -t myapp:latest
```

### Command hangs indefinitely

**Symptoms:**
Command appears to hang with no output.

**Cause:** Daemon may be waiting for resources or deadlocked.

**Solution:**

```bash
# Cancel the command (Ctrl+C)

# Check daemon status
sudo systemctl status derpyd

# Check daemon logs
sudo journalctl -u derpyd -n 100

# Restart daemon if needed
sudo systemctl restart derpyd
```

### Getting Help

If you encounter an issue not covered here:

1. **Check daemon logs:** `sudo journalctl -u derpyd -n 100`
2. **Check daemon status:** `sudo systemctl status derpyd`
3. **Verify group membership:** `groups $USER`
4. **Check socket permissions:** `ls -l /var/run/derpy.sock`
5. **Try direct execution:** `sudo derpy build ...` (to isolate daemon issues)
6. **Report the issue:** Include logs and error messages when reporting bugs

### Quick Diagnostic Checklist

Run through this checklist to diagnose daemon issues:

```bash
# 1. Is daemon running?
sudo systemctl status derpyd

# 2. Does socket exist?
ls -l /var/run/derpy.sock

# 3. Am I in the derpy group?
groups $USER | grep derpy

# 4. Can I connect to the socket?
derpy ls

# 5. Are there errors in logs?
sudo journalctl -u derpyd -n 50

# 6. Is daemon version correct?
derpy --version
sudo journalctl -u derpyd | grep version
```

If all checks pass but you still have issues, restart the daemon:

```bash
sudo systemctl restart derpyd
```
