# Derpy - Zero-Dependency Container Tool

Derpy is a Python CLI application that provides essential container functionality without relying on existing container runtimes like Docker, Podman, or containerd. It builds, manages, and distributes OCI-compliant container images using only Python and its standard library.

## Features

- **Dockerfile Support**: Parse and build from familiar Dockerfile syntax
- **OCI Compliance**: Generate fully compliant OCI container images
- **Local Repository**: Manage images in a local repository
- **Registry Integration**: Push images to OCI-compliant registries
- **Cross-Platform**: Works on Windows, Linux, and macOS
- **Zero Dependencies**: Minimal external dependencies for maximum compatibility

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

## Requirements

- Python 3.8 or higher
- No additional system dependencies required

## Development Status

This is version 0.1.0 - an alpha release focusing on core functionality. See the project roadmap for planned features and improvements.

## License

MIT License - see LICENSE file for details.
