# Ubuntu with curl Example

This example demonstrates building a real-world Ubuntu-based image with package installation using apt-get.

## Requirements

- **Linux environment**: This example requires build isolation, which is only available on Linux
- Root privileges or CAP_SYS_CHROOT capability

## What This Example Does

1. Starts with Ubuntu 22.04 base image
2. Updates the apt package list
3. Installs curl using apt-get
4. Verifies curl is installed
5. Sets bash as the default command

## Building

```bash
# From the derpy root directory
derpy build examples/ubuntu-curl -f examples/ubuntu-curl/Dockerfile -t ubuntu-curl:latest

# Or from this directory
cd examples/ubuntu-curl
derpy build . -f Dockerfile -t ubuntu-curl:latest
```

## How It Works

With build isolation enabled (Linux only), Derpy:

1. Downloads the ubuntu:22.04 base image from Docker Hub
2. Extracts the base image layers into a temporary filesystem
3. Executes the RUN commands in a chrooted environment
4. The apt-get commands run inside the Ubuntu filesystem, not on your host
5. Captures filesystem changes (installed packages) as new layers
6. Combines base and new layers into the final image

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
