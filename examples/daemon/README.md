# Derpy Daemon Configuration Examples

This directory contains example configuration files and scripts for the Derpy daemon (derpyd). These examples demonstrate various configuration options and deployment scenarios.

## Files

### 1. derpyd.service.example

Example systemd service file with detailed comments explaining all configuration options.

**Purpose**: Shows how to configure the derpyd systemd service with various options including:

- Socket path configuration
- Log level settings
- Security hardening options
- Resource limits
- Restart policies

**Usage**:

```bash
# Copy to systemd directory
sudo cp derpyd.service.example /etc/systemd/system/derpyd.service

# Edit as needed
sudo nano /etc/systemd/system/derpyd.service

# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl enable derpyd
sudo systemctl start derpyd
```

**Key Configuration Options**:

- `ExecStart`: Command-line options for derpyd (socket path, log level, max workers)
- `Restart`: Service restart behavior
- `ReadWritePaths`: Directories the daemon needs write access to
- Security settings: `ProtectSystem`, `ProtectHome`, `PrivateTmp`, etc.

### 2. daemon-config.yaml.example

Example YAML configuration file showing all available daemon settings.

**Purpose**: Reference documentation for daemon configuration options. While the current daemon uses command-line flags, this file demonstrates what a future YAML-based configuration might include.

**Configuration Categories**:

- **Socket Configuration**: Path, permissions, group ownership
- **Daemon Behavior**: Worker limits, timeouts, shutdown behavior
- **Logging**: Log levels, formats, destinations
- **Build Settings**: Isolation, caching, chroot timeouts
- **Security Settings**: Credential validation, input sanitization, privilege dropping
- **Registry Settings**: Timeouts, retries, authentication
- **Performance Settings**: Concurrent operations, buffer sizes
- **Monitoring**: Metrics, health checks, profiling

**Example Scenarios**:

- High-performance server configuration
- Development environment with debug logging
- Secure production environment
- Resource-constrained system

### 3. setup-user.sh.example

Example user setup script with extensive customization options.

**Purpose**: Demonstrates how to automate adding users to the derpy group for daemon access. Can be customized for different deployment scenarios.

**Features**:

- Batch user processing
- Verification of daemon status
- Detailed logging with color output
- Error handling and validation
- Summary reporting

**Usage**:

```bash
# Single user
sudo bash setup-user.sh.example alice

# Multiple users
sudo bash setup-user.sh.example alice bob charlie

# Customize for your environment
cp setup-user.sh.example /usr/local/bin/derpy-add-user
chmod +x /usr/local/bin/derpy-add-user
sudo derpy-add-user newuser
```

**Customization Examples Included**:

1. Batch user setup from a file
2. Integration with LDAP/Active Directory
3. Cloud-init integration
4. Ansible playbook integration
5. Docker container initialization

## Quick Start

### Basic Installation

1. Install the daemon:

```bash
sudo scripts/install-daemon.sh
```

2. Add a user to the derpy group:

```bash
sudo scripts/add-user-to-derpy.sh <username>
```

3. User logs out and back in, then tests access:

```bash
derpy build . -f Dockerfile -t myapp:latest
```

### Custom Installation

1. Copy and customize the service file:

```bash
sudo cp examples/daemon/derpyd.service.example /etc/systemd/system/derpyd.service
sudo nano /etc/systemd/system/derpyd.service
```

2. Reload and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable derpyd
sudo systemctl start derpyd
```

3. Verify the service is running:

```bash
sudo systemctl status derpyd
ls -l /var/run/derpy.sock
```

4. Add users using the example script:

```bash
sudo bash examples/daemon/setup-user.sh.example alice bob
```

## Configuration Scenarios

### Development Environment

For a development environment with verbose logging:

```ini
# In derpyd.service
ExecStart=/usr/local/bin/derpyd --socket /var/run/derpy.sock --log-level DEBUG
```

### Production Environment

For a production environment with security hardening:

```ini
# In derpyd.service
[Service]
ExecStart=/usr/local/bin/derpyd --socket /var/run/derpy.sock --log-level INFO
NoNewPrivileges=false
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ProtectKernelLogs=yes
ProtectKernelModules=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
```

### High-Performance Server

For a server handling many concurrent builds:

```ini
# In derpyd.service
ExecStart=/usr/local/bin/derpyd --socket /var/run/derpy.sock --max-workers 16
MemoryLimit=8G
CPUQuota=800%
```

### Resource-Constrained System

For a system with limited resources:

```ini
# In derpyd.service
ExecStart=/usr/local/bin/derpyd --socket /var/run/derpy.sock --max-workers 2
MemoryLimit=1G
CPUQuota=100%
```

## Integration Examples

### Ansible

```yaml
- name: Install derpy daemon
  pip:
    name: derpy
    state: present

- name: Create derpy group
  group:
    name: derpy
    state: present
    system: yes

- name: Copy systemd service file
  copy:
    src: derpyd.service
    dest: /etc/systemd/system/derpyd.service
    mode: "0644"

- name: Enable and start derpyd
  systemd:
    name: derpyd
    enabled: yes
    state: started
    daemon_reload: yes

- name: Add users to derpy group
  user:
    name: "{{ item }}"
    groups: derpy
    append: yes
  loop:
    - alice
    - bob
    - charlie
```

### Docker

```dockerfile
# In a Dockerfile for a build container
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y python3 python3-pip
RUN pip3 install derpy

# Create derpy group and add user
RUN groupadd -r derpy && \
    useradd -r -g derpy -G derpy builduser

USER builduser
```

### Cloud-Init

```yaml
#cloud-config
packages:
  - python3-pip

runcmd:
  - pip3 install derpy
  - groupadd -r derpy
  - cp /tmp/derpyd.service /etc/systemd/system/
  - systemctl daemon-reload
  - systemctl enable derpyd
  - systemctl start derpyd
  - usermod -aG derpy ubuntu
```

## Troubleshooting

### Socket Not Created

If the socket is not created after starting the service:

```bash
# Check service status
sudo systemctl status derpyd

# Check logs
sudo journalctl -u derpyd -n 50

# Verify permissions on /var/run
ls -ld /var/run
```

### Permission Denied

If users get "permission denied" errors:

```bash
# Verify user is in derpy group
groups <username>

# Verify socket permissions
ls -l /var/run/derpy.sock

# User must log out and back in after being added to group
```

### Service Won't Start

If the service fails to start:

```bash
# Check for errors in logs
sudo journalctl -u derpyd -n 100

# Verify derpyd binary exists
which derpyd

# Try running manually to see errors
sudo /usr/local/bin/derpyd --socket /var/run/derpy.sock
```

## Additional Resources

- [Installation Guide](../../docs/installation.md)
- [Daemon Documentation](../../docs/daemon.md)
- [Troubleshooting Guide](../../docs/troubleshooting.md)
- [Security Documentation](../../docs/SECURITY.md)

## Contributing

If you have additional configuration examples or deployment scenarios, please contribute them! See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.
