# Design Document

## Overview

This feature adds image removal capabilities to derpy through two new CLI commands: `rm` for removing individual images and `purge` for bulk removal of all images and cached data. The implementation extends the existing ImageManager class with removal methods and adds new CLI commands that follow derpy's established patterns for error handling, user feedback, and configuration management.

## Architecture

### Component Overview

The feature consists of three main components:

1. **CLI Commands** (`derpy/cli/main.py`)

   - `derpy rm <image:tag>` - Remove a specific image
   - `derpy purge [--force]` - Remove all images and cache

2. **Storage Manager Extensions** (`derpy/storage/manager.py`)

   - `remove_image(tag: str) -> bool` - Remove single image
   - `remove_all_images() -> int` - Remove all images
   - `calculate_storage_size() -> int` - Calculate total storage size
   - `get_cache_size() -> int` - Calculate base image cache size

3. **Exception Handling** (`derpy/core/exceptions.py`)
   - Leverage existing `StorageError`, `ImageNotFoundError`
   - Add `ImageRemovalError` for removal-specific failures

### Data Flow

#### Remove Single Image (`rm`)

```
User Command → CLI Validation → ImageManager.remove_image() →
Update metadata.json → Remove from OCI index → Display confirmation
```

#### Purge All Images (`purge`)

```
User Command → Confirmation Prompt (unless --force) →
ImageManager.remove_all_images() → Clear metadata.json →
Clear OCI layout → Remove base image cache → Display summary
```

## Components and Interfaces

### CLI Commands

#### `derpy rm` Command

```python
@cli.command()
@click.argument('image')
@click.pass_context
def rm(ctx, image: str):
    """
    Remove a container image from local storage.

    IMAGE is the image tag to remove (e.g., myapp:latest).

    Examples:

      derpy rm myapp:latest

      derpy rm nginx:alpine
    """
```

**Behavior:**

- Validates image tag format
- Checks if image exists in local repository
- Calls `ImageManager.remove_image()`
- Displays success message with freed space
- Exits with code 1 on error, 0 on success

**Output Examples:**

```
Success:
  Removing image 'myapp:latest'...
  ✓ Successfully removed image: myapp:latest
    Freed: 45.2MB

Not Found:
  Error: Image 'myapp:latest' not found in local repository.

  List available images with: derpy ls
```

#### `derpy purge` Command

```python
@cli.command()
@click.option(
    '-f', '--force',
    is_flag=True,
    help='Skip confirmation prompt'
)
@click.pass_context
def purge(ctx, force: bool):
    """
    Remove all container images and cached data.

    This command removes all images from local storage and clears
    the base image cache. Use with caution as this operation cannot
    be undone.

    Examples:

      derpy purge

      derpy purge --force
    """
```

**Behavior:**

- Calculates total storage size before removal
- Prompts for confirmation unless `--force` is specified
- Calls `ImageManager.remove_all_images()`
- Clears base image cache directory
- Displays summary with images removed and space freed
- Exits with code 0 on success or user cancellation

**Output Examples:**

```
Interactive (with confirmation):
  WARNING: This will remove all images and cached data.

  Images: 5
  Storage: 234.5MB
  Cache: 128.3MB
  Total: 362.8MB

  Are you sure you want to continue? [y/N]: y

  Removing all images...
  Clearing base image cache...

  ✓ Successfully purged all images
    Images removed: 5
    Space freed: 362.8MB

Force mode:
  Removing all images...
  Clearing base image cache...

  ✓ Successfully purged all images
    Images removed: 5
    Space freed: 362.8MB

No images:
  No images found in local repository.
  Nothing to purge.
```

### ImageManager Extensions

#### New Methods

```python
def remove_image(self, tag: str) -> bool:
    """Remove a single image from local repository.

    Args:
        tag: Image tag to remove

    Returns:
        True if image was removed, False if not found

    Raises:
        StorageError: If removal fails
    """

def remove_all_images(self) -> int:
    """Remove all images from local repository.

    Returns:
        Number of images removed

    Raises:
        StorageError: If removal fails
    """

def calculate_storage_size(self) -> int:
    """Calculate total size of image storage.

    Returns:
        Total size in bytes

    Raises:
        StorageError: If calculation fails
    """

def get_cache_size(self, cache_dir: Path) -> int:
    """Calculate size of base image cache directory.

    Args:
        cache_dir: Path to base image cache directory

    Returns:
        Total cache size in bytes

    Raises:
        StorageError: If calculation fails
    """
```

#### Implementation Details

**`remove_image(tag: str)`:**

1. Check if image exists using `_get_image_metadata(tag)`
2. If not found, return False
3. Load all metadata from `metadata.json`
4. Remove the image entry from metadata dictionary
5. Save updated metadata back to file
6. Remove manifest from OCI index using `oci_layout.remove_manifest_from_index(tag)`
7. Return True

**Note:** Blob cleanup is intentionally not performed during individual image removal since blobs may be shared between images. Users can run a separate cleanup operation if needed (future enhancement).

**`remove_all_images()`:**

1. Load current metadata to count images
2. Store count for return value
3. Clear metadata by saving empty dictionary `{}`
4. Clear OCI index by recreating layout
5. Remove all blobs from `blobs/` directory
6. Return count of removed images

**`calculate_storage_size()`:**

1. Initialize total_size = 0
2. Iterate through all files in `repository_path` recursively
3. Sum file sizes using `Path.stat().st_size`
4. Return total_size

**`get_cache_size(cache_dir: Path)`:**

