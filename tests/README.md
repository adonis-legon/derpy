# Derpy Container Tool - Tests

This directory contains the test suite for the derpy container tool.

## Test Structure

- `test_oci_models.py` - Tests for OCI specification data models
- `test_oci_layout.py` - Tests for OCI layout manager
- `test_dockerfile_parser.py` - Tests for Dockerfile parsing
- `test_config.py` - Tests for configuration management
- `test_storage_manager.py` - Tests for image storage manager
- `test_build_engine.py` - Tests for build engine components

## Running Tests

### Run all tests:

```bash
# Using pytest directly
pytest tests/ -v

# Using the test runner script
python run_tests.py
```

### Run specific test file:

```bash
pytest tests/test_oci_models.py -v
```

### Run specific test class:

```bash
pytest tests/test_oci_models.py::TestDescriptor -v
```

### Run specific test method:

```bash
pytest tests/test_oci_models.py::TestDescriptor::test_create_descriptor -v
```

### Run with coverage:

```bash
pytest tests/ --cov=derpy --cov-report=html
```

## Test Requirements

Make sure you have pytest installed:

```bash
pip install pytest pytest-cov
```

## Writing Tests

When adding new tests:

1. Create a new test file with the prefix `test_`
2. Organize tests into classes with the prefix `Test`
3. Name test methods with the prefix `test_`
4. Use descriptive names that explain what is being tested
5. Include docstrings for test classes and methods
6. Use fixtures for common setup/teardown operations
7. Keep tests focused and independent

## Test Coverage

The test suite covers:

- OCI specification compliance
- Dockerfile parsing and validation
- Configuration management
- Image storage and retrieval
- Build engine functionality
- Layer creation and management
