# Derpy Example Dockerfiles

This directory contains example Dockerfiles demonstrating various use cases with Derpy.

## Build Isolation

On Linux systems, Derpy automatically enables build isolation, which allows you to build real-world images that depend on base image filesystems and distribution-specific package managers.

**Important**: Build isolation requires root privileges. Use `sudo` when building examples that depend on base images:

```bash
# Examples requiring sudo (base image filesystem access)
sudo derpy build examples/nginx-web -f examples/nginx-web/Dockerfile -t nginx-web:latest
sudo derpy build examples/ubuntu-curl -f examples/ubuntu-curl/Dockerfile -t ubuntu-curl:latest
sudo derpy build examples/alpine-python -f examples/alpine-python/Dockerfile -t alpine-python:latest

# Simple examples that work without sudo
derpy build examples/minimal -f examples/minimal/Dockerfile -t minimal:latest
```

On macOS and Windows, build isolation is disabled and examples may have limited functionality. Consider using a Linux VM or WSL2 for full feature support.

## Available Examples

### 1. Minimal Example (`minimal/`)

The simplest possible Dockerfile using Alpine Linux. Perfect for testing and learning. Works without sudo.

**Build**: `derpy build examples/minimal -f examples/minimal/Dockerfile -t minimal:latest`

### 2. Python Flask Application (`python-app/`)

A Python web application using Flask framework. Requires sudo for base image access.

**Build**: `sudo derpy build examples/python-app -f examples/python-app/Dockerfile -t flask-app:latest`

### 3. Nginx Web Server (`nginx-web/`)

A lightweight web server with custom HTML content. Requires sudo for base image filesystem access.

**Build**: `sudo derpy build examples/nginx-web -f examples/nginx-web/Dockerfile -t nginx-hello:latest`

### 4. Ubuntu Development Tools (`ubuntu-tools/`)

Ubuntu-based image with common development tools installed. Requires sudo for apt-get.

**Build**: `sudo derpy build examples/ubuntu-tools -f examples/ubuntu-tools/Dockerfile -t ubuntu-dev:latest`

### 5. Ubuntu with curl (`ubuntu-curl/`) - Linux Only

Demonstrates real-world package installation with apt-get. Requires build isolation (Linux with sudo).

**Build**: `sudo derpy build examples/ubuntu-curl -f examples/ubuntu-curl/Dockerfile -t ubuntu-curl:latest`

### 6. Alpine with Python (`alpine-python/`) - Linux Only

Demonstrates lightweight Alpine image with Python installation using apk. Requires build isolation (Linux with sudo).

**Build**: `sudo derpy build examples/alpine-python -f examples/alpine-python/Dockerfile -t alpine-python:latest`

## General Usage Pattern

All examples follow this pattern:

```bash
# Navigate to example directory
cd examples/[example-name]

# Build the image
derpy build . -f Dockerfile -t [image-name]:[tag]

# List your images
derpy ls

# Push to registry (optional)
derpy push [image-name]:[tag]
```

## Supported Instructions

These examples only use instructions currently supported by Derpy:

- `FROM` - Specify base image (with automatic download and caching)
- `RUN` - Execute commands during build (in isolated chroot on Linux)
- `CMD` - Set default command

## Real-World Image Building (Linux Only)

With build isolation enabled on Linux, you can build images that use distribution-specific package managers:

### Ubuntu with apt-get

```dockerfile
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y curl wget git
RUN curl --version
CMD ["/bin/bash"]
```

### Alpine with apk

```dockerfile
FROM alpine:latest
RUN apk add --no-cache python3 py3-pip nodejs npm
RUN python3 --version && node --version
CMD ["/bin/sh"]
```

### Debian with apt

```dockerfile
FROM debian:bullseye
RUN apt-get update && apt-get install -y nginx
RUN nginx -v
CMD ["nginx", "-g", "daemon off;"]
```

These examples work because Derpy:

1. Downloads the base image from the registry
2. Extracts the base image layers into a temporary filesystem
3. Executes RUN commands in a chrooted environment with access to the base image's tools
4. Captures filesystem changes as new layers
5. Combines base and new layers into the final image

## Tips

1. **Start Simple**: Begin with the minimal example to verify your setup
2. **Build Context**: The build context is the directory containing files needed for the build
3. **Layer Caching**: Each RUN instruction creates a new layer
4. **Image Size**: Chain commands with `&&` and clean up in the same RUN instruction to reduce size

## Troubleshooting

If builds fail:

1. Check that the base image is accessible
2. Verify commands exist in the base image
3. Review error messages for specific issues
4. Consult the main README.md troubleshooting section

## Contributing Examples

Have a useful example? Contributions are welcome! Please ensure:

- Only use supported instructions (FROM, RUN, CMD)
- Include a README.md explaining the example
- Keep it simple and focused on one concept
- Test the build before submitting
