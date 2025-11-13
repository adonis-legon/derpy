# Derpy - Independent Container Tool

Derpy is an independent container tool that does not depend on Docker, Podman, containerd, or any other container runtime. It's a Python CLI application that provides essential container functionality, building, managing, and distributing OCI-compliant container images from scratch.

**Note**: While Derpy is independent of container runtimes, it does use minimal Python dependencies (like PyYAML) for configuration management.

## Features

- **Dockerfile Support**: Parse and build from familiar Dockerfile syntax
- **OCI Compliance**: Generate fully compliant OCI container images
- **Build Isolation**: Execute RUN commands in isolated chroot environments using base image filesystems (Linux only)
- **Base Image Support**: Automatically pull and cache base images from OCI registries
- **Local Repository**: Manage images in a local repository
- **Registry Integration**: Push images to OCI-compliant registries
- **Cross-Platform**: Works on Windows, Linux, and macOS
- **Runtime Independent**: No dependency on Docker, Podman, containerd, or other container runtimes
- **Minimal Dependencies**: Uses only essential Python packages

## Installation

```bash
pip install derpy
```

## Quick Start

```bash
# Check version
derpy --version

# Build an image
derpy build . -f Dockerfile -t myapp:latest

# List local images
derpy ls

# Push to registry
derpy push myapp:latest
```

## Usage

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

This allows you to build real-world images that depend on distribution-specific package managers:

```bash
# Build Ubuntu image with apt-get
derpy build . -f Dockerfile -t ubuntu-app:latest

# Build Alpine image with apk
derpy build . -f Dockerfile -t alpine-app:latest
```

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

### Pushing Images

Upload an image to a remote registry:

```bash
derpy push [IMAGE:TAG]
```

Example:

```bash
derpy push myapp:v1.0
```

### Configuration Management

View current configuration:

```bash
derpy config show
```

Set configuration values:

```bash
derpy config set images_path /custom/path/to/images
```

Configuration is stored in `~/.derpy/config.yaml`

#### Build Isolation Configuration

Configure build isolation behavior (Linux only):

```bash
# Disable isolation (use v0.1.0 behavior)
derpy config set build_settings.enable_isolation false

# Set base image cache directory
derpy config set build_settings.base_image_cache_dir /custom/cache/path

# Set chroot command timeout (seconds)
derpy config set build_settings.chroot_timeout 600
```

Configuration options:

- `enable-isolation`: Enable/disable build isolation (default: true on Linux, false elsewhere)
- `base-image-cache-dir`: Directory for caching downloaded base images (default: ~/.derpy/cache/base-images)
- `chroot-timeout`: Maximum time in seconds for RUN commands in chroot (default: 300)

### Getting Help

Get help for any command:

```bash
derpy --help
derpy build --help
derpy push --help
```

## Requirements

- Python 3.8 or higher
- No Docker, Podman, or containerd installation required
- **For build isolation with base images**: Linux environment (native or VM) with root privileges or CAP_SYS_CHROOT capability
  - On macOS/Windows: Isolation features are disabled; builds fall back to v0.1.0 behavior
  - On Linux: Full isolation support with chroot-based execution

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

## Supported Dockerfile Instructions (v0.1.0)

Derpy v0.1.0 supports a subset of Dockerfile instructions:

- `FROM`: Specify base image
- `RUN`: Execute commands during build
- `CMD`: Set default command for container

Additional instructions will be added in future releases.

## Example Dockerfiles

### Simple Python Application

```dockerfile
FROM python:3.11-slim
RUN pip install flask
CMD ["python", "-m", "flask", "run"]
```

### Basic Web Server

```dockerfile
FROM nginx:alpine
RUN echo "Hello from Derpy!" > /usr/share/nginx/html/index.html
CMD ["nginx", "-g", "daemon off;"]
```

### Ubuntu with Package Installation

```dockerfile
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y curl wget
RUN curl --version
CMD ["/bin/bash"]
```

### Alpine with Development Tools

```dockerfile
FROM alpine:latest
RUN apk add --no-cache git python3 py3-pip
RUN python3 --version
CMD ["/bin/sh"]
```

See the `examples/` directory for more sample Dockerfiles.

## Troubleshooting

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

# Or specify a different path
derpy config set images_path ~/custom/derpy/images
```

### Registry Push Fails

**Problem**: Cannot connect to registry or authentication fails.

**Solution**:

1. Verify registry URL is correct
2. Check network connectivity
3. Ensure you have proper credentials configured
4. Verify the image exists locally: `derpy ls`

### Unsupported Dockerfile Instruction

**Problem**: Build fails with "unsupported instruction" error.

**Solution**: Derpy v0.1.0 only supports FROM, RUN, and CMD instructions. Remove or comment out unsupported instructions like COPY, ADD, ENV, etc. These will be added in future releases.

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

**A**: By default, images are stored in `~/.derpy/images/`. You can change this with:

```bash
derpy config set images_path /your/custom/path
```

### Q: What Python version is required?

**A**: Python 3.8 or higher is required.

### Q: Can I use Derpy in CI/CD pipelines?

**A**: Yes! Derpy is designed to work in automated environments. Just ensure Python 3.8+ is available.

### Q: How do I report bugs or request features?

**A**: Please open an issue on the GitHub repository with details about the problem or feature request.

## Development Status

This is version 0.1.0 - an alpha release focusing on core functionality. See the project roadmap for planned features and improvements.

## Contributing

Contributions are welcome! Please see CONTRIBUTING.md for guidelines.

## License

MIT License - see LICENSE file for details.
