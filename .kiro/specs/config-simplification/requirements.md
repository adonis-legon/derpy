# Requirements Document

## Introduction

This specification defines the requirements for simplifying the derpy container tool by removing per-user configuration features. With the daemon-based architecture now operational, the image repository is stored in a fixed, shared location accessible to all users. This change eliminates the need for per-user configuration management, simplifying both the codebase and user experience. This work is part of preparing version 0.3.0 of derpy-tool.

## Glossary

- **Derpy**: An independent container tool that builds, manages, and distributes OCI-compliant container images
- **Daemon (derpyd)**: A privileged background service that handles container build operations
- **Per-User Config**: Configuration files stored in each user's home directory (~/.derpy/config.yaml)
- **Shared Repository**: A centralized image storage location accessible to all users through the daemon
- **ConfigManager**: The Python class responsible for managing configuration files
- **CLI**: Command-line interface for interacting with derpy
- **OCI**: Open Container Initiative, the standard for container images

## Requirements

### Requirement 1

**User Story:** As a derpy user, I want the tool to work without managing per-user configuration files, so that I can focus on building containers without configuration overhead.

#### Acceptance Criteria

1. WHEN a user runs any derpy command THEN the system SHALL NOT create or read per-user configuration files in ~/.derpy/config.yaml
2. WHEN a user runs derpy build THEN the system SHALL use the daemon's shared repository without requiring user-specific configuration
3. WHEN a user runs derpy ls THEN the system SHALL list images from the shared repository without accessing per-user config
4. WHEN a user runs derpy rm THEN the system SHALL remove images from the shared repository without per-user config
5. WHEN a user runs derpy purge THEN the system SHALL clear the shared repository without per-user config

### Requirement 2

**User Story:** As a derpy developer, I want to remove the ConfigManager class and related configuration code, so that the codebase is simpler and easier to maintain.

#### Acceptance Criteria

1. WHEN the ConfigManager class is removed THEN the system SHALL remove the derpy/core/config.py file
2. WHEN configuration code is removed THEN the system SHALL remove all imports of ConfigManager from CLI and other modules
3. WHEN configuration code is removed THEN the system SHALL remove all calls to config_manager.get_config() and related methods
4. WHEN configuration code is removed THEN the system SHALL remove the config command group from the CLI
5. WHEN configuration models are removed THEN the system SHALL remove RegistryConfig, BuildSettings, and Config dataclasses

### Requirement 3

**User Story:** As a derpy developer, I want to remove configuration-related tests, so that the test suite only covers active functionality.

#### Acceptance Criteria

1. WHEN configuration code is removed THEN the system SHALL remove test_config.py
2. WHEN configuration code is removed THEN the system SHALL remove test_config_extended.py
3. WHEN configuration code is removed THEN the system SHALL remove configuration-related test cases from other test files
4. WHEN tests are removed THEN the system SHALL ensure all remaining tests pass
5. WHEN tests are removed THEN the system SHALL maintain test coverage for daemon-based operations

### Requirement 4

**User Story:** As a derpy user, I want updated documentation that reflects the simplified configuration model, so that I understand how to use the tool correctly.

#### Acceptance Criteria

1. WHEN documentation is updated THEN the system SHALL remove all references to per-user configuration from README.md
2. WHEN documentation is updated THEN the system SHALL remove the "Configuration Management" section from README.md
3. WHEN documentation is updated THEN the system SHALL update the "Quick Start" section to remove config commands
4. WHEN documentation is updated THEN the system SHALL update steering files to remove configuration guidance
5. WHEN documentation is updated THEN the system SHALL ensure all examples work without configuration commands

### Requirement 5

**User Story:** As a derpy maintainer, I want to create version 0.3.0 with these changes, so that users can benefit from the simplified tool.

#### Acceptance Criteria

1. WHEN the version is updated THEN the system SHALL set the version to 0.3.0 in pyproject.toml
2. WHEN the version is updated THEN the system SHALL set the version to 0.3.0 in derpy/**init**.py
3. WHEN a release branch is created THEN the system SHALL create a branch named release/0.3.0
4. WHEN the release branch is pushed THEN the system SHALL trigger the CI/CD workflow
5. WHEN the CI/CD workflow completes THEN the system SHALL publish version 0.3.0 to PyPI

### Requirement 6

**User Story:** As a derpy user, I want the daemon to handle all storage paths, so that I don't need to configure image storage locations.

#### Acceptance Criteria

1. WHEN the daemon starts THEN the system SHALL use a fixed shared repository path
2. WHEN build operations execute THEN the system SHALL store images in the shared repository
3. WHEN list operations execute THEN the system SHALL read from the shared repository
4. WHEN remove operations execute THEN the system SHALL delete from the shared repository
5. WHEN the daemon is unavailable THEN the system SHALL use a sensible default path for direct execution

### Requirement 7

**User Story:** As a derpy developer, I want to remove build isolation configuration options, so that the tool uses sensible defaults without user configuration.

#### Acceptance Criteria

1. WHEN build isolation code is simplified THEN the system SHALL use hardcoded default values for isolation settings
2. WHEN build isolation code is simplified THEN the system SHALL remove enable_isolation configuration option
3. WHEN build isolation code is simplified THEN the system SHALL remove base_image_cache_dir configuration option
4. WHEN build isolation code is simplified THEN the system SHALL remove chroot_timeout configuration option
5. WHEN build isolation code is simplified THEN the system SHALL maintain backward compatibility with existing builds
