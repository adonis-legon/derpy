# Build Isolation Architecture

## Overview

Build isolation is a feature that enables Derpy to build real-world container images by executing RUN commands in an isolated filesystem environment using the base image's tools and dependencies. This feature is available on Linux systems and uses chroot for isolation.

## Architecture Components

### High-Level Flow

```
Dockerfile with FROM instruction
         ↓
1. Parse FROM instruction → image reference (e.g., "ubuntu:22.04")
         ↓
2. Resolve & Download base image from registry
         ↓
3. Extract base layers → merged rootfs in temp directory
         ↓
4. For each RUN instruction:
   a. Snapshot current rootfs state
   b. Execute command in chroot(rootfs)
   c. Capture filesystem diff
   d. Create new layer from diff
         ↓
5. Combine base layers + new layers → final image
         ↓
6. Store in local OCI layout
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    BuildEngine                          │
│  - Orchestrates build process                           │
│  - Delegates to specialized components                  │
└─────────────────────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ↓                ↓                ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│BaseImageMgr  │  │IsolationExec │  │LayerDiffMgr  │
│- Pull images │  │- Chroot exec │  │- Capture diffs│
│- Extract     │  │- Mount setup │  │- Create layers│
└──────────────┘  └──────────────┘  └──────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         ↓
              ┌──────────────────┐
              │  RegistryClient  │
              │  OCILayoutMgr    │
              └──────────────────┘
```

## Core Components

### 1. BaseImageManager (`derpy/build/base_image.py`)

Handles downloading and extracting base images from OCI registries.

**Key Responsibilities:**

- Parse image references (e.g., "ubuntu:22.04" → registry, repository, tag)
- Download base images from registries (manifest, config, layers)
- Cache downloaded images locally
- Extract base image layers into a merged rootfs
- Handle OCI whiteout files during layer extraction

**Key Methods:**

- `resolve_image_reference(image_ref: str)`: Parse image reference into components
- `pull_base_image(image_ref: str)`: Download base image if not cached
- `extract_base_image(image: Image, target_dir: Path)`: Extract layers to rootfs
- `handle_whiteout_files(rootfs: Path, layer_dir: Path)`: Process deletion markers

### 2. IsolationExecutor (`derpy/build/isolation.py`)

Executes commands in isolated chroot environments.

**Key Responsibilities:**

- Validate Linux environment and chroot capability
- Set up chroot environment (mount /proc, /sys, /dev, copy resolv.conf)
- Execute commands in chrooted filesystem
- Handle command timeouts and errors
- Clean up chroot environment after execution

**Key Methods:**

- `validate_linux_environment()`: Check if running on Linux with chroot capability
- `setup_chroot_environment(rootfs: Path)`: Prepare rootfs for chroot
- `execute_in_chroot(rootfs: Path, command: str)`: Run command in chroot
- `cleanup_chroot_environment(rootfs: Path)`: Clean up mounts and temp files

### 3. LayerDiffManager (`derpy/build/diff.py`)

Captures filesystem changes and creates OCI layers.

**Key Responsibilities:**

- Create filesystem snapshots before command execution
- Compare snapshots to identify changes (added, modified, deleted files)
- Create tar.gz archives with changed files
- Generate proper OCI layer metadata (digest, diff_id)
- Handle empty diffs (no-op commands)

**Key Methods:**

- `create_snapshot(rootfs: Path)`: Capture current filesystem state
- `capture_diff(rootfs: Path, before_snapshot: Snapshot)`: Identify changes
- `create_layer_from_diff(changed_files: List[Path], rootfs: Path)`: Create OCI layer

### 4. Enhanced BuildEngine (`derpy/build/engine.py`)

Modified to support build isolation.

**Key Changes:**

- Detect isolation support at initialization
- Handle FROM instructions by pulling and extracting base images
- Execute RUN instructions in chroot when isolation is enabled
- Capture filesystem diffs after each RUN instruction
- Combine base image layers with new layers in final image
- Fall back to v0.1.0 behavior on unsupported platforms

## Data Models

### Snapshot

Represents a filesystem state at a point in time.

```python
@dataclass
class FileEntry:
    path: Path
    size: int
    mtime: float
    mode: int
    is_dir: bool
    is_symlink: bool
    link_target: Optional[str] = None

@dataclass
class Snapshot:
    timestamp: datetime
    files: Dict[str, FileEntry]
```

