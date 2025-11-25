## Tech Stack

- Python 3.10+ (supports 3.10, 3.11, 3.12, 3.13)
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
pytest tests/test_cli.py                 # Specific file
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

Version management:

```bash
python scripts/version.py set 0.3.0      # Set version in all files
python scripts/version.py get            # Get current version
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

## Storage and Authentication

- Registry credentials: `~/.derpy/auth.json` (file permissions: 0600)
- Images stored (daemon mode): `/var/lib/derpy/images/`
- Images stored (direct execution): `~/.derpy/images/`
- Base image cache (daemon mode): `/var/lib/derpy/cache/base-images/`
- Base image cache (direct execution): `~/.derpy/cache/base-images/`

Build isolation is automatically enabled on Linux systems and disabled on macOS/Windows. All settings use sensible defaults without requiring configuration.
