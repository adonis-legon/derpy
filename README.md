# Derpy - Independent Container Tool

Derpy is an independent container tool that does not depend on Docker, Podman, containerd, or any other container runtime. It's a Python CLI application that provides essential container functionality, building, managing, and distributing OCI-compliant container images from scratch.

**Note**: While Derpy is independent of container runtimes, it does use minimal Python dependencies (like PyYAML) for configuration management.

## Features

- **Dockerfile Support**: Parse and build from familiar Dockerfile syntax
- **OCI Compliance**: Generate fully compliant OCI container images
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
derpy config set images-path /custom/path/to/images
```

Configuration is stored in `~/.derpy/config.yaml`

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

See the `examples/` directory for more sample Dockerfiles.

## Troubleshooting

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
derpy config set images-path ~/custom/derpy/images
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

**A**: Version 0.1.0 focuses on building and distributing images. Container execution will be added in future releases. However, images built with Derpy are OCI-compliant and can be run with Docker, Podman, or other OCI-compatible runtimes.

### Q: Are Derpy images compatible with Docker?

**A**: Yes! Derpy generates OCI-compliant images that work with Docker, Podman, Kubernetes, and other OCI-compatible tools.

### Q: Where are images stored locally?

**A**: By default, images are stored in `~/.derpy/images/`. You can change this with:

```bash
derpy config set images-path /your/custom/path
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
