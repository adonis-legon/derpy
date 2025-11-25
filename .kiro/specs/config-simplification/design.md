# Design Document

## Overview

This design document outlines the approach for simplifying the derpy container tool by removing per-user configuration features. With the daemon-based architecture operational, the image repository is now stored in a fixed, shared location managed by the daemon. This eliminates the need for per-user configuration files, simplifying both the codebase and user experience.

The key changes include:

- Removing the ConfigManager class and related configuration code
- Removing per-user config files (~/.derpy/config.yaml)
- Using daemon-managed shared repository paths
- Simplifying build isolation settings to use hardcoded defaults
- Updating documentation to reflect the simplified model
- Preparing version 0.3.0 for release

## Architecture

### Current Architecture (v0.2.x)

```
┌─────────────────┐
│   derpy CLI     │
└────────┬────────┘
         │
         ├──────────────────┐
         │                  │
         ▼                  ▼
┌─────────────────┐  ┌──────────────┐
│  ConfigManager  │  │   Daemon     │
│  (~/.derpy/     │  │  (shared     │
│   config.yaml)  │  │   repo)      │
└─────────────────┘  └──────────────┘
```

### New Architecture (v0.3.0)

```
┌─────────────────┐
│   derpy CLI     │
└────────┬────────┘
         │
         ▼
┌──────────────────┐
│     Daemon       │
│  (shared repo    │
│   at fixed path) │
└──────────────────┘
```

The new architecture removes the ConfigManager layer entirely. All storage operations go through the daemon, which manages a single shared repository at a fixed location.

## Components and Interfaces

### Removed Components

1. **ConfigManager** (derpy/core/config.py)

   - Entire file will be removed
   - No replacement needed - daemon handles storage paths

2. **Config Command Group** (derpy/cli/main.py)

   - `derpy config show` command removed
   - `derpy config set` command removed
   - Entire `@cli.group() config` section removed

3. **Configuration Models**
   - `Config` dataclass removed
   - `BuildSettings` dataclass removed
   - `RegistryConfig` dataclass removed (note: auth still uses credentials, not config)

### Modified Components

1. **CLI Commands** (derpy/cli/main.py)

   - Remove all `config_manager` references
   - Remove `ctx.obj['config_manager']` initialization
   - Update build command to use hardcoded defaults
   - Update other commands to work without config

2. **Build Engine** (derpy/build/engine.py)

   - Accept isolation settings as constructor parameters with defaults
   - Remove config dependency
   - Use hardcoded default values:
     - `enable_isolation`: True on Linux, False elsewhere
     - `base_image_cache_dir`: `/var/lib/derpy/cache/base-images` (daemon) or `~/.derpy/cache/base-images` (direct)
     - `chroot_timeout`: 600 seconds

3. **Storage Manager** (derpy/storage/manager.py)

   - Use fixed shared repository path: `/var/lib/derpy/images`
   - For direct execution fallback: `~/.derpy/images`
   - Remove config dependency

4. **Daemon** (derpy/daemon/server.py)
   - Use fixed paths for shared repository
   - No config file reading needed

### Hardcoded Default Values

```python
# Build isolation defaults
DEFAULT_ENABLE_ISOLATION = platform.system() == 'Linux'
DEFAULT_BASE_IMAGE_CACHE_DIR = '/var/lib/derpy/cache/base-images'  # daemon
DEFAULT_BASE_IMAGE_CACHE_DIR_USER = '~/.derpy/cache/base-images'  # direct execution
DEFAULT_CHROOT_TIMEOUT = 600  # 10 minutes

# Storage defaults
DEFAULT_SHARED_REPOSITORY = '/var/lib/derpy/images'  # daemon
DEFAULT_USER_REPOSITORY = '~/.derpy/images'  # direct execution fallback
```

## Data Models

### Removed Models

All configuration-related dataclasses are removed:

- `Config`
- `BuildSettings`
- `RegistryConfig` (from config.py - note: auth.py still has RegistryCredentials)

### Retained Models

All other existing models remain unchanged:

- `Image`, `Layer`, `Manifest` (OCI models)
- `BuildContext`, `Instruction` (build models)
- `RegistryCredentials` (auth models)
- `ImageMetadata` (storage models)

## Correctness Properties

_A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees._

### Property 1: No config file access

_For any_ derpy command execution, the system should never attempt to read or write files at ~/.derpy/config.yaml
**Validates: Requirements 1.1**

### Property 2: Config command removed

_For any_ attempt to run `derpy config`, the system should return an error indicating the command does not exist
**Validates: Requirements 2.4**

## Error Handling

### Removed Error Handling

- ConfigError exceptions no longer needed
- ConfigParseError exceptions no longer needed
- ConfigValidationError exceptions no longer needed

### Retained Error Handling

All other error handling remains:

- BuildError for build failures
- StorageError for storage issues
- AuthenticationError for auth problems
- DaemonConnectionError for daemon issues

### New Error Scenarios

None - the simplification reduces error scenarios by removing configuration complexity.

## Testing Strategy

### Unit Testing

Since this is primarily a refactoring/removal task, unit tests will focus on:

1. **Command Availability Tests**

   - Verify `derpy config` command no longer exists
   - Verify all other commands still work

2. **Path Usage Tests**

   - Verify daemon uses `/var/lib/derpy/images`
   - Verify direct execution uses `~/.derpy/images`
   - Verify no attempts to access `~/.derpy/config.yaml`

3. **Default Values Tests**

   - Verify build isolation uses correct defaults
   - Verify cache directory uses correct defaults
   - Verify timeout uses correct default