### ExecutionResult

Represents the result of command execution in chroot.

```python
@dataclass
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str
    duration: float
```

### ImageReference

Represents a parsed container image reference.

```python
@dataclass
class ImageReference:
    registry: str      # e.g., "docker.io"
    repository: str    # e.g., "library/ubuntu"
    tag: str          # e.g., "22.04"
    digest: Optional[str] = None
```

## Platform Support

### Linux

Full support for build isolation:

- Chroot-based command execution
- Base image filesystem extraction
- Filesystem change capture
- Proper layer creation

**Requirements:**

- Linux kernel with chroot support
- Root privileges or CAP_SYS_CHROOT capability
- Sufficient disk space for base image extraction

### macOS and Windows

Build isolation is automatically disabled on these platforms. Derpy falls back to v0.1.0 behavior:

- RUN commands execute on the host system
- No base image extraction
- Limited support for distribution-specific package managers

**Workarounds:**

- Use a Linux VM (VirtualBox, VMware, Parallels)
- Use Docker Desktop with Linux containers
- Use WSL2 on Windows
- Use a cloud Linux instance

## Configuration

Build isolation can be configured via `~/.derpy/config.yaml`:

```yaml
build:
  enable_isolation: true
  base_image_cache_dir: ~/.derpy/cache/base-images
  chroot_timeout: 300
```

**Configuration Options:**

- `enable_isolation`: Enable/disable build isolation (default: true on Linux, false elsewhere)
- `base_image_cache_dir`: Directory for caching downloaded base images
- `chroot_timeout`: Maximum time in seconds for RUN commands in chroot

## Error Handling

### Exception Types

- `BaseImageError`: Base image retrieval or extraction failed
- `IsolationError`: Chroot isolation setup or execution failed
- `FilesystemDiffError`: Filesystem diff capture failed
- `PlatformNotSupportedError`: Operation not supported on current platform

### Error Scenarios

1. **Base image not found**: Clear message with registry and image reference
2. **Network failure**: Retry logic with exponential backoff
3. **Chroot permission denied**: Suggest running with sudo or granting capabilities
4. **Layer extraction failure**: Clean up partial extraction
5. **Command execution timeout**: Kill process and clean up

## Performance Considerations

### Base Image Caching

Downloaded base images are cached in `~/.derpy/cache/base-images/` to avoid re-downloading:

- Images are stored in OCI layout format
- Cache is shared across builds
- Cache can be cleared manually if needed

### Layer Extraction

Base image layers are extracted to temporary directories:

- Extraction happens once per build
- Layers are merged in order (overlay behavior)
- Temporary directories are cleaned up after build

### Filesystem Diff Capture

Filesystem changes are captured efficiently:

- File metadata comparison before content comparison
- Only changed files are included in new layers
- Empty diffs are detected and skipped

## Security Considerations

### Chroot Limitations

Chroot is not a security boundary:

- Processes can escape chroot with sufficient privileges
- Use chroot for isolation, not security
- Do not run untrusted code in chroot

### Network Access

Commands in chroot have network access:

- DNS resolution is available (via /etc/resolv.conf)
- Network connectivity is not restricted
- Be cautious with untrusted Dockerfiles

### Cleanup

Temporary directories are always cleaned up:

- Cleanup happens on successful builds
- Cleanup happens on build failures
- Cleanup happens on interruption (SIGINT, SIGTERM)

## Future Enhancements

### Rootless Builds

Use user namespaces for rootless chroot:

- No root privileges required
- Better security isolation
- Compatible with rootless container runtimes

### Build Cache

Cache layers by instruction hash:

- Skip rebuilding unchanged layers
- Faster incremental builds
- Reduced disk I/O

### Multi-stage Builds

Support FROM ... AS stage syntax:

- Build multiple images in one Dockerfile
- Copy artifacts between stages
- Smaller final images

### Cross-architecture Builds

Use QEMU for building different architectures:

- Build arm64 images on amd64 hosts
- Build amd64 images on arm64 hosts
- Support multi-architecture manifests

## References

- [OCI Image Specification](https://github.com/opencontainers/image-spec)
- [OCI Distribution Specification](https://github.com/opencontainers/distribution-spec)
- [Dockerfile Reference](https://docs.docker.com/engine/reference/builder/)
- [Linux chroot(2) man page](https://man7.org/linux/man-pages/man2/chroot.2.html)
