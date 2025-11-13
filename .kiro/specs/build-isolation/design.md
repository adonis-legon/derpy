# Design Document: Build Isolation with Base Image Support

## Overview

This design implements proper container build isolation for derpy, enabling it to build real-world container images by:

1. Downloading base images from OCI registries
2. Extracting base image layers into a usable filesystem
3. Executing RUN commands in an isolated chroot environment
4. Capturing filesystem changes as new layers
5. Integrating base and new layers into the final image

The implementation targets Linux environments and uses chroot for isolation, making derpy capable of building images that depend on distribution-specific package managers and base image tools.

## Architecture

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

### Component Architecture

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

## Components and Interfaces

### 1. BaseImageManager

Handles downloading and extracting base images from registries.

```python
class BaseImageManager:
    """Manages base image retrieval and extraction."""

    def __init__(self, registry_client: RegistryClient, storage_manager: ImageManager):
        self.registry_client = registry_client
        self.storage = storage_manager
        self.cache_dir = Path("~/.derpy/cache/base-images").expanduser()

    def resolve_image_reference(self, image_ref: str) -> tuple[str, str, str]:
        """Parse image reference into registry, repository, tag.

        Examples:
            "ubuntu:22.04" → ("docker.io", "library/ubuntu", "22.04")
            "ghcr.io/org/app:v1" → ("ghcr.io", "org/app", "v1")
            "nginx" → ("docker.io", "library/nginx", "latest")

        Returns:
            (registry_url, repository, tag)
        """
        pass

    def pull_base_image(self, image_ref: str) -> Image:
        """Download base image from registry if not cached locally.

        Steps:
        1. Check if image exists in local storage
        2. If not, resolve registry and authenticate
        3. Download manifest
        4. Download config blob
        5. Download all layer blobs
        6. Store in local OCI layout
        7. Return Image object

        Returns:
            Image object with manifest, config, and layers
        """
        pass

    def extract_base_image(self, image: Image, target_dir: Path) -> Path:
        """Extract base image layers into a merged rootfs.

        Steps:
        1. Create target directory
        2. For each layer in order:
           a. Extract tar.gz to temp location
           b. Apply to target_dir (overlay behavior)
           c. Handle whiteout files (.wh.* markers)
        3. Return path to merged rootfs

        Returns:
            Path to extracted rootfs directory
        """
        pass

    def handle_whiteout_files(self, rootfs: Path, layer_dir: Path):
        """Process OCI whiteout files during layer extraction.

        Whiteout files (.wh.filename) indicate deleted files.
        Opaque whiteout (.wh..wh..opq) indicates directory replacement.
        """
        pass
```

### 2. IsolationExecutor

Executes commands in isolated chroot environment.

```python
class IsolationExecutor:
    """Executes commands in chrooted filesystem."""

    def __init__(self):
        self.logger = get_logger('isolation')

    def validate_linux_environment(self) -> None:
        """Verify running on Linux with chroot capability.

        Raises:
            BuildError: If not on Linux or chroot unavailable
        """
        pass

    def setup_chroot_environment(self, rootfs: Path) -> None:
        """Prepare rootfs for chroot execution.

        Steps:
        1. Mount /proc, /sys, /dev if needed
        2. Copy /etc/resolv.conf for DNS
        3. Verify shell exists (/bin/sh)
        """
        pass

    def execute_in_chroot(
        self,
        rootfs: Path,
        command: str,
        shell: str = "/bin/sh",
        timeout: int = 300
    ) -> ExecutionResult:
        """Execute command in chrooted environment.

        Uses os.chroot() to change root directory, then executes command.

        Args:
            rootfs: Path to root filesystem
            command: Command to execute
            shell: Shell to use (from base image)
            timeout: Command timeout in seconds

        Returns:
            ExecutionResult with stdout, stderr, exit_code
        """
        pass

    def cleanup_chroot_environment(self, rootfs: Path) -> None:
        """Clean up mounts and temporary files."""
        pass
```

### 3. LayerDiffManager

Captures filesystem changes and creates layers.

