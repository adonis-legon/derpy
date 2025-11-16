"""Platform-specific utilities for cross-platform compatibility.

This module provides utilities for handling platform-specific operations
including path handling, directory permissions, and file operations.
"""

import os
import stat
from pathlib import Path
from typing import Optional, Union
import platform


def get_platform_info() -> dict:
    """Get current platform information.
    
    Returns:
        Dictionary with platform details including os, architecture, and system
    """
    return {
        "os": platform.system().lower(),
        "architecture": platform.machine().lower(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
    }


def normalize_path(path: Union[str, Path], resolve_symlinks: bool = False) -> Path:
    """Normalize a path for the current platform.
    
    Handles:
    - Tilde expansion (~)
    - Environment variable expansion
    - Path separator normalization
    - Absolute path resolution
    
    Args:
        path: Path string or Path object to normalize
        resolve_symlinks: If True, resolve symbolic links (default: False)
    
    Returns:
        Normalized Path object
    """
    if isinstance(path, str):
        path = Path(path)
    
    # Expand user home directory
    path = path.expanduser()
    
    # Expand environment variables if path is a string
    path_str = str(path)
    if "$" in path_str or "%" in path_str:
        path = Path(os.path.expandvars(path_str))
    
    # Convert to absolute path
    if resolve_symlinks:
        # Resolve symlinks and make absolute
        try:
            path = path.resolve()
        except (OSError, RuntimeError):
            # If resolve fails (e.g., path doesn't exist), just make it absolute
            path = path.absolute()
    else:
        # Just make absolute without resolving symlinks
        if not path.is_absolute():
            path = path.absolute()
    
    return path


def ensure_directory(
    path: Path,
    mode: Optional[int] = None,
    parents: bool = True,
    exist_ok: bool = True
) -> Path:
    """Ensure a directory exists with appropriate permissions.
    
    Creates the directory if it doesn't exist, with platform-appropriate
    permissions.
    
    Args:
        path: Directory path to create
        mode: Permission mode (Unix-style). If None, uses platform defaults
        parents: Create parent directories if needed
        exist_ok: Don't raise error if directory already exists
    
    Returns:
        Normalized path to the directory
    
    Raises:
        OSError: If directory creation fails
    """
    path = normalize_path(path)
    
    # Create directory
    path.mkdir(mode=mode or get_default_dir_mode(), parents=parents, exist_ok=exist_ok)
    
    # On Unix-like systems, explicitly set permissions if mode was provided
    if mode is not None and os.name != 'nt':
        try:
            os.chmod(path, mode)
        except OSError:
            # Permission change might fail, but directory exists
            pass
    
    return path


def get_default_dir_mode() -> int:
    """Get default directory permission mode for the platform.
    
    Returns:
        Permission mode as integer (Unix-style)
    """
    if os.name == 'nt':
        # Windows doesn't use Unix permissions
        # Return a value that mkdir will ignore
        return 0o777
    else:
        # Unix-like: rwxr-xr-x (755)
        return 0o755


def get_default_file_mode() -> int:
    """Get default file permission mode for the platform.
    
    Returns:
        Permission mode as integer (Unix-style)
    """
    if os.name == 'nt':
        # Windows doesn't use Unix permissions
        return 0o666
    else:
        # Unix-like: rw-r--r-- (644)
        return 0o644


def set_file_permissions(path: Path, mode: int) -> None:
    """Set file permissions in a platform-appropriate way.
    
    On Windows, this is a no-op as Windows uses a different permission model.
    On Unix-like systems, sets the standard Unix permissions.
    
    Args:
        path: Path to file or directory
        mode: Permission mode (Unix-style)
    """
    if os.name != 'nt':
        try:
            os.chmod(path, mode)
        except OSError:
            # Silently fail if we can't set permissions
            pass


def make_executable(path: Path) -> None:
    """Make a file executable in a platform-appropriate way.
    
    On Unix-like systems, adds execute permission.
    On Windows, this is a no-op as executability is determined by extension.
    
    Args:
        path: Path to file to make executable
    """
    if os.name != 'nt':
        try:
            current_mode = path.stat().st_mode
            # Add execute permission for owner, group, and others
            new_mode = current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            os.chmod(path, new_mode)
        except OSError:
            # Silently fail if we can't set permissions
            pass


def get_config_dir() -> Path:
    """Get the platform-appropriate configuration directory.
    
    Returns:
        Path to configuration directory:
        - Linux/macOS: ~/.derpy
        - Windows: %USERPROFILE%/.derpy or %APPDATA%/derpy
    """
    if os.name == 'nt':
        # Windows: prefer APPDATA, fallback to USERPROFILE
        appdata = os.getenv('APPDATA')
        if appdata:
            return Path(appdata) / 'derpy'
        else:
            return Path.home() / '.derpy'
    else:
        # Unix-like: use home directory
        return Path.home() / '.derpy'


def get_cache_dir() -> Path:
    """Get the platform-appropriate cache directory.
    
    Returns:
        Path to cache directory:
        - Linux: ~/.cache/derpy
        - macOS: ~/Library/Caches/derpy
        - Windows: %LOCALAPPDATA%/derpy/cache
    """
    system = platform.system().lower()
    
    if system == 'darwin':
        # macOS
        return Path.home() / 'Library' / 'Caches' / 'derpy'
    elif system == 'windows' or os.name == 'nt':
        # Windows
        localappdata = os.getenv('LOCALAPPDATA')
        if localappdata:
            return Path(localappdata) / 'derpy' / 'cache'
        else:
            return Path.home() / '.derpy' / 'cache'
    else:
        # Linux and other Unix-like
        xdg_cache = os.getenv('XDG_CACHE_HOME')
        if xdg_cache:
            return Path(xdg_cache) / 'derpy'
        else:
            return Path.home() / '.cache' / 'derpy'


def get_temp_dir() -> Path:
    """Get a platform-appropriate temporary directory for derpy.
    
    Returns:
        Path to temporary directory
    """
    import tempfile
    system_temp = Path(tempfile.gettempdir())
    return system_temp / 'derpy'


def is_windows() -> bool:
    """Check if running on Windows.
    
    Returns:
        True if on Windows, False otherwise
    """
    return os.name == 'nt' or platform.system().lower() == 'windows'


def is_unix() -> bool:
    """Check if running on a Unix-like system (Linux, macOS, BSD, etc.).
    
    Returns:
        True if on Unix-like system, False otherwise
    """
    return os.name == 'posix'


def is_macos() -> bool:
    """Check if running on macOS.
    
    Returns:
        True if on macOS, False otherwise
    """
    return platform.system().lower() == 'darwin'


def is_linux() -> bool:
    """Check if running on Linux.
    
    Returns:
        True if on Linux, False otherwise
    """
    return platform.system().lower() == 'linux'


def safe_remove(path: Path, missing_ok: bool = True) -> bool:
    """Safely remove a file or directory.
    
    Handles platform-specific quirks and permission issues.
    
    Args:
        path: Path to remove
        missing_ok: Don't raise error if path doesn't exist
    
    Returns:
        True if removed, False if didn't exist (when missing_ok=True)
    
    Raises:
        OSError: If removal fails and missing_ok=False
    """
    if not path.exists():
        if missing_ok:
            return False
        else:
            raise FileNotFoundError(f"Path does not exist: {path}")
    
    try:
        if path.is_dir():
            import shutil
            # On Windows, might need to handle read-only files
            if is_windows():
                def handle_remove_readonly(func, path, exc):
                    """Error handler for Windows readonly files."""
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                
                shutil.rmtree(path, onerror=handle_remove_readonly)
            else:
                shutil.rmtree(path)
        else:
            # On Windows, might need to clear readonly flag
            if is_windows() and not os.access(path, os.W_OK):
                os.chmod(path, stat.S_IWRITE)
            path.unlink()
        return True
    except OSError as e:
        if not missing_ok:
            raise
        return False


def get_path_separator() -> str:
    """Get the platform-specific path separator.
    
    Returns:
        Path separator character ('/' on Unix, '\\' on Windows)
    """
    return os.sep


def join_paths(*parts: Union[str, Path]) -> Path:
    """Join path components in a platform-appropriate way.
    
    Args:
        *parts: Path components to join
    
    Returns:
        Joined Path object
    """
    if not parts:
        return Path()
    
    result = Path(parts[0])
    for part in parts[1:]:
        result = result / part
    
    return result
