# Alpine with Python Example

This example demonstrates building a lightweight Alpine-based image with Python installation using apk.

## Requirements

- **Linux environment**: This example requires build isolation, which is only available on Linux
- Root privileges or CAP_SYS_CHROOT capability

## What This Example Does

1. Starts with Alpine Linux latest base image
2. Installs Python 3 and pip using apk (Alpine's package manager)
3. Verifies Python is installed
4. Sets python3 as the default command

## Building

```bash
# From the derpy root directory
derpy build examples/alpine-python -f examples/alpine-python/Dockerfile -t alpine-python:latest

# Or from this directory
cd examples/alpine-python
derpy build . -f Dockerfile -t alpine-python:latest
```

## How It Works

With build isolation enabled (Linux only), Derpy:

1. Downloads the alpine:latest base image from Docker Hub
2. Extracts the base image layers into a temporary filesystem
3. Executes the RUN commands in a chrooted environment
4. The apk commands run inside the Alpine filesystem, not on your host
5. Captures filesystem changes (installed packages) as new layers
6. Combines base and new layers into the final image

## Why Alpine?

Alpine Linux is popular for container images because:

- **Small size**: Base image is only ~5MB
- **Fast downloads**: Minimal network transfer
- **Security**: Minimal attack surface
- **apk package manager**: Simple and efficient

## Running the Built Image

The image built by Derpy is OCI-compliant and can be run with Docker or Podman:

```bash
# Export the image (future feature)
# For now, push to a registry and pull with Docker/Podman

# Or inspect locally
derpy ls
```

## Platform Notes

- **Linux**: Full support with build isolation
- **macOS/Windows**: Build isolation is disabled; this example will not work as expected

For macOS/Windows users, consider:

- Using a Linux VM (VirtualBox, VMware, Parallels)
- Using WSL2 on Windows
- Using Docker Desktop with Linux containers
