# Derpy Architecture

This directory contains architecture documentation for Derpy, an independent container tool that builds, manages, and distributes OCI-compliant container images.

## Overview

Derpy is designed as a modular Python application with clear separation of concerns. The architecture follows these principles:

- **Runtime Independence**: No dependency on Docker, Podman, or containerd
- **OCI Compliance**: Full adherence to OCI specifications for interoperability
- **Cross-Platform**: Consistent behavior across Windows, Linux, and macOS
- **Minimal Dependencies**: Uses Python standard library wherever possible
- **Extensibility**: Modular design allows easy addition of new features

## Core Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CLI Layer                            │
│  - Command parsing (click)                              │
│  - User interaction                                     │
│  - Configuration management                             │
└─────────────────────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ↓                ↓                ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│Build Engine  │  │Storage Mgr   │  │Registry      │
│- Parse       │  │- Local repo  │  │- Push/pull   │
│- Execute     │  │- OCI layout  │  │- Auth        │
│- Layer build │  │- Image mgmt  │  │- Manifest    │
└──────────────┘  └──────────────┘  └──────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         ↓
              ┌──────────────────┐
              │   OCI Models     │
              │ - Manifest       │
              │ - Config         │
              │ - Layers         │
              └──────────────────┘
```

## Module Structure

### CLI Layer (`derpy/cli/`)

Entry point for user interaction:

- `main.py`: Command definitions using click framework
- `banner.py`: ASCII banner display

**Commands:**

- `build`: Build images from Dockerfiles
- `ls`: List local images
- `push`: Push images to registries
- `config`: Manage configuration

### Core Utilities (`derpy/core/`)

Shared utilities and configuration:

- `config.py`: Configuration management (ConfigManager, Config models)
- `exceptions.py`: Custom exception hierarchy
- `logging.py`: Logging setup and utilities
- `platform.py`: Cross-platform path and directory utilities

### Build System (`derpy/build/`)

Image building functionality:

- `engine.py`: BuildEngine orchestrates the build process
- `layers.py`: LayerBuilder creates filesystem layers
- `pipeline.py`: InstructionPipeline executes build steps
- `base_image.py`: BaseImageManager handles base image retrieval
- `isolation.py`: IsolationExecutor provides chroot-based execution
- `diff.py`: LayerDiffManager captures filesystem changes
- `models.py`: Build-specific data models

### Dockerfile Parsing (`derpy/dockerfile/`)

Dockerfile syntax parsing and handling:

- `parser.py`: DockerfileParser and Instruction models
- `handlers.py`: Instruction handlers (FROM, RUN, CMD, etc.)

### OCI Specification (`derpy/oci/`)

OCI-compliant data models:

- `models.py`: Manifest, ImageConfig, Layer, Descriptor
- `layout.py`: OCI layout management for local storage

### Storage Management (`derpy/storage/`)

Local image repository:

- `manager.py`: ImageManager for local image storage and retrieval

### Registry Integration (`derpy/registry/`)

Remote registry interaction:

- `client.py`: RegistryClient for push/pull operations, authentication

## Key Features

### 1. Dockerfile Parsing

The parser converts Dockerfile syntax into structured instruction objects:

```python
parser = DockerfileParser()
instructions = parser.parse(dockerfile_content)
# Returns: List[Instruction]
```

Supported instructions:

- `FROM`: Base image specification
- `RUN`: Command execution
- `CMD`: Default container command

### 2. Build Engine

The build engine orchestrates the entire build process:

```python
engine = BuildEngine()
image = engine.build_image(context, tag)
```

**Build Flow:**

1. Parse Dockerfile
2. Create build context
3. Execute instructions sequentially
4. Create layers for each instruction
5. Generate OCI manifest and config
6. Store in local repository

### 3. Build Isolation (Linux Only)

On Linux, the build engine uses isolation for realistic builds:

**Components:**

- **BaseImageManager**: Downloads and extracts base images
- **IsolationExecutor**: Executes commands in chroot
- **LayerDiffManager**: Captures filesystem changes

**Flow:**

1. Pull base image from registry
2. Extract layers to temporary rootfs
3. Execute RUN commands in chroot
4. Capture filesystem diffs
5. Create layers from diffs
6. Combine base and new layers

See [build-isolation.md](./build-isolation.md) for detailed documentation.

### 4. Layer Building

Layers are created from filesystem changes:

```python
layer_builder = LayerBuilder()
layer = layer_builder.create_layer(files, instruction)
```

**Layer Creation:**

1. Create tar.gz archive of changed files
2. Calculate digest (SHA256 of compressed content)
3. Calculate diff_id (SHA256 of uncompressed content)
4. Generate layer metadata
5. Store in OCI layout

### 5. OCI Compliance

All images follow OCI specifications:

- **Image Manifest**: References config and layers
- **Image Config**: Container configuration and history
- **Layers**: Filesystem changesets as tar.gz archives
- **Descriptors**: Content-addressable references

### 6. Local Storage

Images are stored in OCI layout format:

```
~/.derpy/images/
├── blobs/
│   └── sha256/
│       ├── <manifest-digest>
│       ├── <config-digest>
│       └── <layer-digest>
└── index.json
```

### 7. Registry Integration

Push and pull images from OCI registries:

- Docker Hub (docker.io)
- GitHub Container Registry (ghcr.io)
- Any OCI-compliant registry

**Features:**

- Authentication support
- Manifest upload/download
- Blob upload/download
- Chunked uploads for large layers

## Data Flow

### Build Process

```
Dockerfile
    ↓
