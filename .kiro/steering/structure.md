## Project Structure

```
derpy/
├── cli/              # CLI interface and commands
│   ├── main.py       # Entry point, click commands
│   └── banner.py     # ASCII banner display
├── core/             # Core utilities and configuration
│   ├── config.py     # Configuration management (ConfigManager, Config models)
│   ├── exceptions.py # Custom exception hierarchy
│   ├── logging.py    # Logging setup
│   └── platform.py   # Cross-platform path/directory utilities
├── build/            # Build engine and layer creation
│   ├── engine.py     # BuildEngine, BuildContext
│   ├── layers.py     # LayerBuilder for filesystem layers
│   └── pipeline.py   # InstructionPipeline for build execution
├── dockerfile/       # Dockerfile parsing
│   ├── parser.py     # DockerfileParser, Instruction models
│   └── handlers.py   # Instruction handlers (FROM, RUN, CMD)
├── oci/              # OCI specification models
│   ├── models.py     # Manifest, ImageConfig, Layer, Descriptor
│   └── layout.py     # OCI layout management
├── storage/          # Local image storage
│   └── manager.py    # ImageManager for local repository
└── registry/         # Registry client
    └── client.py     # RegistryClient for push/pull operations

tests/                # Test suite (mirrors source structure)
examples/             # Sample Dockerfiles
scripts/              # Build and utility scripts
```

## Architecture Patterns

- Dataclasses for models with to_dict/from_dict serialization
- Custom exception hierarchy inheriting from base exceptions
- Type hints on all function signatures
- Docstrings for public functions and classes
- Path objects (pathlib.Path) for all file operations
- Context managers for resource management (e.g., RegistryClient)
- Validation methods on models returning List[str] of errors

## Code Conventions

- PEP 8 style guide
- Line length: 88 characters (black default)
- Import order: standard library, third-party, local
- Test files: `test_*.py` with `Test*` classes and `test_*` functions
- Test markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- Error handling: Raise specific exceptions from derpy.core.exceptions
- Configuration: Use ConfigManager for all config operations
- Platform paths: Use derpy.core.platform utilities for cross-platform compatibility
