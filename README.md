# Derpy - Independent Container Tool

Derpy is an independent container tool that does not depend on Docker, Podman, containerd, or any other container runtime. It's a Python CLI application that provides essential container functionality, building, managing, and distributing OCI-compliant container images from scratch.

**Note**: While Derpy is independent of container runtimes, it does use minimal Python dependencies (like PyYAML) for configuration management.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Supported Dockerfile Instructions](#supported-dockerfile-instructions-v010)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Daemon vs Direct Execution](#daemon-vs-direct-execution)
- [Usage](#usage)
  - [Authentication](#authentication)
  - [Building Images](#building-images)
  - [Listing Images](#listing-images)
  - [Removing Images](#removing-images)
  - [Pushing Images](#pushing-images)
  - [Verbose and Debug Output](#verbose-and-debug-output)
  - [Getting Help](#getting-help)
- [Examples](#examples)
  - [Example Dockerfiles](#example-dockerfiles)
  - [Authentication Examples](#authentication-examples)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Development](#development)
  - [Setting Up Development Environment](#setting-up-development-environment)
  - [Running Without Installation](#running-without-installation)
  - [Deactivating Virtual Environment](#deactivating-virtual-environment)
  - [Version Management](#version-management)
  - [Project Status](#project-status)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Dockerfile Support**: Parse and build from familiar Dockerfile syntax
- **OCI Compliance**: Generate fully compliant OCI container images
- **Build Isolation**: Execute RUN commands in isolated chroot environments using base image filesystems (Linux only)
- **Daemon Architecture**: Optional privileged daemon (derpyd) eliminates the need for sudo on every build command
- **Base Image Support**: Automatically pull and cache base images from OCI registries
- **Local Repository**: Manage images in a local repository
- **Registry Integration**: Push images to OCI-compliant registries
- **Cross-Platform**: Works on Windows, Linux, and macOS
- **Runtime Independent**: No dependency on Docker, Podman, containerd, or other container runtimes
- **Minimal Dependencies**: Uses only essential Python packages

## Requirements

- Python 3.10 or higher
- No Docker, Podman, or containerd installation required

### For Build Isolation (Real-World Container Builds)

Build isolation enables building images that depend on base image filesystems and package managers (apt, apk, yum, etc.):

- **Linux**: Full support with root privileges (`sudo`) or CAP_SYS_CHROOT capability
- **macOS/Windows**: Not supported; builds automatically fall back to v0.1.0 behavior

Without isolation, only simple RUN commands that don't depend on base image filesystems will work (e.g., `echo`, basic shell commands).

## Supported Dockerfile Instructions (v0.1.0)

Derpy v0.1.0 supports a subset of Dockerfile instructions:

- `FROM`: Specify base image
- `RUN`: Execute commands during build
- `CMD`: Set default command for container

Additional instructions will be added in future releases.

## Installation

### For Regular Use (Non-Daemon)

Install from PyPI using pipx (recommended) or pip:

```bash
# Using pipx (recommended for Ubuntu 23.04+, Debian 12+)
pipx install derpy-tool

# Or using pip in a virtual environment
python3 -m venv venv
source venv/bin/activate
pip install derpy-tool
```

### For Daemon Setup (Linux Only)

For daemon installation, you need system-wide access:

```bash
# Install pipx if not already installed
sudo apt update
sudo apt install -y pipx

# Install derpy-tool system-wide
sudo pipx install derpy-tool --global

# Or on older distributions (Ubuntu 22.04)
sudo pip install derpy-tool
```

The package is named `derpy-tool` on PyPI, but the command-line tool is simply `derpy`.

**Note**: On modern Linux distributions (Ubuntu 23.04+, Debian 12+), pip is externally managed by the system package manager. Use `pipx` for isolated installation or `sudo pip` for system-wide installation (required for daemon setup).

## Quick Start

```bash
# Check version
derpy --version

# Build an image (with daemon if available, otherwise requires sudo)
derpy build . -f Dockerfile -t myapp:latest

# List local images
derpy ls

# Remove an image
derpy rm myapp:latest

# Remove all images
derpy purge --force

# Push to registry
derpy push myapp:latest
```

**Note**: If you have the daemon installed and are in the `derpy` group, builds run without sudo. Otherwise, use `sudo derpy build` for build isolation on Linux. See [Daemon vs Direct Execution](#daemon-vs-direct-execution) for details.

Images are stored in a shared repository managed by the daemon at `/var/lib/derpy/images` (daemon mode) or `~/.derpy/images` (direct execution fallback).

## Daemon vs Direct Execution

Derpy v0.2.0 introduces an optional daemon architecture that eliminates the need for sudo on every build command. This section explains how the daemon works, when it's used, and how to set it up.

### Overview

Derpy can operate in two modes:

1. **Daemon Mode** (Recommended for Linux): The `derpyd` daemon runs as a privileged background service. Users in the `derpy` group can build images without sudo by communicating with the daemon via Unix socket. Images are stored in a shared repository at `/var/lib/derpy/images`.

2. **Direct Execution Mode**: The CLI executes build operations directly, requiring sudo for build isolation on Linux. This is the fallback mode when the daemon is unavailable. Images are stored at `~/.derpy/images`.

### How the Daemon Works

```
┌─────────────────┐                    ┌──────────────────┐
│   derpy build   │◄──────────────────►│     derpyd       │
│  (unprivileged) │   Unix Socket      │  (privileged)    │
│                 │  /var/run/derpy.   │                  │
│                 │       sock          │                  │
└─────────────────┘                    └──────────────────┘
         │                                      │
         │                                      │
         ▼                                      ▼
  User commands                        Build operations with
  without sudo                         root privileges
```

**Key Benefits**:

- No need to type `sudo` for every build command
- Secure group-based access control
- Concurrent builds from multiple users
- Automatic fallback to direct execution if daemon unavailable
- Full backward compatibility with existing workflows

### When is the Daemon Used?

The CLI automatically detects and uses the daemon when:

1. The daemon is running (socket exists at `/var/run/derpy.sock`)
2. The user is in the `derpy` group (has socket permissions)
3. The socket is accessible

**Automatic Fallback**: If the daemon is unavailable, the CLI automatically falls back to direct execution with a warning. This ensures existing workflows continue to work.

### Setting Up the Daemon (Linux Only)

The daemon is currently only supported on Linux systems with systemd.

**Tested Distributions**:

- Ubuntu 22.04 LTS
- Debian 12 (Bookworm)
- Fedora 39
- Arch Linux (rolling)

For distribution-specific installation notes and testing procedures, see the [Distribution Testing Guide](docs/distribution-testing.md).

#### Prerequisites

- Linux operating system with systemd
- Python 3.10 or higher
- Root access for installation

#### Installation Steps

1. **Install Derpy** (if not already installed):

```bash
# Using pipx (recommended for Ubuntu 23.04+, Debian 12+)
sudo apt update
sudo apt install -y pipx
sudo pipx install derpy-tool --global

# Or using pip on older distributions (Ubuntu 22.04)
sudo pip install derpy-tool
```

2. **View setup instructions**:

```bash
derpy daemon setup-info
```

This command displays step-by-step instructions for downloading and installing the daemon.

3. **Download the installation script**:

```bash
# Download the installation script
curl -O https://raw.githubusercontent.com/adonis-legon/derpy/main/scripts/install-daemon.sh

# Make the script executable
chmod +x install-daemon.sh
```

4. **Run the installation script**:

```bash
sudo bash install-daemon.sh
```

This script will:

- Create the `derpy` system group
- Install the `derpyd` daemon
- Set up the systemd service
- Start the daemon
- Create the Unix socket at `/var/run/derpy.sock`

5. **Add your user to the derpy group**:

```bash
sudo usermod -aG derpy $USER
```

6. **Log out and back in** for group membership to take effect:

```bash
# Check your groups
groups
# Should include 'derpy'
```

7. **Verify the daemon is running**:

```bash
# Check service status
sudo systemctl status derpyd

# Check socket exists
ls -l /var/run/derpy.sock
# Should show: srw-rw---- 1 root derpy ... /var/run/derpy.sock
```

#### Managing the Daemon

```bash
# Start the daemon
sudo systemctl start derpyd

# Stop the daemon
sudo systemctl stop derpyd

# Restart the daemon
sudo systemctl restart derpyd

# Check daemon status
sudo systemctl status derpyd

# View daemon logs
sudo journalctl -u derpyd -f

# Enable daemon to start on boot
sudo systemctl enable derpyd

# Disable daemon from starting on boot
sudo systemctl disable derpyd
```

### Building with the Daemon

Once the daemon is set up and you're in the `derpy` group, building is simple:

```bash
# Build without sudo - daemon handles privileges automatically
derpy build . -f Dockerfile -t myapp:latest

# The CLI automatically:
# 1. Detects the daemon is available
# 2. Sends the build request to the daemon
# 3. Streams output back to you in real-time
# 4. Displays the final result
```

**Output Example**:

```bash
$ derpy build . -f Dockerfile -t myapp:latest
Building image myapp:latest...
Step 1/3: FROM ubuntu:22.04
Pulling base image ubuntu:22.04...
Step 2/3: RUN apt-get update && apt-get install -y curl
 ---> Running in isolated environment
Get:1 http://archive.ubuntu.com/ubuntu jammy InRelease [270 kB]
...
Step 3/3: CMD ["/bin/bash"]
Successfully built myapp:latest
```

### Fallback to Direct Execution

If the daemon is not available, the CLI automatically falls back to direct execution:

```bash
$ derpy build . -f Dockerfile -t myapp:latest
Warning: Daemon not available, falling back to direct execution
This requires sudo privileges for build isolation.
Error: Insufficient permissions for chroot. Run with sudo or install the daemon.
```

In this case, use sudo:

```bash
sudo derpy build . -f Dockerfile -t myapp:latest
```

### Daemon vs Direct Execution Comparison

| Feature                | Daemon Mode      | Direct Execution |
| ---------------------- | ---------------- | ---------------- |
| **Requires sudo**      | No (after setup) | Yes (for builds) |
| **Setup required**     | Yes (one-time)   | No               |
| **Concurrent builds**  | Yes              | Yes              |
| **Platform support**   | Linux only       | All platforms    |
| **Automatic fallback** | N/A              | Yes              |
| **Group membership**   | Required         | Not required     |

### Group Membership Requirement

To use the daemon, you must be in the `derpy` group. This provides secure access control to the daemon socket.

**Check your group membership**:

```bash
groups
# Should include 'derpy'
```

**Add yourself to the group** (requires sudo):

```bash
sudo usermod -aG derpy $USER
```

**Important**: You must log out and back in for group changes to take effect. Simply opening a new terminal is not sufficient.

**Verify access**:

```bash
# Check socket permissions
ls -l /var/run/derpy.sock
# Should show: srw-rw---- 1 root derpy

# Try building without sudo
derpy build . -f Dockerfile -t test:latest
```

### Security Considerations

The daemon architecture is designed with security in mind:

- **Socket Permissions**: The Unix socket has 0660 permissions (owner: root, group: derpy)
- **Group-Based Access**: Only users in the `derpy` group can connect
- **Credential Validation**: The daemon verifies connecting user's group membership
- **Request Validation**: All requests are validated before execution
- **Input Sanitization**: User inputs are sanitized to prevent injection attacks
- **Privilege Separation**: The daemon drops privileges for non-critical operations
- **Audit Logging**: All operations are logged to the system journal

**Best Practices**:

- Only add trusted users to the `derpy` group
- Regularly review group membership: `getent group derpy`
- Monitor daemon logs for suspicious activity: `sudo journalctl -u derpyd`
- Keep the daemon updated with security patches

### Troubleshooting Daemon Issues

See the [Troubleshooting](#troubleshooting) section for common daemon-related issues and solutions.

## Usage

### Authentication

Derpy supports authentication with container registries for pulling private base images and pushing images to authenticated registries.

#### Login to a Registry

Authenticate with a container registry:

```bash
derpy login [REGISTRY]
```

If no registry is specified, Docker Hub (`docker.io`) is used by default.

Examples:

```bash
# Login to Docker Hub (interactive prompts)
derpy login

# Login to Docker Hub with username and password
derpy login -u myusername -p mypassword

# Login to a private registry
derpy login registry.example.com

# Login with password from stdin (useful for CI/CD)
echo "$PASSWORD" | derpy login --password-stdin registry.example.com
```

Options:

- `-u, --username`: Username for authentication
- `-p, --password`: Password for authentication (not recommended for security reasons)
- `--password-stdin`: Read password from standard input

**Security Note**: For interactive use, it's recommended to omit the password option and let Derpy prompt you securely. This prevents the password from appearing in your shell history.

#### Logout from a Registry

Remove stored credentials for a registry:

```bash
derpy logout [REGISTRY]
```

Examples:

```bash
# Logout from Docker Hub
derpy logout

# Logout from a private registry
derpy logout registry.example.com
```

#### Credential Storage

Credentials are stored securely in `~/.derpy/auth.json` with the following characteristics:

- File permissions are automatically set to `0600` (owner read/write only)
- Passwords are base64-encoded (not encrypted, but not plaintext)
- Multiple registry credentials can be stored simultaneously
- Credentials persist across sessions until explicitly removed with `logout`

**Security Considerations**:

- The auth file is protected with restrictive permissions (0600)
- Only the file owner can read or write credentials
- Derpy warns if incorrect permissions are detected and automatically fixes them
- For maximum security, use `derpy logout` when credentials are no longer needed

### Building Images

Build a container image from a Dockerfile:

```bash
derpy build [CONTEXT] -f [DOCKERFILE] -t [TAG]
```

Options:

- `CONTEXT`: Build context directory (default: current directory)
- `-f, --file`: Path to Dockerfile (default: ./Dockerfile)
- `-t, --tag`: Name and optionally a tag in 'name:tag' format

Example:

```bash
derpy build . -f Dockerfile -t myapp:v1.0
```

#### Build Isolation (Linux Only)

On Linux systems, Derpy automatically enables build isolation, which:

- Downloads and caches base images from OCI registries
- Extracts base image layers into a temporary filesystem
- Executes RUN commands in a chrooted environment using the base image's tools
- Captures filesystem changes as proper OCI layers
- Combines base and new layers into the final image

#### With Daemon (Recommended)

If you have the daemon installed and are in the `derpy` group, simply run:

```bash
# Build without sudo - daemon handles privileges
derpy build . -f Dockerfile -t myapp:latest

# Build Ubuntu image with apt-get
derpy build . -f Dockerfile -t ubuntu-app:latest

# Build Alpine image with apk
derpy build . -f Dockerfile -t alpine-app:latest
```

The CLI automatically detects the daemon and uses it for privileged operations.

#### Without Daemon (Direct Execution)

If the daemon is not available, build isolation requires root privileges. Use `sudo`:

```bash
# Build Ubuntu image with apt-get (requires sudo)
sudo derpy build . -f Dockerfile -t ubuntu-app:latest

# Build Alpine image with apk (requires sudo)
sudo derpy build . -f Dockerfile -t alpine-app:latest

# Build nginx with custom content (requires sudo)
sudo derpy build examples/nginx-web -f examples/nginx-web/Dockerfile -t nginx-web:latest
```

**Without sudo**: Derpy detects insufficient permissions and automatically falls back to v0.1.0 behavior (commands execute on the host system). This works for simple commands but fails for operations requiring base image filesystems.

On macOS and Windows, isolation is automatically disabled and builds use the v0.1.0 behavior (commands execute on the host system).

### Listing Images

View all locally stored images:

```bash
derpy ls
```

This displays:

- Image names and tags
- Creation dates
- Image sizes

### Removing Images

Remove images from local storage to free up disk space.

#### Remove a Single Image

Remove a specific image by tag:

```bash
derpy rm [IMAGE:TAG]
```

Example:

```bash
derpy rm myapp:v1.0
```

This will:

- Remove the image from local storage
- Display the amount of disk space freed
- Show an error if the image doesn't exist

#### Remove All Images

Remove all images and cached data:

```bash
derpy purge
```

This command will:

- Display a warning with the total number of images and disk space to be freed
- Prompt for confirmation before proceeding
- Remove all images from local storage
- Clear the base image cache directory

To skip the confirmation prompt, use the `--force` flag:

```bash
derpy purge --force
```

**Warning**: The purge operation cannot be undone. Make sure you have pushed any important images to a registry before purging.

### Pushing Images

Upload an image to a remote registry:

```bash
derpy push [IMAGE:TAG]
```

Example:

```bash
derpy push myapp:v1.0
```

### Verbose and Debug Output

Derpy supports verbose and debug logging to help you understand what's happening during builds and other operations.

#### Verbose Mode

Enable verbose output to see INFO level logs showing build progress, layer operations, and registry interactions:

```bash
# Build with verbose output
derpy --verbose build . -f Dockerfile -t myapp:latest

# Short form
derpy -v build . -f Dockerfile -t myapp:latest

# Push with verbose output (recommended for troubleshooting uploads)
derpy -v push myapp:latest
derpy -v push registry.example.com/myapp:v1.0

# Works with any command
derpy --verbose ls
derpy --verbose login
```

Verbose output shows:

- Build progress and instruction execution
- Base image download and caching
- Layer creation and merging
- Registry authentication and uploads
- **Push operations**: Layer-by-layer upload progress with sizes, blob deduplication, and upload status
- File operations and snapshots

**Recommended for push operations**: Use verbose mode when pushing images to see detailed upload progress, identify which layers are being uploaded, and troubleshoot timeout or network issues.

#### Debug Mode

Enable debug output for even more detailed logging, including DEBUG level messages:

```bash
# Build with debug output
derpy --debug build . -f Dockerfile -t myapp:latest

# Works with any command
derpy --debug login
derpy --debug push myapp:latest
```

Debug output includes everything from verbose mode plus:

- Detailed HTTP requests and responses
- File system operations
- Token authentication flows
- Tar archive operations
- Snapshot comparisons

**When to use verbose/debug**:

- Troubleshooting build failures
- Understanding why a build is slow
- Debugging authentication issues
- Investigating layer caching behavior
- Reporting bugs (include debug output in bug reports)

### Getting Help

Get help for any command:

```bash
derpy --help
derpy build --help
derpy push --help
```

## Development

### Setting Up Development Environment

It's recommended to use a virtual environment to isolate derpy's dependencies from your system Python packages (especially if you manage Python via Homebrew or other system package managers):

```bash
# Clone the repository
git clone https://github.com/derpy-team/derpy.git
cd derpy

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install in development mode
pip install -e .

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

### Running Without Installation

You can also run derpy directly from the source without installing:

```bash
# Activate your virtual environment first
source venv/bin/activate

# Run derpy module
python -m derpy.cli.main --version
```

### Deactivating Virtual Environment

When you're done developing:

```bash
deactivate
```

### Version Management

Derpy includes a version management script to keep version numbers synchronized across the project:

```bash
# Show current version
python scripts/version.py show

# Set a specific version
python scripts/version.py set 0.2.0

# Bump major version (1.0.0 -> 2.0.0)
python scripts/version.py bump major

# Bump minor version (0.1.0 -> 0.2.0)
python scripts/version.py bump minor

# Bump patch version (0.1.0 -> 0.1.1)
python scripts/version.py bump patch
```

The script automatically updates both `pyproject.toml` and `derpy/__init__.py` to keep them in sync.

**Workflow for releasing a new version:**

1. Update the version:

   ```bash
   python scripts/version.py bump minor
   ```

2. Create a release branch:

   ```bash
   git checkout -b release/0.2.0
   git add derpy/__init__.py pyproject.toml
   git commit -m "Bump version to 0.2.0"
   ```

3. Push the release branch to trigger CI/CD:

   ```bash
   git push origin release/0.2.0
   ```

The CI/CD pipeline will automatically test, build, publish to PyPI, and merge back to main.

For detailed release instructions, see [CONTRIBUTING.md](CONTRIBUTING.md#release-process)

### Project Status

**Current Version: 0.2.1** - Alpha release with core functionality and daemon support.

**Key Features:**

- ✅ Core Dockerfile instructions (FROM, RUN, CMD, COPY, ADD, WORKDIR, ENV, EXPOSE, USER, LABEL)
- ✅ OCI-compliant image building and distribution
- ✅ Build isolation with chroot on Linux
- ✅ Registry authentication (Docker Hub, private registries, AWS ECR)
- ✅ Daemon architecture for unprivileged builds
- ✅ Base image caching and management
- ✅ Local image repository
- ✅ Cross-platform support (Linux, macOS, Windows)

**In Development:**

- 🚧 Additional Dockerfile instructions (VOLUME, ENTRYPOINT, ARG, ONBUILD)
- 🚧 Multi-stage builds
- 🚧 Build caching and layer optimization
- 🚧 Container runtime capabilities

See the project roadmap and [CONTRIBUTING.md](CONTRIBUTING.md) for more information on planned features.

## Examples

### Example Dockerfiles

#### Simple Python Application

```dockerfile
FROM python:3.11-slim
RUN pip install flask
CMD ["python", "-m", "flask", "run"]
```

#### Basic Web Server

```dockerfile
FROM nginx:alpine
RUN echo "Hello from Derpy!" > /usr/share/nginx/html/index.html
CMD ["nginx", "-g", "daemon off;"]
```

#### Ubuntu with Package Installation

```dockerfile
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y curl wget
RUN curl --version
CMD ["/bin/bash"]
```

#### Alpine with Development Tools

```dockerfile
FROM alpine:latest
RUN apk add --no-cache git python3 py3-pip
RUN python3 --version
CMD ["/bin/sh"]
```

See the `examples/` directory for more sample Dockerfiles.

### Authentication Examples

#### Docker Hub Authentication

Docker Hub allows anonymous pulls for public images, but authenticated users get higher rate limits and access to private repositories.

```bash
# Login to Docker Hub
derpy login
# Enter username and password when prompted

# Build with a public base image (works with or without authentication)
derpy build . -f Dockerfile -t myapp:latest

# Build with a private base image (requires authentication)
# Dockerfile: FROM myusername/private-base:latest
sudo derpy build . -f Dockerfile -t myapp:latest

# Push to Docker Hub (requires authentication)
derpy push myusername/myapp:latest

# Logout when done
derpy logout
```

#### Private Registry Authentication

For self-hosted or third-party private registries:

```bash
# Login to private registry
derpy login registry.example.com
# Enter username and password when prompted

# Build with private base image from your registry
# Dockerfile: FROM registry.example.com/base-images/ubuntu:22.04
sudo derpy build . -f Dockerfile -t myapp:latest

# Push to private registry
derpy push registry.example.com/myteam/myapp:v1.0

# Logout when done
derpy logout registry.example.com
```

#### AWS ECR Authentication

Amazon Elastic Container Registry (ECR) uses temporary tokens for authentication:

```bash
# Get ECR login token (requires AWS CLI)
aws ecr get-login-password --region us-east-1 | derpy login --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com -u AWS

# Build with ECR base image
# Dockerfile: FROM 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-base:latest
sudo derpy build . -f Dockerfile -t myapp:latest

# Push to ECR
derpy push 123456789012.dkr.ecr.us-east-1.amazonaws.com/myapp:v1.0

# Note: ECR tokens expire after 12 hours
# Re-authenticate if you see authentication errors
```

#### CI/CD Pipeline Authentication

For automated builds in CI/CD environments:

```bash
# Using environment variables and stdin (GitHub Actions, GitLab CI, etc.)
echo "$REGISTRY_PASSWORD" | derpy login --password-stdin registry.example.com -u "$REGISTRY_USERNAME"

# Build and push
sudo derpy build . -f Dockerfile -t registry.example.com/myapp:$CI_COMMIT_TAG
derpy push registry.example.com/myapp:$CI_COMMIT_TAG

# Cleanup
derpy logout registry.example.com
```

### Building with Private Base Images

When your Dockerfile uses a private base image, ensure you're authenticated before building:

```dockerfile
# Dockerfile
FROM registry.example.com/internal/python-base:3.11
RUN pip install flask
CMD ["python", "app.py"]
```

```bash
# Authenticate first
derpy login registry.example.com

# Build (requires sudo for isolation on Linux)
sudo derpy build . -f Dockerfile -t myapp:latest

# Note: When using sudo, derpy automatically uses your user's credentials
# from ~/.derpy/auth.json (not root's credentials)
```

## Troubleshooting

### Daemon Issues

#### "Daemon not available" Warning

**Problem**: CLI displays "Warning: Daemon not available, falling back to direct execution"

**Solution**: This means the daemon is not running or not accessible. Check:

1. **Is the daemon installed?**

```bash
which derpyd
# Should show: /usr/local/bin/derpyd or similar
```

2. **Is the daemon running?**

```bash
sudo systemctl status derpyd
# Should show: active (running)
```

If not running, start it:

```bash
sudo systemctl start derpyd
```

3. **Does the socket exist?**

```bash
ls -l /var/run/derpy.sock
# Should show: srw-rw---- 1 root derpy
```

4. **Are you in the derpy group?**

```bash
groups
# Should include 'derpy'
```

If not, add yourself and log out/in:

```bash
sudo usermod -aG derpy $USER
# Then log out and back in
```

#### "Permission denied" on Socket

**Problem**: Cannot connect to daemon socket even though it exists.

**Solution**: You need to be in the `derpy` group:

```bash
# Check your groups
groups

# Add yourself to derpy group
sudo usermod -aG derpy $USER

# IMPORTANT: Log out and back in for changes to take effect
# Opening a new terminal is NOT sufficient
```

Verify after logging back in:

```bash
groups | grep derpy
ls -l /var/run/derpy.sock
```

#### Daemon Won't Start

**Problem**: `systemctl start derpyd` fails or daemon immediately stops.

**Solution**: Check the daemon logs for errors:

```bash
# View recent logs
sudo journalctl -u derpyd -n 50

# Follow logs in real-time
sudo journalctl -u derpyd -f
```

Common issues:

1. **Port/socket already in use**: Another process is using `/var/run/derpy.sock`

```bash
# Check what's using the socket
sudo lsof /var/run/derpy.sock

# Remove stale socket file
sudo rm /var/run/derpy.sock
sudo systemctl start derpyd
```

2. **Python not found**: Ensure Python 3.10+ is installed

```bash
python3 --version
which python3
```

3. **Derpy not installed**: Install derpy first

```bash
pip install derpy-tool
```

#### Daemon Connection Timeout

**Problem**: Build hangs or times out when using daemon.

**Solution**:

1. **Check daemon is responsive**:

```bash
sudo systemctl status derpyd
# Should show: active (running)
```

2. **Check daemon logs for errors**:

```bash
sudo journalctl -u derpyd -n 100
```

3. **Restart the daemon**:

```bash
sudo systemctl restart derpyd
```

4. **Try direct execution as fallback**:

```bash
sudo derpy build . -f Dockerfile -t myapp:latest
```

#### Build Works with Sudo but Not with Daemon

**Problem**: `sudo derpy build` works but `derpy build` (with daemon) fails.

**Solution**: This usually indicates a permission or configuration issue with the daemon:

1. **Check daemon logs**:

```bash
sudo journalctl -u derpyd -n 50
```

2. **Verify daemon has access to required directories**:

```bash
# Check derpy directories
ls -la ~/.derpy/
ls -la ~/.derpy/cache/base-images/

# Ensure daemon can access them
sudo ls -la /root/.derpy/
```

3. **Try rebuilding with verbose output**:

```bash
derpy -v build . -f Dockerfile -t myapp:latest
```

#### Multiple Users Cannot Build Concurrently

**Problem**: Second user's build fails when another user is building.

**Solution**: This should work with the daemon. Check:

1. **Both users are in derpy group**:

```bash
# As each user
groups | grep derpy
```

2. **Daemon is configured for concurrent builds**:

```bash
# Check daemon logs for resource limits
sudo journalctl -u derpyd | grep -i "concurrent\|limit\|queue"
```

3. **Sufficient system resources**:

```bash
# Check disk space
df -h ~/.derpy

# Check memory
free -h
```

### Build Isolation Issues

#### "Platform not supported for isolation" Error

**Problem**: Attempting to use build isolation on macOS or Windows.

**Solution**: Build isolation requires Linux. On other platforms, Derpy automatically falls back to v0.1.0 behavior. To build images with base image dependencies, use:

- A Linux VM (VirtualBox, VMware, Parallels)
- Docker Desktop with Linux containers
- WSL2 on Windows
- A cloud Linux instance

#### "Insufficient permissions for chroot" Error

**Problem**: Running on Linux but without root privileges or CAP_SYS_CHROOT capability.

**Solution**: Run derpy with sudo or grant the capability:

```bash
# Option 1: Run with sudo
sudo derpy build . -f Dockerfile -t myapp:latest

# Option 2: Grant capability (one-time setup)
sudo setcap cap_sys_chroot+ep $(which python3)
```

#### Base Image Download Fails

**Problem**: Cannot download base image from registry.

**Solution**:

1. Check network connectivity
2. Verify the image reference is correct (e.g., "ubuntu:22.04")
3. For private registries, configure authentication in `~/.derpy/config.yaml`
4. Check if the registry is accessible: `curl -I https://registry-1.docker.io/v2/`

### Build Fails with "Command not found"

**Problem**: RUN instruction fails because a command is not available in the base image.

**Solution**: Ensure the base image contains the required tools, or install them first:

```dockerfile
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y curl
RUN curl --version
```

### "No such file or directory" during build

**Problem**: Files referenced in the build context cannot be found.

**Solution**: Verify the build context path and ensure files exist:

```bash
# Check your current directory
ls -la

# Build with explicit context
derpy build /path/to/context -f Dockerfile -t myapp:latest
```

### Permission Denied Errors

**Problem**: Cannot write to `~/.derpy/` directory.

**Solution**: Check directory permissions:

```bash
# On macOS/Linux
chmod 755 ~/.derpy
ls -la ~/.derpy
```

**Note**: With daemon mode, images are stored in `/var/lib/derpy/images` which is managed by the daemon. In direct execution mode, images are stored in `~/.derpy/images`.

### Registry Push Fails

**Problem**: Cannot connect to registry or authentication fails.

**Solution**:

1. Verify registry URL is correct
2. Check network connectivity
3. Ensure you have proper credentials configured
4. Verify the image exists locally: `derpy ls`

### Push Timeout Errors

**Problem**: Push fails with "timeout" or "write operation timed out" error.

**Solution**: This typically occurs when uploading large layers over slow network connections.

1. **Use verbose mode** to see which layer is timing out:

```bash
derpy -v push registry.example.com/myapp:latest
```

2. **Check your network connection**: Large layers (>50MB) may take several minutes to upload

3. **Retry the push**: Derpy automatically skips layers that were already uploaded successfully

4. **Increase timeout** (if needed): The default blob upload timeout is 600 seconds (10 minutes). For very large layers or slow connections, you may need to modify the timeout in the code.

5. **Split large layers**: Consider optimizing your Dockerfile to create smaller layers:

```dockerfile
# Instead of one large RUN command
RUN apt-get update && apt-get install -y package1 package2 package3 ...

# Split into multiple RUN commands (creates separate layers)
RUN apt-get update
RUN apt-get install -y package1 package2
RUN apt-get install -y package3
```

6. **Check registry limits**: Some registries have size limits or rate limits for uploads

**Example with verbose output**:

```bash
$ derpy -v push 123456789012.dkr.ecr.us-east-1.amazonaws.com/myapp:latest

INFO: Pushing image myapp:latest
INFO: Total upload size: 57.00 MB
INFO: Uploading config blob...
INFO: Uploading blob sha256:abc123... (0.01 MB)
INFO: Successfully uploaded blob sha256:abc123... (0.01 MB)
INFO: Uploading 8 layer(s)...
INFO: Uploading layer 1/8: sha256:def456...
INFO: Uploading blob sha256:def456... (25.50 MB)
INFO: Successfully uploaded blob sha256:def456... (25.50 MB)
...
```

This helps identify which specific layer is causing the timeout.

### Unsupported Dockerfile Instruction

**Problem**: Build fails with "unsupported instruction" error.

**Solution**: Derpy v0.1.0 only supports FROM, RUN, and CMD instructions. Remove or comment out unsupported instructions like COPY, ADD, ENV, etc. These will be added in future releases.

### Authentication Failed

**Problem**: Login fails with "Authentication failed" error.

**Solution**:

1. Verify your username and password are correct
2. Check if the registry URL is correct (e.g., `registry.example.com` not `https://registry.example.com`)
3. For Docker Hub, use your Docker Hub username (not email)
4. Ensure the registry is accessible: `curl -I https://registry.example.com/v2/`
5. Check if your account has the necessary permissions
6. For ECR, ensure your AWS credentials are valid and have ECR permissions

```bash
# Try logging in again with correct credentials
derpy login registry.example.com

# For Docker Hub, use your username (not email)
derpy login -u myusername
```

### No Credentials Found

**Problem**: Build or push fails with "No credentials found for registry" error.

**Solution**: You need to authenticate with the registry before pulling private images or pushing:

```bash
# Login to the registry
derpy login registry.example.com

# Then retry your build or push
sudo derpy build . -f Dockerfile -t myapp:latest
derpy push registry.example.com/myapp:latest
```

**Note**: Docker Hub public images can be pulled without authentication, but private images require login.

### Token Request Failed

**Problem**: Build fails with "Failed to obtain authentication token" error.

**Solution**:

1. Check network connectivity to the authentication service
2. Verify the registry's authentication endpoint is accessible
3. For Docker Hub, ensure `https://auth.docker.io` is reachable
4. Check for firewall or proxy issues blocking the token request
5. Try logging out and back in:

```bash
derpy logout registry.example.com
derpy login registry.example.com
```

### Rate Limit Exceeded

**Problem**: Pull fails with "rate limit exceeded" or "too many requests" error.

**Solution**: Docker Hub enforces rate limits on anonymous pulls (100 pulls per 6 hours per IP). Authenticated users get higher limits (200 pulls per 6 hours).

```bash
# Login to Docker Hub for higher rate limits
derpy login

# Then retry your build
sudo derpy build . -f Dockerfile -t myapp:latest
```

**Alternative solutions**:

- Wait for the rate limit window to reset (6 hours)
- Use a Docker Hub Pro account for unlimited pulls
- Use a private registry or mirror
- Cache base images locally (Derpy does this automatically in `~/.derpy/cache/base-images/`)

### ECR Token Expired

**Problem**: AWS ECR authentication fails with "authorization token has expired" error.

**Solution**: ECR tokens expire after 12 hours. Re-authenticate with a fresh token:

```bash
# Get a new ECR token
aws ecr get-login-password --region us-east-1 | \
  derpy login --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com -u AWS

# Then retry your operation
sudo derpy build . -f Dockerfile -t myapp:latest
```

**For CI/CD**: Ensure your pipeline re-authenticates before each build, as tokens may expire between runs.

### Sudo Build Cannot Find Credentials

**Problem**: Building with `sudo` fails to find credentials even after logging in.

**Solution**: Derpy automatically detects when running under `sudo` and uses the original user's credentials from their home directory. However, if this fails:

1. Ensure you logged in as your regular user (not as root):

```bash
# Login as your regular user (without sudo)
derpy login registry.example.com

# Then build with sudo
sudo derpy build . -f Dockerfile -t myapp:latest
```

2. Check that the `SUDO_USER` environment variable is set:

```bash
sudo env | grep SUDO_USER
```

3. Verify your auth file exists and has correct permissions:

```bash
ls -la ~/.derpy/auth.json
# Should show: -rw------- (permissions 600)
```

## FAQ

### Q: Does Derpy require Docker to be installed?

**A**: No! Derpy is completely independent and does not require Docker, Podman, containerd, or any other container runtime.

### Q: Can I run containers built with Derpy?

**A**: Derpy focuses on building and distributing images. Container execution will be added in future releases. However, images built with Derpy are OCI-compliant and can be run with Docker, Podman, or other OCI-compatible runtimes.

### Q: Do I need Linux to use Derpy?

**A**: Derpy works on Windows, Linux, and macOS. However, build isolation with base image support requires Linux. On macOS and Windows, Derpy automatically disables isolation and uses v0.1.0 behavior.

### Q: How does build isolation work?

**A**: On Linux, Derpy downloads base images from registries, extracts their layers into a temporary filesystem, and uses chroot to execute RUN commands in that isolated environment. This allows commands to access tools and dependencies from the base image rather than the host system.

### Q: Are Derpy images compatible with Docker?

**A**: Yes! Derpy generates OCI-compliant images that work with Docker, Podman, Kubernetes, and other OCI-compatible tools.

### Q: Where are images stored locally?

**A**: Images are stored in a shared repository managed by the daemon:

- **Daemon mode**: `/var/lib/derpy/images` (shared across all users)
- **Direct execution**: `~/.derpy/images` (per-user storage)

The CLI automatically uses the appropriate location based on whether the daemon is available.

### Q: What Python version is required?

**A**: Python 3.10 or higher is required.

### Q: Can I use Derpy in CI/CD pipelines?

**A**: Yes! Derpy is designed to work in automated environments. Just ensure Python 3.10+ is available.

### Q: How do I report bugs or request features?

**A**: Please open an issue on the GitHub repository with details about the problem or feature request.

### Daemon-Related FAQs

### Q: Do I need to install the daemon?

**A**: No, the daemon is optional. Derpy works without it, but you'll need to use `sudo` for builds on Linux. The daemon eliminates the need for sudo by running as a privileged background service.

### Q: What's the difference between daemon mode and direct execution?

**A**:

- **Daemon mode**: The CLI communicates with a privileged background service (derpyd) via Unix socket. No sudo needed for builds if you're in the `derpy` group.
- **Direct execution**: The CLI runs build operations directly, requiring sudo for build isolation on Linux.

The CLI automatically uses the daemon if available and falls back to direct execution otherwise.

### Q: Is the daemon required for building images?

**A**: No. The daemon is optional and only available on Linux. Without it, you can still build images using `sudo derpy build` on Linux, or without sudo on macOS/Windows (with limited functionality).

### Q: How do I know if I'm using the daemon or direct execution?

**A**: The CLI automatically detects and uses the daemon if available. If the daemon is not available, you'll see a warning: "Warning: Daemon not available, falling back to direct execution"

You can also check:

```bash
# Check if daemon is running
sudo systemctl status derpyd

# Check if socket exists
ls -l /var/run/derpy.sock

# Check if you're in the derpy group
groups | grep derpy
```

### Q: Why do I need to be in the derpy group?

**A**: The `derpy` group provides secure access control to the daemon socket. Only users in this group can communicate with the daemon and build images without sudo. This prevents unauthorized users from executing privileged operations.

### Q: Do I need to log out after being added to the derpy group?

**A**: Yes! Group membership changes only take effect after you log out and back in. Simply opening a new terminal is not sufficient. After logging back in, verify with `groups | grep derpy`.

### Q: Can multiple users build images at the same time?

**A**: Yes! The daemon is designed to handle concurrent builds from multiple users safely. Each build is isolated and receives its own output stream.

### Q: What happens if the daemon crashes during a build?

**A**: The CLI will detect the connection loss and display an error. The daemon is configured to restart automatically via systemd. You can retry your build after the daemon restarts.

### Q: Can I use the daemon in CI/CD pipelines?

**A**: Yes, but it's often simpler to use direct execution with sudo in CI/CD environments:

```bash
# In CI/CD, use sudo directly
sudo derpy build . -f Dockerfile -t myapp:latest
```

The daemon is most beneficial for interactive development where multiple developers are building frequently.

### Q: Does the daemon work on macOS or Windows?

**A**: No, the daemon is currently only supported on Linux systems with systemd. On macOS and Windows, use direct execution (which doesn't require sudo since build isolation isn't available on those platforms).

### Q: How do I uninstall the daemon?

**A**: To remove the daemon:

```bash
# Stop and disable the service
sudo systemctl stop derpyd
sudo systemctl disable derpyd

# Remove the service file
sudo rm /etc/systemd/system/derpyd.service
sudo systemctl daemon-reload

# Remove the socket
sudo rm /var/run/derpy.sock

# Optionally remove the derpy group
sudo groupdel derpy
```

### Q: Where are daemon logs stored?

**A**: Daemon logs are stored in the systemd journal. View them with:

```bash
# View recent logs
sudo journalctl -u derpyd -n 50

# Follow logs in real-time
sudo journalctl -u derpyd -f

# View logs since last boot
sudo journalctl -u derpyd -b
```

### Q: Is the daemon secure?

**A**: Yes, the daemon is designed with security in mind:

- Socket has restrictive permissions (0660, owner: root, group: derpy)
- Only users in the derpy group can connect
- All requests are validated before execution
- User inputs are sanitized to prevent injection attacks
- The daemon drops privileges for non-critical operations
- All operations are logged for audit purposes

Only add trusted users to the `derpy` group.

## Contributing

Contributions are welcome! Please see CONTRIBUTING.md for guidelines.

## License

MIT License - see LICENSE file for details.
