# Implementation Plan: Build Isolation with Base Image Support

## Task List

- [ ] 1. Create core data models and utilities

  - Create ImageReference model for parsing image references (e.g., "ubuntu:22.04")
  - Create Snapshot and FilesystemDiff models for tracking filesystem changes
  - Create ExecutionResult model for command execution results
  - Add new exception types: BaseImageError, IsolationError, FilesystemDiffError, PlatformNotSupportedError
  - _Requirements: 1.1, 2.1, 3.1, 8.1_

- [ ] 2. Implement BaseImageManager for image retrieval

  - [ ] 2.1 Implement image reference parsing and resolution

    - Write `resolve_image_reference()` to parse "ubuntu:22.04" → ("docker.io", "library/ubuntu", "22.04")
    - Handle default registry (docker.io) and default tag (latest)
    - Validate image reference format
    - _Requirements: 1.1, 6.1, 6.2_

  - [ ] 2.2 Extend RegistryClient with pull capabilities

    - Add `download_manifest()` method to fetch image manifest from registry
    - Add `download_blob()` method to fetch individual blobs (config, layers)
    - Add `pull_image()` method to download complete image (manifest + config + all layers)
    - Support both Docker v2 and OCI manifest formats
    - _Requirements: 1.2, 1.3, 6.3, 6.4_

  - [ ] 2.3 Implement base image caching

    - Check if image exists in local storage before downloading
    - Store downloaded images in local OCI layout
    - Return cached Image object if available
    - _Requirements: 1.4, 1.5, 10.1_

  - [ ] 2.4 Implement layer extraction logic
    - Extract tar.gz layers to temporary directory
    - Merge layers in order (overlay behavior)
    - Handle OCI whiteout files (.wh.\* markers for deleted files)
    - Handle opaque whiteout (.wh..wh..opq for directory replacement)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ] 3. Implement IsolationExecutor for chroot execution

  - [ ] 3.1 Implement Linux environment validation

    - Check if running on Linux (platform.system() == "Linux")
    - Verify chroot capability (check if running as root or with CAP_SYS_CHROOT)
    - Provide clear error messages for unsupported platforms
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [ ] 3.2 Implement chroot environment setup

    - Mount /proc, /sys, /dev into rootfs if needed
    - Copy /etc/resolv.conf for DNS resolution
    - Verify shell exists in rootfs (/bin/sh or specified shell)
    - _Requirements: 3.2, 3.3_

  - [ ] 3.3 Implement command execution in chroot

    - Use os.chroot() to change root directory
    - Execute command with specified shell
    - Capture stdout and stderr
    - Handle command timeout
    - Return ExecutionResult with exit code and output
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [ ] 3.4 Implement chroot cleanup
    - Unmount /proc, /sys, /dev
    - Remove temporary files
    - Handle cleanup errors gracefully
    - _Requirements: 7.2, 7.3, 7.5_

- [ ] 4. Implement LayerDiffManager for filesystem change capture

  - [ ] 4.1 Implement filesystem snapshot creation

    - Scan rootfs directory recursively
    - Capture file metadata (path, size, mtime, mode, type)
    - Handle symlinks and special files
    - Store in Snapshot data structure
    - _Requirements: 4.1_

  - [ ] 4.2 Implement snapshot comparison

    - Compare two snapshots to identify changes
    - Detect added files (in after, not in before)
    - Detect modified files (different size/mtime)
    - Detect deleted files (in before, not in after)
    - Return FilesystemDiff object
    - _Requirements: 4.2_

  - [ ] 4.3 Implement layer creation from diff

    - Create tar.gz archive with changed files
    - Add whiteout markers for deleted files (.wh.filename)
    - Preserve file permissions, ownership, timestamps
    - Calculate layer digest (SHA256 of compressed content)
    - Calculate diff_id (SHA256 of uncompressed content)
    - Create Layer object with proper metadata
    - _Requirements: 4.3, 4.4_

  - [ ] 4.4 Handle empty diffs
    - Detect when no filesystem changes occurred
    - Create empty layer marker if needed
    - Skip layer creation for no-op commands
    - _Requirements: 4.5_

