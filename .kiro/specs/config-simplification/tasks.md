# Implementation Plan

- [x] 1. Remove configuration infrastructure

  - Remove derpy/core/config.py file completely
  - Remove ConfigManager class and all configuration models
  - Remove configuration serialization/deserialization functions
  - _Requirements: 2.1, 2.5_

- [x] 2. Update CLI to remove config commands and dependencies

  - Remove config command group (@cli.group() config and all subcommands)
  - Remove config_manager initialization from CLI context
  - Remove all imports of ConfigManager, Config, BuildSettings, RegistryConfig from cli/main.py
  - Update build command to use hardcoded defaults instead of config
  - Update other commands (ls, rm, purge, push) to work without config
  - _Requirements: 2.2, 2.3, 2.4, 1.2, 1.3, 1.4, 1.5_

- [x] 3. Update BuildEngine to use hardcoded defaults

  - Modify BuildEngine constructor to accept isolation parameters with defaults
  - Remove config dependency from BuildEngine
  - Use platform detection for enable_isolation default (Linux=True, others=False)
  - Use hardcoded paths for base_image_cache_dir
  - Use hardcoded default for chroot_timeout (600 seconds)
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 4. Update StorageManager to use fixed paths

  - Modify ImageManager to use fixed shared repository path
  - Use /var/lib/derpy/images for daemon mode
  - Use ~/.derpy/images for direct execution fallback
  - Remove config dependency from storage manager
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 5. Update daemon to use fixed paths

  - Ensure daemon uses /var/lib/derpy/images for shared repository
  - Ensure daemon uses /var/lib/derpy/cache/base-images for cache
  - Remove any config file reading from daemon code
  - _Requirements: 6.1_

- [x] 6. Remove configuration tests

  - Delete tests/test_config.py
  - Delete tests/test_config_extended.py
  - Remove config-related test cases from tests/test_cli.py
  - Remove config-related test cases from tests/test_build_engine.py
  - Remove config-related test cases from any other test files
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 6.1 Write property test for no config file access

  - **Property 1: No config file access**
  - **Validates: Requirements 1.1**

- [x] 6.2 Write unit test for config command removal

  - Verify `derpy config` command no longer exists
  - **Validates: Requirements 2.4**

- [x] 6.3 Write unit tests for default values

  - Verify build isolation uses correct defaults
  - Verify cache directory uses correct defaults
  - Verify timeout uses correct default
  - **Validates: Requirements 7.1**

- [x] 6.4 Write integration tests for commands without config

  - Test build command works without config files
  - Test ls command works without config files
  - Test rm command works without config files
  - Test purge command works without config files
  - **Validates: Requirements 1.2, 1.3, 1.4, 1.5**

- [x] 7. Checkpoint - Ensure all tests pass

  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Update README.md documentation

  - Remove "Configuration Management" section
  - Update "Quick Start" section to remove config commands
  - Update "Usage" section to remove config examples
  - Update "Daemon vs Direct Execution" to clarify storage paths
  - Update "Troubleshooting" to remove config-related issues
  - _Requirements: 4.1, 4.2, 4.3_

- [x] 9. Update steering files

  - Update .kiro/steering/tech.md to remove config commands
  - Update .kiro/steering/structure.md to remove ConfigManager references
  - Update .kiro/steering/product.md to reflect simplified model
  - _Requirements: 4.4_

- [x] 9.1 Verify examples work without config

  - Test all examples in examples/ directory
  - Ensure they work without config files
  - **Validates: Requirements 4.5**

- [x] 10. Update version to 0.3.0

  - Update version in pyproject.toml to "0.3.0"
  - Update **version** in derpy/**init**.py to "0.3.0"
  - _Requirements: 5.1, 5.2_

- [-] 11. Create and push release branch

  - Create release/0.3.0 branch
  - Commit all changes with message "Release v0.3.0: Simplify configuration by removing per-user config"
  - Push release/0.3.0 branch to trigger CI/CD
  - _Requirements: 5.3, 5.4_

- [ ] 12. Final Checkpoint - Verify release
  - Ensure CI/CD workflow completes successfully
  - Verify version 0.3.0 is published to PyPI
  - Verify release notes are accurate
  - _Requirements: 5.5_
