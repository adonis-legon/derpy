# Contributing to Derpy

Thank you for your interest in contributing to Derpy! This document provides guidelines and instructions for setting up your development environment and contributing to the project.

## Development Environment Setup

### Prerequisites

- Python 3.8 or higher
- Git

### Virtual Environment (Recommended)

**Important**: Always use a virtual environment when developing Derpy. This is especially important if you manage Python via Homebrew, system package managers, or have other Python projects with different dependencies.

#### Creating a Virtual Environment

```bash
# Clone the repository
git clone https://github.com/adonis-legon/derpy.git
cd derpy

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

#### Installing Dependencies

```bash
# Install derpy in editable mode
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

### Verifying Your Setup

```bash
# Run tests to verify everything works
pytest

# Check code formatting
black --check derpy tests

# Run linter
flake8 derpy tests

# Run type checker
mypy derpy
```

## Project Philosophy

Derpy is designed to be an **independent container tool** that:

1. **Does not depend on Docker, Podman, or containerd**: Derpy implements container functionality from scratch
2. **Minimizes external dependencies**: Uses Python standard library wherever possible
3. **Maintains OCI compliance**: Ensures interoperability with existing container ecosystems
4. **Stays cross-platform**: Works consistently on Windows, Linux, and macOS
5. **Provides build isolation on Linux**: Uses chroot to execute RUN commands in base image filesystems

## Development Workflow

### Before Making Changes

1. Create a new branch for your feature or bugfix:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Ensure your virtual environment is activated:
   ```bash
   source venv/bin/activate  # macOS/Linux
   ```

### Making Changes

1. Write your code following the project's coding standards
2. Add or update tests for your changes
3. Run the test suite to ensure nothing breaks:

   ```bash
   pytest
   ```

4. Format your code:

   ```bash
   black derpy tests
   ```

5. Check for linting issues:

   ```bash
   flake8 derpy tests
   ```

6. Run type checking:
   ```bash
   mypy derpy
   ```

### Committing Changes

1. Stage your changes:

   ```bash
   git add .
   ```

2. Commit with a descriptive message:

   ```bash
   git commit -m "Add feature: description of your changes"
   ```

3. Push to your fork:

   ```bash
   git push origin feature/your-feature-name
   ```

4. Create a pull request on GitHub

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=derpy --cov-report=html

# Run specific test file
pytest tests/test_config.py

# Run specific test
pytest tests/test_config.py::test_config_manager_load

# Run unit tests only
pytest -m unit

# Run integration tests only (may require Linux for isolation tests)
pytest -m integration
```

### Testing Build Isolation

Build isolation tests require a Linux environment:

- **On Linux**: All tests should pass
- **On macOS/Windows**: Isolation tests will be skipped automatically

To test build isolation features:

```bash
# Run isolation-specific tests (Linux only)
pytest tests/test_build_isolation_integration.py
pytest tests/test_isolation_executor.py
pytest tests/test_base_image_manager.py
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files with `test_` prefix
- Use descriptive test function names
- Focus on testing core functionality
- Avoid over-testing edge cases

## Code Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Write docstrings for public functions and classes
- Keep functions focused and concise
- Use meaningful variable names

## Dependency Management

### Adding Dependencies

**Think twice before adding external dependencies!** Derpy aims to be a simple tool with minimal dependencies.

If you absolutely must add a dependency:

1. Discuss it in an issue first
2. Ensure it's cross-platform compatible
3. Add it to `pyproject.toml` under `dependencies`
4. Update the documentation

### Development Dependencies

Development dependencies (testing, linting, etc.) can be added to `[project.optional-dependencies]` under the `dev` section in `pyproject.toml`.

## Common Issues

### Import Errors

If you encounter import errors, ensure:

1. Your virtual environment is activated
2. You've installed derpy in editable mode: `pip install -e .`
3. You're running commands from the project root directory

### Homebrew Python Conflicts

If you use Homebrew to manage Python and encounter issues:

1. Always use a virtual environment
2. Specify the Python version explicitly: `python3.11 -m venv venv`
3. Avoid installing packages globally with pip

### Virtual Environment Not Activating

If `source venv/bin/activate` doesn't work:

- Check that you created the venv in the current directory
- Try using the full path: `source /path/to/derpy/venv/bin/activate`
- On Windows, use: `venv\Scripts\activate`

## Release Process

### Publishing a New Version

Derpy uses an automated CI/CD pipeline that triggers on `release/*` branches. Here's how to publish a new version:

#### 1. Update the Version

Use the version management script to bump the version:

```bash
# Show current version
python scripts/version.py show

# Set a specific version
python scripts/version.py set 0.2.1

# Or bump automatically
python scripts/version.py bump patch   # 0.2.0 -> 0.2.1
python scripts/version.py bump minor   # 0.2.0 -> 0.3.0
python scripts/version.py bump major   # 0.2.0 -> 1.0.0
```

This updates both `derpy/__init__.py` and `pyproject.toml`.

#### 2. Create a Release Branch

```bash
# Create and checkout a release branch
git checkout -b release/0.2.1

# Add the version changes
git add derpy/__init__.py pyproject.toml
git commit -m "Bump version to 0.2.1"
```

#### 3. Push the Release Branch

```bash
# Push to trigger CI/CD
git push origin release/0.2.1
```

#### 4. CI/CD Pipeline Runs Automatically

The pipeline will:

1. Run tests across Python 3.10-3.13
2. Build the package (wheel and source distribution)
3. Publish to PyPI
4. Automatically merge the release branch back to main

#### 5. Monitor the Release

- Check the Actions tab on GitHub to monitor progress
- If tests fail, fix issues and push to the same release branch
- Once published to PyPI, the release branch merges to main automatically

### Release Branch Workflow Benefits

- **Main branch stays clean**: Push documentation and script updates to main without triggering releases
- **Controlled releases**: Only `release/*` branches trigger the full CI/CD pipeline
- **Automatic sync**: Successful releases automatically merge back to main
- **Version safety**: CI/CD only runs when you explicitly create a release branch

### Pre-Release Checklist

Before creating a release branch:

- [ ] All tests pass locally: `pytest`
- [ ] Code is formatted: `black derpy tests`
- [ ] No linting issues: `flake8 derpy tests`
- [ ] Type checking passes: `mypy derpy`
- [ ] Documentation is updated
- [ ] CHANGELOG or release notes are prepared (if applicable)
- [ ] Version number follows semantic versioning

## Questions?

If you have questions or need help:

- Open an issue on GitHub
- Check existing issues for similar questions
- Review the project documentation

Thank you for contributing to Derpy!