```python
class LayerDiffManager:
    """Manages filesystem diff capture and layer creation."""

    def __init__(self, layer_builder: LayerBuilder):
        self.layer_builder = layer_builder

    def create_snapshot(self, rootfs: Path) -> Snapshot:
        """Create filesystem snapshot before command execution.

        Captures:
        - File paths and metadata (mtime, size, permissions)
        - Directory structure
        - Symlinks

        Returns:
            Snapshot object for comparison
        """
        pass

    def capture_diff(
        self,
        rootfs: Path,
        before_snapshot: Snapshot,
        instruction: str
    ) -> Optional[Layer]:
        """Capture filesystem changes after command execution.

        Steps:
        1. Scan rootfs and compare to snapshot
        2. Identify added, modified, deleted files
        3. Create tar.gz with changes
        4. Generate layer with proper diff_id
        5. Add history entry

        Returns:
            Layer object or None if no changes
        """
        pass

    def create_layer_from_diff(
        self,
        changed_files: List[Path],
        rootfs: Path,
        instruction: str
    ) -> Layer:
        """Create OCI layer from list of changed files.

        Creates tar.gz archive with:
        - Changed files with full paths
        - Whiteout markers for deleted files
        - Proper permissions and ownership
        """
        pass
```

### 4. Enhanced BuildEngine

Modified to use new isolation components.

```python
class BuildEngine:
    """Enhanced build engine with isolation support."""

    def __init__(self):
        self.parser = DockerfileParser()
        self.base_image_mgr = BaseImageManager(...)
        self.isolation_exec = IsolationExecutor()
        self.layer_diff_mgr = LayerDiffManager(...)
        self.use_isolation = self._check_isolation_support()

    def _check_isolation_support(self) -> bool:
        """Check if isolation is supported on this platform."""
        try:
            self.isolation_exec.validate_linux_environment()
            return True
        except BuildError:
            return False

    def build_image(self, context: BuildContext, tag: str) -> Image:
        """Build image with isolation support.

        Flow:
        1. Parse Dockerfile
        2. If FROM instruction exists:
           a. Pull base image
           b. Extract to temp rootfs
           c. Use isolated execution
        3. Execute RUN instructions in chroot
        4. Capture diffs as layers
        5. Combine base + new layers
        6. Generate final image
        """
        pass

    def _execute_run_with_isolation(
        self,
        instruction: Instruction,
        run_inst: RunInstruction,
        rootfs: Path
    ) -> Optional[Layer]:
        """Execute RUN instruction in isolated environment.

        Steps:
        1. Create snapshot of rootfs
        2. Setup chroot environment
        3. Execute command in chroot
        4. Capture filesystem diff
        5. Create layer from diff
        6. Cleanup chroot

        Returns:
            Layer with captured changes
        """
        pass
```

## Data Models

### Snapshot

```python
@dataclass
class FileEntry:
    """Represents a file in the filesystem."""
    path: Path
    size: int
    mtime: float
    mode: int
    is_dir: bool
    is_symlink: bool
    link_target: Optional[str] = None

@dataclass
class Snapshot:
    """Filesystem snapshot for diff comparison."""
    timestamp: datetime
    files: Dict[str, FileEntry]  # path → FileEntry

    def compare(self, other: "Snapshot") -> FilesystemDiff:
        """Compare two snapshots to find changes."""
        pass

@dataclass
class FilesystemDiff:
    """Represents changes between two snapshots."""
    added: List[Path]
    modified: List[Path]
    deleted: List[Path]

    def is_empty(self) -> bool:
        return not (self.added or self.modified or self.deleted)
```

### ExecutionResult

```python
@dataclass
class ExecutionResult:
    """Result of command execution in chroot."""
    exit_code: int
    stdout: str
    stderr: str
    duration: float

    def is_success(self) -> bool:
        return self.exit_code == 0
```

### ImageReference

```python
@dataclass
class ImageReference:
    """Parsed container image reference."""
    registry: str  # e.g., "docker.io"
    repository: str  # e.g., "library/ubuntu"
    tag: str  # e.g., "22.04"
    digest: Optional[str] = None  # e.g., "sha256:abc..."

    @classmethod
    def parse(cls, ref: str) -> "ImageReference":
        """Parse image reference string."""
        pass

    def to_string(self) -> str:
        """Convert back to string format."""
        pass
```

## Error Handling

### New Exception Types

