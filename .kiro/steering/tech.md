## Tech Stack

- Python 3.8+ (supports 3.8, 3.9, 3.10, 3.11, 3.12)
- Build system: setuptools with pyproject.toml
- CLI framework: click 8.0+
- Configuration: PyYAML 6.0+
- HTTP client: requests 2.28+

## Development Dependencies

- Testing: pytest 7.0+, pytest-cov 4.0+
- Code formatting: black 23.0+ (line length: 88)
- Linting: flake8 6.0+
- Type checking: mypy 1.0+

## Common Commands

Development setup (always use virtual environment):

```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -e .
pip install -e ".[dev]"
```

Testing:

```bash
pytest                                    # Run all tests
pytest --cov=derpy --cov-report=html     # With coverage
pytest tests/test_config.py              # Specific file
pytest -m unit                           # Unit tests only
pytest -m integration                    # Integration tests only
```

Code quality:

```bash
black derpy tests                        # Format code
black --check derpy tests                # Check formatting
flake8 derpy tests                       # Lint
mypy derpy                               # Type check
```

Running derpy:

```bash
derpy --version
derpy build . -f Dockerfile -t myapp:latest
derpy ls
derpy push myapp:latest

# Build with isolation (Linux only, requires sudo)
sudo derpy build . -f Dockerfile -t myapp:latest
```

Authentication:

```bash
# Login to Docker Hub
derpy login

# Login to custom registry
derpy login registry.example.com
derpy login -u myuser -p mypass registry.example.com

# Login with password from stdin
echo "mypass" | derpy login --password-stdin registry.example.com

# Logout from registry
derpy logout
derpy logout registry.example.com

# Build with private base image (uses stored credentials)
derpy build . -f Dockerfile -t myapp:latest

# Push to authenticated registry (uses stored credentials)
derpy push registry.example.com/myapp:latest
```

## Configuration

- User config: `~/.derpy/config.yaml`
- Registry credentials: `~/.derpy/auth.json` (file permissions: 0600)
- Images stored: `~/.derpy/images/` (configurable)
- Base image cache: `~/.derpy/cache/base-images/` (configurable)
- Config managed via: `derpy config show/set` commands

Build isolation settings:

```bash
derpy config set build_settings.enable_isolation true
derpy config set build_settings.base_image_cache_dir /custom/cache/path
derpy config set build_settings.chroot_timeout 600
```
