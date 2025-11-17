# Scripts

This directory contains utility scripts for managing the derpy-tool project.

## version.py

Manages the version number across the project, keeping `pyproject.toml` and `derpy/__init__.py` in sync.

### Usage

**Show current version:**

```bash
python scripts/version.py show
```

**Set a specific version:**

```bash
python scripts/version.py set 0.2.0
```

**Bump version automatically:**

```bash
# Bump patch version (0.1.0 -> 0.1.1)
python scripts/version.py bump patch

# Bump minor version (0.1.0 -> 0.2.0)
python scripts/version.py bump minor

# Bump major version (0.1.0 -> 1.0.0)
python scripts/version.py bump major
```

### Workflow for releasing a new version

1. **Update the version:**

   ```bash
   python scripts/version.py bump patch
   ```

2. **Review the changes:**

   ```bash
   git diff derpy/__init__.py pyproject.toml
   ```

3. **Commit the version bump:**

   ```bash
   git add derpy/__init__.py pyproject.toml
   git commit -m "Bump version to 0.1.1"
   ```

4. **Push to your feature branch:**

   ```bash
   git push origin feature/your-branch
   ```

5. **Merge to main:**
   - Create a pull request
   - Once merged, the CI/CD pipeline will automatically build and publish to PyPI

### Version numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** version (X.0.0): Incompatible API changes
- **MINOR** version (0.X.0): New functionality in a backward-compatible manner
- **PATCH** version (0.0.X): Backward-compatible bug fixes

### Examples

```bash
# For a bug fix release
python scripts/version.py bump patch  # 0.1.0 -> 0.1.1

# For a new feature release
python scripts/version.py bump minor  # 0.1.1 -> 0.2.0

# For a breaking change release
python scripts/version.py bump major  # 0.2.0 -> 1.0.0

# For a specific version (e.g., release candidate)
python scripts/version.py set 1.0.0-rc1  # Note: PyPI may not accept pre-release versions
```

### Notes

- The script validates that versions follow the X.Y.Z format
- Both `pyproject.toml` and `derpy/__init__.py` are updated automatically
- Always commit version changes before merging to main
- The CI/CD pipeline only publishes when code is merged to main
