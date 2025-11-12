# Design Document

## Overview

Derpy is a zero-dependency container tool implemented as a Python CLI application that provides essential container functionality without relying on existing container runtimes. The architecture follows a modular design with clear separation of concerns between CLI interface, core container operations, OCI compliance, and registry interactions.

The tool leverages Python's cross-platform capabilities and standard library to minimize external dependencies while maintaining full OCI compliance for interoperability with existing container ecosystems.

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI Layer     │    │  Core Engine    │    │  Storage Layer  │
│                 │    │                 │    │                 │
│ • Click Framework│───▶│ • Build Engine  │───▶│ • Local Repo    │
│ • Command Parser│    │ • Image Manager │    │ • OCI Layout    │
│ • Help System   │    │ • Registry Client│    │ • Config Store  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Dockerfile     │    │   OCI Spec      │    │  File System    │
│  Parser         │    │  Compliance     │    │  Operations     │
│                 │    │                 │    │                 │
│ • FROM Handler  │    │ • Manifest Gen  │    │ • Tar/Gzip     │
│ • RUN Executor  │    │ • Config Gen    │    │ • Path Utils    │
│ • CMD Parser    │    │ • Layer Builder │    │ • Permissions   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Component Interaction Flow

1. **CLI Layer** receives user commands and delegates to appropriate core components
2. **Core Engine** orchestrates build processes, image management, and registry operations
3. **Storage Layer** handles local repository management and OCI-compliant file structures
4. **Dockerfile Parser** processes Dockerfile instructions into executable operations
5. **OCI Compliance** ensures all generated artifacts meet OCI specifications

## Components and Interfaces

### CLI Layer Components

#### Command Interface

```python
class DerpyCommand:
    def build(context_path: str, dockerfile_path: str, tag: str) -> BuildResult
    def list_images() -> List[ImageInfo]
    def push(image_tag: str, registry_url: str) -> PushResult
    def version() -> VersionInfo
    def config(action: str, key: str, value: str) -> ConfigResult
```

#### Configuration Manager

```python
class ConfigManager:
    def load_config() -> Config
    def save_config(config: Config) -> None
    def get_images_path() -> Path
    def set_images_path(path: Path) -> None
```

### Core Engine Components

#### Build Engine

```python
class BuildEngine:
    def build_image(dockerfile: Dockerfile, context: BuildContext, tag: str) -> Image
    def create_layers(instructions: List[Instruction]) -> List[Layer]
    def generate_manifest(layers: List[Layer], config: ImageConfig) -> Manifest
```

#### Image Manager

```python
class ImageManager:
    def store_image(image: Image, tag: str) -> None
    def list_local_images() -> List[ImageInfo]
    def get_image(tag: str) -> Optional[Image]
    def delete_image(tag: str) -> bool
```

#### Registry Client

```python
class RegistryClient:
    def authenticate(registry_url: str, credentials: Credentials) -> AuthToken
    def push_image(image: Image, tag: str, registry_url: str) -> PushResult
    def check_registry_compatibility(registry_url: str) -> bool
```

### Storage Layer Components

#### OCI Layout Manager

```python
class OCILayoutManager:
    def create_layout(path: Path) -> OCILayout
    def store_blob(content: bytes, media_type: str) -> Descriptor
    def store_manifest(manifest: Manifest) -> Descriptor
    def create_index(manifests: List[Descriptor]) -> Index
```

#### Local Repository

```python
class LocalRepository:
    def initialize_repo(path: Path) -> None
    def store_image_metadata(tag: str, metadata: ImageMetadata) -> None
    def get_image_list() -> List[ImageInfo]
    def cleanup_orphaned_blobs() -> None
```

### Dockerfile Processing Components

#### Dockerfile Parser

```python
class DockerfileParser:
    def parse(dockerfile_path: Path) -> Dockerfile
    def validate_syntax(content: str) -> List[ValidationError]
    def extract_instructions(content: str) -> List[Instruction]
```

#### Instruction Handlers

```python
class FromHandler:
    def process(instruction: FromInstruction, context: BuildContext) -> BaseLayer

class RunHandler:
    def process(instruction: RunInstruction, context: BuildContext) -> Layer

class CmdHandler:
    def process(instruction: CmdInstruction, context: BuildContext) -> ImageConfig
```

## Data Models

### Core Data Structures

#### Image Representation

```python
@dataclass
class Image:
    manifest: Manifest
    config: ImageConfig
    layers: List[Layer]
    metadata: ImageMetadata

@dataclass
class Layer:
    digest: str
    size: int
    media_type: str
    content_path: Path
    diff_id: str
```