```python
class BaseImageError(BuildError):
    """Base image retrieval or extraction failed."""
    pass

class IsolationError(BuildError):
    """Chroot isolation setup or execution failed."""
    pass

class FilesystemDiffError(BuildError):
    """Filesystem diff capture failed."""
    pass

class PlatformNotSupportedError(BuildError):
    """Operation not supported on current platform."""
    pass
```

### Error Scenarios

1. **Base image not found**: Clear message with registry and image ref
2. **Network failure**: Retry logic with exponential backoff
3. **Chroot permission denied**: Suggest running with sudo or capabilities
4. **Layer extraction failure**: Clean up partial extraction
5. **Command execution timeout**: Kill process and clean up

## Testing Strategy

### Unit Tests

```python
# test_base_image_manager.py
def test_resolve_image_reference():
    """Test parsing various image reference formats."""
    pass

def test_pull_base_image_cached():
    """Test using cached base image."""
    pass

def test_extract_base_image_with_whiteouts():
    """Test whiteout file handling."""
    pass

# test_isolation_executor.py
def test_validate_linux_environment():
    """Test platform validation."""
    pass

def test_execute_in_chroot():
    """Test command execution in chroot."""
    pass

# test_layer_diff_manager.py
def test_create_snapshot():
    """Test filesystem snapshot creation."""
    pass

def test_capture_diff():
    """Test diff capture between snapshots."""
    pass
```

### Integration Tests

```python
# test_build_with_isolation.py
def test_build_ubuntu_with_apt():
    """Test building Ubuntu image with apt-get."""
    dockerfile = """
    FROM ubuntu:22.04
    RUN apt-get update && apt-get install -y curl
    CMD ["curl", "--version"]
    """
    pass

def test_build_alpine_with_apk():
    """Test building Alpine image with apk."""
    dockerfile = """
    FROM alpine:latest
    RUN apk add --no-cache nginx
    CMD ["nginx", "-v"]
    """
    pass

def test_build_with_multiple_run_commands():
    """Test multiple RUN instructions creating separate layers."""
    pass
```

### Manual Testing

1. Build simple Alpine image with package installation
2. Build Ubuntu image with apt-get
3. Build RHEL/CentOS image with dnf/yum
4. Verify layer count matches RUN instructions
5. Verify final image works with Docker/Podman

## Implementation Plan Integration

This design integrates with the existing derpy architecture:

### Modified Components

1. **BuildEngine** (`derpy/build/engine.py`)

   - Add isolation detection
   - Add base image handling
   - Modify `_execute_run_instruction_impl` to use chroot

2. **RegistryClient** (`derpy/registry/client.py`)
   - Add `pull_image()` method
   - Add `download_manifest()` method
   - Add `download_blob()` method

### New Components

1. **BaseImageManager** (`derpy/build/base_image.py`)
2. **IsolationExecutor** (`derpy/build/isolation.py`)
3. **LayerDiffManager** (`derpy/build/diff.py`)
4. **Snapshot** (`derpy/build/snapshot.py`)

### Configuration

Add to `Config`:

```python
@dataclass
class BuildSettings:
    # ... existing fields ...
    enable_isolation: bool = True
    base_image_cache_dir: Path = Path("~/.derpy/cache/base-images")
    chroot_timeout: int = 300
```

## Performance Considerations

1. **Base Image Caching**: Store downloaded images in local OCI layout
2. **Layer Reuse**: Don't re-download layers that exist locally
3. **Efficient Diff**: Use file metadata comparison before content comparison
4. **Parallel Downloads**: Download layer blobs in parallel (future)
5. **Incremental Extraction**: Extract layers incrementally during download

## Security Considerations

1. **Chroot Limitations**: Chroot is not a security boundary; use for isolation only
2. **Network Access**: Commands in chroot have network access
3. **Host Filesystem**: Ensure rootfs is properly isolated
4. **Cleanup**: Always clean up temp directories, even on failure
5. **Registry Authentication**: Securely handle registry credentials

## Future Enhancements

1. **Rootless Builds**: Use user namespaces for rootless chroot
2. **Build Cache**: Cache layers by instruction hash
3. **Multi-stage Builds**: Support FROM ... AS stage
4. **Cross-architecture**: Use QEMU for building different architectures
5. **BuildKit Features**: Parallel execution, mount caching
