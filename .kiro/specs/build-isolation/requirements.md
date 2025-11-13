# Requirements Document: Build Isolation with Base Image Support

## Introduction

This feature adds proper container build isolation to derpy, enabling it to build real-world container images that depend on base image filesystems and distribution-specific package managers. The implementation will support Linux environments (native or VM) and enable derpy to execute RUN commands in an isolated filesystem environment using the base image's tools and dependencies.

## Glossary

- **Base Image**: The container image specified in the FROM instruction that provides the initial filesystem and tools
- **Rootfs**: Root filesystem - the complete directory tree that will become the container's filesystem
- **Layer**: A tar.gz archive containing filesystem changes from a single Dockerfile instruction
- **Chroot**: Linux system call that changes the apparent root directory for a process and its children
- **Registry**: Remote OCI-compliant image repository (e.g., Docker Hub, ghcr.io)
- **Image Reference**: String identifying an image (e.g., "nginx:alpine", "ubuntu:22.04")
- **Manifest**: JSON document describing image layers and configuration
- **Blob**: Content-addressable storage unit identified by SHA256 digest
- **Diff**: Filesystem changes between two states, captured as a layer
- **Build System**: The derpy build engine that processes Dockerfiles
- **Isolation Environment**: Chrooted filesystem where RUN commands execute

## Requirements

### Requirement 1: Base Image Retrieval

**User Story:** As a developer, I want derpy to automatically download base images from registries, so that I can build images that depend on existing base images like nginx, alpine, or ubuntu.

#### Acceptance Criteria

1. WHEN a Dockerfile contains a FROM instruction with an image reference, THE Build System SHALL resolve the image reference to a registry URL and tag
2. WHEN the base image is not available locally, THE Build System SHALL download the image manifest from the registry
3. WHEN the manifest is retrieved, THE Build System SHALL download all layer blobs referenced in the manifest
4. WHEN all layers are downloaded, THE Build System SHALL store them in the local OCI layout
5. IF the base image already exists locally, THEN THE Build System SHALL use the cached version without re-downloading

### Requirement 2: Base Image Filesystem Extraction

**User Story:** As a developer, I want derpy to extract base image layers into a usable filesystem, so that RUN commands can access the tools and files from the base image.

#### Acceptance Criteria

1. WHEN base image layers are available locally, THE Build System SHALL extract each layer tar.gz archive in order
2. WHEN extracting layers, THE Build System SHALL merge them into a single rootfs directory
3. WHEN merging layers, THE Build System SHALL apply later layers on top of earlier layers (overlay behavior)
4. WHEN a layer contains whiteout files, THE Build System SHALL remove the corresponding files from the rootfs
5. WHEN extraction is complete, THE Build System SHALL verify the rootfs contains expected files and directories

### Requirement 3: Isolated Command Execution

**User Story:** As a developer, I want RUN commands to execute inside the base image filesystem using chroot, so that commands can use tools and dependencies from the base image rather than the host system.

#### Acceptance Criteria

1. WHEN executing a RUN instruction, THE Build System SHALL use chroot to change the root directory to the extracted rootfs
2. WHEN the command executes, THE Build System SHALL run it with the base image's shell (e.g., /bin/sh)
3. WHEN the command requires network access, THE Build System SHALL allow network connectivity from the chrooted environment
4. IF the command exits with a non-zero status, THEN THE Build System SHALL fail the build with an error message
5. WHEN the command completes successfully, THE Build System SHALL capture stdout and stderr for logging

### Requirement 4: Filesystem Change Capture

**User Story:** As a developer, I want derpy to capture filesystem changes after each RUN command, so that each instruction creates a proper layer with only the modified files.

#### Acceptance Criteria

1. WHEN a RUN command is about to execute, THE Build System SHALL create a snapshot of the current rootfs state
2. WHEN the command completes, THE Build System SHALL compare the rootfs to the snapshot
3. WHEN differences are detected, THE Build System SHALL create a tar.gz archive containing only changed files
4. WHEN creating the layer archive, THE Build System SHALL preserve file permissions, ownership, and timestamps
5. WHEN no changes are detected, THE Build System SHALL create an empty layer marker

### Requirement 5: Layer Integration

**User Story:** As a developer, I want derpy to properly integrate new layers with base image layers, so that the final image contains all layers in the correct order.