DockerfileParser
    ↓
List[Instruction]
    ↓
BuildEngine
    ↓
InstructionPipeline
    ↓
[For each instruction]
    ↓
InstructionHandler
    ↓
LayerBuilder
    ↓
Layer
    ↓
ImageManager (store)
    ↓
OCI Layout
```

### Push Process

```
Local Image
    ↓
ImageManager (load)
    ↓
Image (manifest + config + layers)
    ↓
RegistryClient
    ↓
[Upload config blob]
    ↓
[Upload layer blobs]
    ↓
[Upload manifest]
    ↓
Remote Registry
```

## Configuration

Configuration is stored in `~/.derpy/config.yaml`:

```yaml
images_path: ~/.derpy/images
registry:
  default: docker.io
  credentials:
    docker.io:
      username: user
      password: pass
build:
  enable_isolation: true
  base_image_cache_dir: ~/.derpy/cache/base-images
  chroot_timeout: 300
```

## Error Handling

Custom exception hierarchy:

```
DerpyError (base)
├── ConfigError
├── BuildError
│   ├── BaseImageError
│   ├── IsolationError
│   └── FilesystemDiffError
├── ParseError
├── StorageError
└── RegistryError
```

## Testing Strategy

### Unit Tests

Test individual components in isolation:

- Configuration management
- Dockerfile parsing
- Layer building
- OCI model serialization

### Integration Tests

Test component interactions:

- End-to-end build process
- Registry push/pull
- Build isolation (Linux only)

### Test Organization

```
tests/
├── test_config.py
├── test_dockerfile_parser.py
├── test_build_engine.py
├── test_build_isolation_integration.py
├── test_layers.py
├── test_oci_models.py
├── test_storage_manager.py
└── test_registry_client.py
```

## Platform Considerations

### Linux

Full feature support:

- Build isolation with chroot
- Base image extraction
- Filesystem diff capture

### macOS

Limited isolation support:

- Build isolation disabled
- Falls back to v0.1.0 behavior
- RUN commands execute on host

### Windows

Limited isolation support:

- Build isolation disabled
- Falls back to v0.1.0 behavior
- RUN commands execute on host

## Performance Considerations

### Build Performance

- **Layer caching**: Reuse unchanged layers (future)
- **Base image caching**: Store downloaded images locally
- **Parallel downloads**: Download layer blobs concurrently (future)

### Storage Performance

- **Content-addressable storage**: Deduplicate identical layers
- **Efficient tar operations**: Stream processing for large files
- **Lazy extraction**: Extract layers only when needed

## Security Considerations

### Build Isolation

- Chroot is not a security boundary
- Use for isolation, not security
- Do not run untrusted code

### Registry Authentication

- Credentials stored in config file
- Use environment variables for CI/CD
- Support for credential helpers (future)

### Image Verification

- Verify layer digests during download
- Validate manifest signatures (future)
- Check for known vulnerabilities (future)

## Future Enhancements

### Short Term

- Additional Dockerfile instructions (COPY, ADD, ENV, WORKDIR)
- Multi-stage builds
- Build cache for faster rebuilds
- Image export/import

### Medium Term

- Rootless builds with user namespaces
- BuildKit-style parallel execution
- Cross-architecture builds with QEMU
- Image signing and verification

### Long Term

- Container execution runtime
- Kubernetes integration
- Plugin system for extensibility
- Web UI for image management

## References

- [OCI Image Specification](https://github.com/opencontainers/image-spec)
- [OCI Distribution Specification](https://github.com/opencontainers/distribution-spec)
- [Dockerfile Reference](https://docs.docker.com/engine/reference/builder/)
- [Build Isolation Architecture](./build-isolation.md)

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for development guidelines and architecture principles.
