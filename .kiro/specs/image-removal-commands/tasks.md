# Implementation Plan

- [x] 1. Extend OCILayoutManager with manifest removal capability

  - Add `remove_manifest_from_index(tag: str) -> bool` method to OCILayoutManager
  - Load current index.json, filter out manifest entries matching the tag, save updated index
  - Handle cases where index doesn't exist or tag is not found
  - _Requirements: 1.1, 1.5_

- [x] 2. Implement storage size calculation methods in ImageManager

  - [x] 2.1 Add `calculate_storage_size() -> int` method

    - Recursively iterate through repository_path and sum file sizes
    - Handle cases where repository doesn't exist
    - Return total size in bytes
    - _Requirements: 2.3, 5.3_

  - [x] 2.2 Add `get_cache_size(cache_dir: Path) -> int` method
    - Check if cache directory exists, return 0 if not
    - Recursively iterate through cache_dir and sum file sizes
    - Return total size in bytes
    - _Requirements: 2.2, 2.3_

- [x] 3. Implement image removal methods in ImageManager

  - [x] 3.1 Add `remove_image(tag: str) -> bool` method

    - Check if image exists using existing `_get_image_metadata()`
    - Load metadata, remove image entry, save updated metadata
    - Call `oci_layout.remove_manifest_from_index(tag)`
    - Return True if removed, False if not found
    - Wrap exceptions in StorageError with descriptive messages
    - _Requirements: 1.1, 1.5, 3.1, 3.3, 5.1_

  - [x] 3.2 Add `remove_all_images() -> int` method
    - Load current metadata to count images
    - Clear metadata by saving empty dictionary
    - Recreate OCI layout to clear index and blobs
    - Return count of removed images
    - Handle errors gracefully and wrap in StorageError
    - _Requirements: 2.1, 2.2, 3.1, 3.3, 5.1_

- [x] 4. Implement `derpy rm` CLI command

  - [x] 4.1 Add rm command to CLI with image argument

    - Use @cli.command() decorator with click.argument for image tag
    - Add docstring with usage examples
    - _Requirements: 1.1, 1.4_

  - [x] 4.2 Implement rm command logic
    - Validate image tag is provided (handled by click)
    - Create ImageManager instance
    - Call `remove_image(tag)` and check return value
    - Display success message with freed space on success
    - Display error message with suggestion to run `derpy ls` if not found
    - Handle StorageError exceptions and display error messages
    - Exit with code 1 on error, 0 on success
    - _Requirements: 1.1, 1.2, 1.3, 3.1, 3.2, 3.3_

- [x] 5. Implement `derpy purge` CLI command

  - [x] 5.1 Add purge command to CLI with force flag

    - Use @cli.command() decorator with --force/-f flag option
    - Add docstring with usage examples and warning
    - _Requirements: 2.1, 4.1, 4.2_

  - [x] 5.2 Implement purge command logic with confirmation
    - Create ImageManager instance
    - Calculate storage size and cache size before removal
    - Count images from metadata
    - Display warning with size information
    - Prompt user for confirmation unless --force is specified
    - Handle user cancellation (exit with code 0)
    - Call `remove_all_images()` if confirmed
    - Clear base image cache directory using shutil.rmtree
    - Display summary with images removed and space freed
    - Handle StorageError exceptions and display error messages
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 6. Add helper function for human-readable size formatting

  - Create `format_size(size_bytes: int) -> str` helper function in CLI module
  - Format bytes as B, KB, MB, GB, TB with one decimal place
  - Use in both rm and purge commands for consistent output
  - _Requirements: 2.3_

- [x] 7. Write unit tests for ImageManager removal methods

  - [x] 7.1 Test remove_image() method

    - Test removing existing image returns True
    - Test removing non-existent image returns False
    - Test metadata is updated correctly after removal
    - Test OCI index is updated correctly after removal
    - Test StorageError is raised on file permission issues
    - _Requirements: 5.1, 5.2, 5.5_

  - [x] 7.2 Test remove_all_images() method

    - Test removing multiple images returns correct count
    - Test removing when no images exist returns 0
    - Test metadata file is cleared
    - Test OCI layout is cleared
    - Test StorageError is raised on failures
    - _Requirements: 5.1, 5.2, 5.5_

  - [x] 7.3 Test size calculation methods
    - Test calculate_storage_size() with multiple images
    - Test calculate_storage_size() with empty repository
    - Test get_cache_size() with cache directory
    - Test get_cache_size() with non-existent directory
    - _Requirements: 5.3_

- [x] 8. Write integration tests for CLI commands

  - [x] 8.1 Test rm command

    - Test removing image via CLI displays success message
    - Test removing non-existent image displays error
    - Test exit codes (0 for success, 1 for error)
    - Test output format matches design
    - _Requirements: 1.1, 1.2, 1.3, 3.2_

  - [x] 8.2 Test purge command

    - Test purge with --force flag removes all images
    - Test purge displays confirmation prompt without --force
    - Test purge with no images displays appropriate message
    - Test exit codes
    - Test output format and summary
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 8.3 Test end-to-end workflows
    - Build image, remove with rm, verify removal
    - Build multiple images, purge, verify all removed
    - Build image, purge with cache, verify cache cleared
    - _Requirements: 1.1, 1.5, 2.1, 2.2_