#### OCI Compliance Structures

```python
@dataclass
class Manifest:
    schema_version: int
    media_type: str
    config: Descriptor
    layers: List[Descriptor]

@dataclass
class ImageConfig:
    architecture: str
    os: str
    config: ContainerConfig
    rootfs: RootFS
    history: List[HistoryEntry]

@dataclass
class Descriptor:
    media_type: str
    size: int
    digest: str
    urls: Optional[List[str]] = None
    annotations: Optional[Dict[str, str]] = None
```

#### Configuration Models

```python
@dataclass
class Config:
    images_path: Path
    registry_configs: Dict[str, RegistryConfig]
    build_settings: BuildSettings

@dataclass
class BuildContext:
    context_path: Path
    dockerfile_path: Path
    build_args: Dict[str, str]
    platform: Platform
```

## Error Handling

### Error Categories

#### Build Errors

- **Dockerfile Syntax Errors**: Invalid instruction format, unsupported commands
- **Context Errors**: Missing files, permission issues, invalid paths
- **Layer Creation Errors**: Command execution failures, filesystem issues
- **OCI Compliance Errors**: Invalid manifest generation, missing required fields

#### Runtime Errors

- **Configuration Errors**: Invalid config file, missing directories
- **Storage Errors**: Disk space issues, permission problems, corrupted data
- **Network Errors**: Registry connectivity, authentication failures
- **Platform Errors**: OS-specific operation failures, missing dependencies

### Error Handling Strategy

```python
class DerpyError(Exception):
    """Base exception for all derpy errors"""
    pass

class BuildError(DerpyError):
    """Errors during image building process"""
    pass

class RegistryError(DerpyError):
    """Errors during registry operations"""
    pass

class ConfigError(DerpyError):
    """Configuration-related errors"""
    pass
```

### Error Recovery Mechanisms

1. **Graceful Degradation**: Continue with available functionality when non-critical components fail
2. **Retry Logic**: Automatic retry for transient network and filesystem errors
3. **Cleanup on Failure**: Remove partial artifacts when builds fail
4. **User-Friendly Messages**: Clear error descriptions with suggested remediation steps

## Testing Strategy

### Unit Testing Approach

#### Component-Level Testing

- **CLI Commands**: Test argument parsing, help generation, command delegation
- **Build Engine**: Test layer creation, manifest generation, OCI compliance
- **Dockerfile Parser**: Test instruction parsing, validation, error handling
- **Storage Operations**: Test file operations, OCI layout creation, repository management

#### Mock Strategy

- **Filesystem Operations**: Mock file I/O for predictable testing
- **Network Operations**: Mock registry interactions for offline testing
- **System Commands**: Mock subprocess calls for RUN instruction testing
- **Platform-Specific Code**: Mock OS-specific operations for cross-platform testing

### Integration Testing Approach

#### End-to-End Workflows

- **Complete Build Process**: Dockerfile → OCI Image → Local Storage
- **Registry Integration**: Local Image → Registry Push → Verification
- **Configuration Management**: Config Changes → Behavior Verification
- **Cross-Platform Compatibility**: Same operations across OS platforms

#### Test Data Management

- **Sample Dockerfiles**: Various complexity levels and instruction combinations
- **Test Images**: Minimal base images for testing FROM instructions
- **Mock Registry**: Local registry simulation for push/pull testing
- **Test Contexts**: Sample application contexts with different structures

### Performance Testing

#### Build Performance

- **Layer Caching**: Verify efficient layer reuse and caching mechanisms
- **Large Context Handling**: Test performance with large build contexts
- **Concurrent Builds**: Ensure thread safety and resource management
- **Memory Usage**: Monitor memory consumption during build processes

#### Storage Performance

- **Repository Operations**: Test performance of image listing and metadata operations
- **Blob Storage**: Verify efficient storage and retrieval of large blobs
- **Cleanup Operations**: Test performance of garbage collection and cleanup

### Security Testing

#### Input Validation

- **Dockerfile Injection**: Test resistance to malicious Dockerfile content
- **Path Traversal**: Verify protection against directory traversal attacks
- **Command Injection**: Test RUN instruction safety and sandboxing
- **Registry Security**: Test authentication and secure communication

#### Data Protection

- **Configuration Security**: Ensure sensitive config data is properly protected
- **Temporary File Handling**: Verify secure creation and cleanup of temp files
- **Permission Management**: Test proper file and directory permissions
