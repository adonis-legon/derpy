#!/usr/bin/env python3
"""
Version management script for derpy-tool.

This script manages the version number across the project, updating both
pyproject.toml and derpy/__init__.py to keep them in sync.

Usage:
    python scripts/version.py show              # Show current version
    python scripts/version.py set 0.2.0         # Set new version
    python scripts/version.py bump major        # Bump major version (1.0.0 -> 2.0.0)
    python scripts/version.py bump minor        # Bump minor version (0.1.0 -> 0.2.0)
    python scripts/version.py bump patch        # Bump patch version (0.1.0 -> 0.1.1)
"""

import re
import sys
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def get_current_version() -> str:
    """Get the current version from derpy/__init__.py."""
    init_file = get_project_root() / "derpy" / "__init__.py"
    content = init_file.read_text()
    
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    if not match:
        raise ValueError("Could not find __version__ in derpy/__init__.py")
    
    return match.group(1)


def validate_version(version: str) -> bool:
    """Validate that version follows semantic versioning (X.Y.Z)."""
    pattern = r'^\d+\.\d+\.\d+$'
    return bool(re.match(pattern, version))


def parse_version(version: str) -> tuple:
    """Parse version string into (major, minor, patch) tuple."""
    parts = version.split('.')
    return int(parts[0]), int(parts[1]), int(parts[2])


def bump_version(current: str, part: str) -> str:
    """Bump the specified part of the version."""
    major, minor, patch = parse_version(current)
    
    if part == 'major':
        return f"{major + 1}.0.0"
    elif part == 'minor':
        return f"{major}.{minor + 1}.0"
    elif part == 'patch':
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Invalid version part: {part}. Use 'major', 'minor', or 'patch'")


def update_version(new_version: str) -> None:
    """Update version in both pyproject.toml and derpy/__init__.py."""
    if not validate_version(new_version):
        raise ValueError(
            f"Invalid version format: {new_version}. "
            "Version must follow semantic versioning (X.Y.Z)"
        )
    
    project_root = get_project_root()
    
    # Update derpy/__init__.py
    init_file = project_root / "derpy" / "__init__.py"
    content = init_file.read_text()
    content = re.sub(
        r'__version__\s*=\s*["\'][^"\']+["\']',
        f'__version__ = "{new_version}"',
        content
    )
    init_file.write_text(content)
    print(f"✓ Updated derpy/__init__.py")
    
    # Update pyproject.toml
    pyproject_file = project_root / "pyproject.toml"
    content = pyproject_file.read_text()
    content = re.sub(
        r'version\s*=\s*["\'][^"\']+["\']',
        f'version = "{new_version}"',
        content,
        count=1  # Only replace the first occurrence (in [project] section)
    )
    pyproject_file.write_text(content)
    print(f"✓ Updated pyproject.toml")
    
    print(f"\n✓ Version updated to {new_version}")
    print("\nNext steps:")
    print("  1. Review the changes: git diff")
    print("  2. Commit the changes: git add derpy/__init__.py pyproject.toml")
    print(f"  3. Commit: git commit -m 'Bump version to {new_version}'")
    print("  4. Push and merge to main to trigger CI/CD")


def show_version() -> None:
    """Show the current version."""
    version = get_current_version()
    print(f"Current version: {version}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    try:
        if command == 'show':
            show_version()
        
        elif command == 'set':
            if len(sys.argv) < 3:
                print("Error: 'set' command requires a version argument")
                print("Usage: python scripts/version.py set 0.2.0")
                sys.exit(1)
            
            new_version = sys.argv[2]
            current = get_current_version()
            print(f"Current version: {current}")
            print(f"New version: {new_version}")
            print()
            
            update_version(new_version)
        
        elif command == 'bump':
            if len(sys.argv) < 3:
                print("Error: 'bump' command requires a part argument")
                print("Usage: python scripts/version.py bump [major|minor|patch]")
                sys.exit(1)
            
            part = sys.argv[2].lower()
            if part not in ['major', 'minor', 'patch']:
                print(f"Error: Invalid part '{part}'. Use 'major', 'minor', or 'patch'")
                sys.exit(1)
            
            current = get_current_version()
            new_version = bump_version(current, part)
            
            print(f"Current version: {current}")
            print(f"New version: {new_version} ({part} bump)")
            print()
            
            update_version(new_version)
        
        else:
            print(f"Error: Unknown command '{command}'")
            print(__doc__)
            sys.exit(1)
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