- [ ] 5. Integrate isolation into BuildEngine

  - [ ] 5.1 Add isolation support detection

    - Check if platform supports isolation (Linux only)
    - Fall back to v0.1.0 behavior on unsupported platforms
    - Log isolation status at build start
    - _Requirements: 8.1, 8.2, 8.5_

  - [ ] 5.2 Implement FROM instruction handling

    - Parse FROM instruction to get image reference
    - Use BaseImageManager to pull base image
    - Extract base image to temporary rootfs
    - Store rootfs path in build context
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ] 5.3 Modify RUN instruction execution

    - Check if isolation is enabled and rootfs exists
    - If yes: use IsolationExecutor to run in chroot
    - If no: fall back to current subprocess execution
    - Capture execution result and handle errors
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [ ] 5.4 Implement layer diff capture after RUN

    - Create snapshot before command execution
    - Execute command in chroot
    - Create snapshot after command execution
    - Use LayerDiffManager to capture diff
    - Create layer from diff
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ] 5.5 Combine base and new layers in final image
    - Include all base image layers in manifest
    - Append new layers from RUN instructions
    - Update image config with all diff_ids (base + new)
    - Update history entries for all layers
    - Generate final manifest with correct layer order
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 6. Add build context isolation

  - Create unique temporary directory for each build
  - Extract base image to build-specific rootfs
  - Clean up temporary rootfs on build completion
  - Clean up temporary rootfs on build failure
  - Ensure concurrent builds don't interfere
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 7. Implement error handling and recovery

  - Add clear error messages for base image not found
  - Add clear error messages for layer extraction failures
  - Add clear error messages for RUN command failures (include command, exit code, stderr)
  - Add clear error messages for filesystem diff capture failures
  - Ensure cleanup happens on all error paths
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 8. Add configuration options

  - Add `enable_isolation` flag to BuildSettings
  - Add `base_image_cache_dir` path to BuildSettings
  - Add `chroot_timeout` setting to BuildSettings
  - Update config serialization/deserialization
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ] 9. Write unit tests

  - [ ] 9.1 Test BaseImageManager

    - Test image reference parsing (various formats)
    - Test base image caching logic
    - Test layer extraction with whiteouts
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ] 9.2 Test IsolationExecutor

    - Test Linux environment validation
    - Test chroot setup and cleanup
    - Test command execution in chroot
    - Test timeout handling
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 8.1, 8.2, 8.3, 8.4_

  - [ ] 9.3 Test LayerDiffManager

    - Test snapshot creation
    - Test snapshot comparison
    - Test layer creation from diff
    - Test empty diff handling
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ] 9.4 Test BuildEngine integration
    - Test FROM instruction handling
    - Test RUN instruction with isolation
    - Test layer combination
    - Test fallback to non-isolated mode
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 8.1, 8.2, 8.5_

- [ ] 10. Write integration tests

  - [ ] 10.1 Test building Ubuntu image with apt-get

    - Dockerfile with FROM ubuntu:22.04 and RUN apt-get install
    - Verify package is installed in final image
    - Verify layers are created correctly
    - _Requirements: All_

  - [ ] 10.2 Test building Alpine image with apk

    - Dockerfile with FROM alpine:latest and RUN apk add
    - Verify package is installed in final image
    - Verify layers are created correctly
    - _Requirements: All_

  - [ ] 10.3 Test multiple RUN instructions

    - Dockerfile with multiple RUN commands
    - Verify each RUN creates a separate layer
    - Verify filesystem changes are cumulative
    - _Requirements: 4.1, 4.2, 4.3, 5.4, 5.5_

  - [ ] 10.4 Test error scenarios
    - Test base image not found
    - Test RUN command failure
    - Test network failure during pull
    - Verify error messages are clear
    - Verify cleanup happens on failure
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 11. Update documentation
  - Update README with isolation feature description
  - Add examples of building real-world images
  - Document Linux requirement for isolation
  - Document configuration options
  - Update architecture documentation
  - _Requirements: All_