1. Check if cache_dir exists, return 0 if not
2. Initialize total_size = 0
3. Iterate through all files in cache_dir recursively
4. Sum file sizes using `Path.stat().st_size`
5. Return total_size

### OCI Layout Manager Extensions

The `OCILayoutManager` class needs a new method to support removing manifests from the index:

```python
def remove_manifest_from_index(self, tag: str) -> bool:
    """Remove a manifest reference from the OCI index.

    Args:
        tag: Image tag to remove from index

    Returns:
        True if removed, False if not found

    Raises:
        StorageError: If index update fails
    """
```

**Implementation:**

1. Load current index from `index.json`
2. Filter out manifest entries matching the tag
3. Save updated index back to file
4. Return True if entry was found and removed, False otherwise

## Data Models

No new data models are required. The feature uses existing models:

- `ImageMetadata` - Already exists in `ImageManager`
- `ImageInfo` - Already exists for listing images
- Metadata storage format (`metadata.json`) remains unchanged

## Error Handling

### Error Scenarios

1. **Image Not Found (rm command)**

   - Detection: `ImageManager.remove_image()` returns False
   - Response: Display error message with suggestion to run `derpy ls`
   - Exit code: 1

2. **No Images to Purge**

   - Detection: `ImageManager.remove_all_images()` returns 0
   - Response: Display informational message
   - Exit code: 0 (not an error)

3. **Permission Denied**

   - Detection: OSError with errno EACCES during file operations
   - Response: Raise `StorageError` with permission error message
   - Exit code: 1

4. **Disk I/O Error**

   - Detection: OSError during file operations
   - Response: Raise `StorageError` with descriptive message
   - Exit code: 1

5. **Corrupted Metadata**

   - Detection: JSON decode error or missing fields
   - Response: Log warning, continue with removal (best effort)
   - Exit code: 0 (partial success)

6. **User Cancellation (purge)**
   - Detection: User responds "no" to confirmation prompt
   - Response: Display cancellation message
   - Exit code: 0 (user choice, not an error)

### Exception Strategy

- Use existing `StorageError` for all storage-related failures
- Use existing `ImageNotFoundError` when appropriate (though `rm` returns False instead)
- Wrap OS-level exceptions (OSError, PermissionError) in `StorageError`
- Include remediation suggestions in error messages
- Log detailed error information for troubleshooting

## Testing Strategy

### Unit Tests

**Test File:** `tests/test_image_removal.py`

1. **ImageManager.remove_image() Tests**

   - Test removing existing image (success case)
   - Test removing non-existent image (returns False)
   - Test metadata is updated correctly
   - Test OCI index is updated correctly
   - Test error handling for file permission issues

2. **ImageManager.remove_all_images() Tests**

   - Test removing multiple images
   - Test removing when no images exist (returns 0)
   - Test metadata file is cleared
   - Test OCI layout is cleared
   - Test return value matches image count

3. **ImageManager.calculate_storage_size() Tests**

   - Test size calculation with multiple images
   - Test size calculation with empty repository
   - Test size calculation includes all files

4. **ImageManager.get_cache_size() Tests**
   - Test cache size calculation
   - Test with non-existent cache directory
   - Test with empty cache directory

### Integration Tests

**Test File:** `tests/test_image_removal_integration.py`

1. **CLI rm Command Tests**

   - Test removing image via CLI
   - Test error message for non-existent image
   - Test output format and messages
   - Test exit codes

2. **CLI purge Command Tests**

   - Test purge with confirmation (mocked input)
   - Test purge with --force flag
   - Test purge with no images
   - Test user cancellation
   - Test output format and summary

3. **End-to-End Tests**
   - Build image → Remove with rm → Verify removal
   - Build multiple images → Purge → Verify all removed
   - Build image → Purge cache → Verify cache cleared

### Test Utilities

Use existing test fixtures:

- `tmp_path` - Pytest fixture for temporary directories
- `mock_config` - Mock ConfigManager for testing
- `sample_image` - Create test images for removal

### Coverage Goals

- Minimum 90% code coverage for new methods
- 100% coverage for error handling paths
- All CLI commands tested with various inputs

## Implementation Notes

### File Operations Safety

- Use `Path.unlink(missing_ok=True)` for safe file deletion
- Use `shutil.rmtree()` for directory removal with error handling
- Ensure atomic metadata updates (write to temp file, then rename)

### Performance Considerations

- Size calculations may be slow for large repositories
- Consider caching size calculations or showing progress for purge
- Avoid loading full image data during removal (only metadata needed)

### Cross-Platform Compatibility

- Use `pathlib.Path` for all path operations
- Use `derpy.core.platform.normalize_path()` for path normalization
- Test on Windows, Linux, and macOS

### User Experience

- Provide clear, actionable error messages
- Show progress for long operations (purge)
- Display human-readable sizes (MB, GB)
- Use consistent formatting with existing commands (ls, build)
- Confirmation prompt prevents accidental data loss

### Future Enhancements

Not included in this implementation but noted for future consideration:

1. **Orphaned Blob Cleanup**

   - Add `derpy cleanup` command to remove unused blobs
   - Implement reference counting for shared layers

2. **Selective Purge**

   - Add filters to purge command (e.g., `--older-than`, `--pattern`)
   - Support removing images by pattern matching

3. **Dry Run Mode**

   - Add `--dry-run` flag to show what would be removed
   - Useful for scripting and automation

4. **Progress Indicators**

   - Show progress bar for large purge operations
   - Display current file being processed

5. **Reclaim Space Report**
   - Show detailed breakdown of space usage
   - Identify largest images and layers
