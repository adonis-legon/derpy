# Requirements Document

## Introduction

This feature adds image removal capabilities to derpy, enabling users to free up disk space by removing individual images or purging all stored images. The feature includes two new CLI commands: `rm` for targeted image removal and `purge` for bulk removal of all images and cached data.

## Glossary

- **Derpy**: The independent container tool that builds and manages OCI-compliant container images
- **Image Storage**: The local directory (~/.derpy/images/) where built and pulled images are stored
- **Base Image Cache**: The directory (~/.derpy/cache/base-images/) where downloaded base images are cached for build isolation
- **Image Reference**: A string in the format "name:tag" that uniquely identifies a container image
- **OCI Layout**: The directory structure and metadata files that define an OCI-compliant image
- **ImageManager**: The derpy component responsible for managing local image storage operations
- **CLI**: Command-line interface through which users interact with derpy

## Requirements

### Requirement 1

**User Story:** As a derpy user, I want to remove a specific image by its name and tag, so that I can free up disk space from images I no longer need

#### Acceptance Criteria

1. WHEN the user executes `derpy rm <image:tag>`, THE CLI SHALL remove the specified image from Image Storage
2. WHEN the user executes `derpy rm <image:tag>`, THE CLI SHALL display a confirmation message indicating successful removal
3. IF the specified image does not exist in Image Storage, THEN THE CLI SHALL display an error message and exit with a non-zero status code
4. WHEN the user executes `derpy rm` without providing an image reference, THEN THE CLI SHALL display usage information and exit with a non-zero status code
5. WHEN the user executes `derpy rm <image:tag>`, THE ImageManager SHALL remove all OCI Layout files and directories associated with the specified image

### Requirement 2

**User Story:** As a derpy user, I want to remove all stored images at once, so that I can quickly reclaim disk space without removing images individually

#### Acceptance Criteria

1. WHEN the user executes `derpy purge`, THE CLI SHALL remove all images from Image Storage
2. WHEN the user executes `derpy purge`, THE CLI SHALL remove all cached base images from Base Image Cache
3. WHEN the user executes `derpy purge`, THE CLI SHALL display a summary message indicating the number of images removed and disk space reclaimed
4. IF Image Storage contains no images, THEN THE CLI SHALL display a message indicating no images were found
5. WHEN the user executes `derpy purge`, THE CLI SHALL prompt the user for confirmation before proceeding with removal

### Requirement 3

**User Story:** As a derpy user, I want the removal commands to handle errors gracefully, so that I understand what went wrong if removal fails

#### Acceptance Criteria

1. IF file system operations fail during image removal, THEN THE CLI SHALL display a descriptive error message and exit with a non-zero status code
2. IF the user lacks permissions to delete image files, THEN THE CLI SHALL display a permission error message and exit with a non-zero status code
3. WHEN removal operations encounter errors, THE CLI SHALL log detailed error information for troubleshooting
4. IF partial removal occurs due to errors, THEN THE CLI SHALL report which operations succeeded and which failed
5. WHEN the ImageManager encounters corrupted image data during removal, THE CLI SHALL continue with removal and report the corruption

### Requirement 4

**User Story:** As a derpy user, I want to skip the confirmation prompt for purge operations, so that I can automate cleanup in scripts

#### Acceptance Criteria

1. WHEN the user executes `derpy purge --force`, THE CLI SHALL skip the confirmation prompt and proceed with removal immediately
2. WHEN the user executes `derpy purge -f`, THE CLI SHALL skip the confirmation prompt and proceed with removal immediately
3. WHERE the --force flag is provided, THE CLI SHALL remove all images without user interaction
4. WHEN the user executes `derpy purge --force`, THE CLI SHALL display the same summary message as the interactive version
5. WHEN the user responds "no" to the confirmation prompt, THE CLI SHALL cancel the operation and exit with status code zero

### Requirement 5

**User Story:** As a derpy developer, I want the removal functionality to be testable and maintainable, so that the feature remains reliable as the codebase evolves

#### Acceptance Criteria

1. THE ImageManager SHALL provide a method to remove a single image by reference that returns a boolean indicating success
2. THE ImageManager SHALL provide a method to remove all images that returns a count of removed images
3. THE ImageManager SHALL provide a method to calculate disk space used by images that returns size in bytes
4. WHEN removal methods are called, THE ImageManager SHALL validate that Image Storage exists before attempting removal
5. THE removal methods SHALL raise specific exceptions from derpy.core.exceptions for different error conditions