4. **Integration Tests**
   - Verify builds work without config files
   - Verify list/remove/purge work without config files
   - Verify daemon operations use shared repository

### Property-Based Testing

This feature involves primarily code removal and refactoring rather than new algorithmic behavior, so property-based testing is minimal. However, we will implement:

**Property Testing Framework**: pytest with Hypothesis

**Test Configuration**: Each property test will run a minimum of 100 iterations.

**Test Tagging**: Each property-based test will include a comment referencing the design document property using the format: `# Feature: config-simplification, Property N: <property text>`

The main testable property is:

**Property 1: No config file access**

- Generate random command sequences
- Execute commands
- Verify no file access to ~/.derpy/config.yaml
- This validates that config files are never touched

### Test Removal

The following test files will be removed:

- `tests/test_config.py` - entire file
- `tests/test_config_extended.py` - entire file

Configuration-related test cases in other files will be removed:

- Remove config-related tests from `tests/test_cli.py`
- Remove config-related tests from `tests/test_build_engine.py`
- Remove config-related tests from any other files that test config functionality

### Test Coverage Goals

- Maintain >80% code coverage after removal
- Ensure all daemon operations are covered
- Ensure all CLI commands are covered
- Ensure build isolation defaults are covered

## Implementation Notes

### Migration Path

Users upgrading from v0.2.x to v0.3.0:

1. Existing config files will be ignored (not deleted)
2. Daemon will use shared repository regardless of user config
3. No user action required - upgrade is transparent

### Backward Compatibility

- Images built with v0.2.x will work with v0.3.0
- OCI compliance ensures registry compatibility
- Daemon protocol remains unchanged

### Platform Considerations

- Linux: Full daemon support with shared repository
- macOS/Windows: Direct execution with user repository fallback
- Build isolation: Automatic platform detection (Linux only)

### Security Considerations

- Shared repository requires proper file permissions
- Daemon runs as root, manages shared storage
- Users in `derpy` group can access shared repository
- No security changes from v0.2.x

## Documentation Updates

### README.md Changes

1. Remove "Configuration Management" section entirely
2. Update "Quick Start" to remove config commands
3. Update "Usage" section to remove config examples
4. Update "Daemon vs Direct Execution" to clarify storage paths
5. Update "Troubleshooting" to remove config-related issues

### Steering Files Changes

1. Update `.kiro/steering/tech.md` to remove config commands
2. Update `.kiro/steering/structure.md` to remove ConfigManager references
3. Update `.kiro/steering/product.md` to reflect simplified model

### Example Updates

Verify all examples in `examples/` directory work without config:

- `examples/minimal/`
- `examples/alpine-python/`
- `examples/nginx-web/`
- `examples/python-app/`
- `examples/ubuntu-curl/`
- `examples/ubuntu-tools/`

## Version 0.3.0 Release Process

### Version Update

1. Update `pyproject.toml`:

   ```toml
   version = "0.3.0"
   ```

2. Update `derpy/__init__.py`:
   ```python
   __version__ = "0.3.0"
   ```

### Release Branch

1. Create release branch:

   ```bash
   git checkout -b release/0.3.0
   ```

2. Commit all changes:

   ```bash
   git add .
   git commit -m "Release v0.3.0: Simplify configuration by removing per-user config"
   ```

3. Push release branch:
   ```bash
   git push origin release/0.3.0
   ```

### CI/CD Workflow

The existing CI/CD workflow (`.github/workflows/release.yml`) will:

1. Run all tests
2. Build the package
3. Publish to PyPI
4. Create GitHub release
5. Merge back to main

### Release Notes

Version 0.3.0 release notes should include:

**Breaking Changes:**

- Removed `derpy config` command group
- Removed per-user configuration files
- Configuration is now managed by daemon with fixed paths

**Improvements:**

- Simplified user experience - no configuration needed
- Reduced codebase complexity
- Faster startup (no config file parsing)

**Migration:**

- No user action required
- Existing config files are ignored
- Daemon uses shared repository automatically

## Dependencies

### Removed Dependencies

None - all existing dependencies remain.

### Modified Dependencies

None - dependency versions unchanged.

## Performance Considerations

### Performance Improvements

1. **Faster Startup**: No config file parsing on every command
2. **Reduced I/O**: No config file reads/writes
3. **Simpler Code Paths**: Fewer conditional branches

### Performance Metrics

Expected improvements:

- CLI startup time: ~10-20ms faster
- Build command initialization: ~5-10ms faster
- Overall: Negligible but positive impact

## Future Considerations

### Potential Future Enhancements

1. **Daemon Configuration**: If needed, daemon could have its own config file (not per-user)
2. **Environment Variables**: Could add environment variable overrides for advanced users
3. **System-Wide Config**: Could add `/etc/derpy/config.yaml` for system administrators

### Extensibility

The simplified design makes it easier to:

- Add new CLI commands without config concerns
- Modify storage paths in one place (daemon)
- Test functionality without config setup

## Risks and Mitigations

### Risk 1: Users Expect Configuration

**Mitigation**: Clear documentation explaining the simplified model and why it's better.

### Risk 2: Advanced Users Need Customization

**Mitigation**: Document environment variable overrides for advanced use cases (future enhancement).

### Risk 3: Breaking Changes

**Mitigation**: Clear release notes, version bump to 0.3.0, and transparent migration path.

## Success Criteria

The implementation is successful when:

1. ✅ All config-related code is removed
2. ✅ All tests pass without config files
3. ✅ Documentation is updated and accurate
4. ✅ Version 0.3.0 is published to PyPI
5. ✅ Users can build/list/remove images without config
6. ✅ Daemon uses shared repository correctly
7. ✅ Direct execution fallback works correctly