#### Acceptance Criteria

1. WHEN building an image, THE Build System SHALL include all base image layers in the final manifest
2. WHEN new layers are created from RUN commands, THE Build System SHALL append them after base image layers
3. WHEN generating the image config, THE Build System SHALL include diff_ids for all layers (base + new)
4. WHEN calculating layer digests, THE Build System SHALL use SHA256 of the compressed layer content
5. WHEN storing the final image, THE Build System SHALL save all layers in the local OCI layout

### Requirement 6: Registry Client Enhancement

**User Story:** As a developer, I want derpy to fetch base images from any OCI-compliant registry, so that I can use images from Docker Hub, GitHub Container Registry, or private registries.

#### Acceptance Criteria

1. WHEN resolving an image reference without a registry, THE Build System SHALL default to Docker Hub (docker.io)
2. WHEN the image reference includes a registry hostname, THE Build System SHALL use that registry
3. WHEN authenticating to a registry, THE Build System SHALL use credentials from the derpy config
4. WHEN downloading manifests, THE Build System SHALL support both Docker v2 and OCI manifest formats
5. IF a registry requires authentication and no credentials are provided, THEN THE Build System SHALL fail with a clear error message

### Requirement 7: Build Context Isolation

**User Story:** As a developer, I want each build to use an isolated rootfs, so that concurrent builds don't interfere with each other.

#### Acceptance Criteria

1. WHEN starting a build, THE Build System SHALL create a unique temporary directory for the rootfs
2. WHEN the build completes successfully, THE Build System SHALL clean up the temporary rootfs
3. WHEN the build fails, THE Build System SHALL clean up the temporary rootfs
4. WHEN multiple builds run concurrently, THE Build System SHALL ensure each uses a separate rootfs
5. IF cleanup fails, THEN THE Build System SHALL log a warning but not fail the build

### Requirement 8: Linux Environment Validation

**User Story:** As a developer, I want derpy to validate it's running on Linux before attempting isolated builds, so that I get a clear error message on unsupported platforms.

#### Acceptance Criteria

1. WHEN derpy starts a build with a FROM instruction, THE Build System SHALL check if the OS is Linux
2. IF the OS is not Linux, THEN THE Build System SHALL fail with an error message explaining the limitation
3. WHEN running on Linux, THE Build System SHALL verify chroot capability is available
4. IF chroot is not available (e.g., insufficient permissions), THEN THE Build System SHALL fail with a clear error message
5. WHEN validation passes, THE Build System SHALL proceed with the isolated build

### Requirement 9: Error Handling and Recovery

**User Story:** As a developer, I want clear error messages when builds fail, so that I can understand and fix issues quickly.

#### Acceptance Criteria

1. WHEN a base image cannot be found in any registry, THE Build System SHALL fail with an error indicating the image reference
2. WHEN layer extraction fails, THE Build System SHALL fail with an error indicating which layer failed
3. WHEN a RUN command fails, THE Build System SHALL display the command, exit code, and stderr output
4. WHEN filesystem changes cannot be captured, THE Build System SHALL fail with an error describing the issue
5. WHEN any build step fails, THE Build System SHALL clean up temporary resources before exiting

### Requirement 10: Build Performance

**User Story:** As a developer, I want builds to complete in reasonable time, so that I can iterate quickly during development.

#### Acceptance Criteria

1. WHEN a base image is already cached locally, THE Build System SHALL skip downloading it
2. WHEN extracting layers, THE Build System SHALL use efficient tar extraction methods
3. WHEN capturing filesystem changes, THE Build System SHALL use efficient diff algorithms
4. WHEN multiple layers need extraction, THE Build System SHALL extract them sequentially without unnecessary delays
5. WHEN the build completes, THE Build System SHALL report total build time

## Out of Scope for This Feature

- Multi-architecture builds (arm64, amd64, etc.) - will use host architecture only
- BuildKit-style parallel execution and caching
- Dockerfile instructions beyond FROM, RUN, CMD (COPY, ADD, ENV, etc.)
- Windows or macOS native support (Linux-only for this feature)
- Rootless builds (requires root or appropriate capabilities for chroot)
- Build secrets and secure credential handling
- Multi-stage builds (FROM ... AS stage)
