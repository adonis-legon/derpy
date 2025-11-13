"""Tests for platform utilities."""

import pytest
import os
import platform
from pathlib import Path
import tempfile

from derpy.core.platform import (
    get_platform_info,
    normalize_path,
    ensure_directory,
    get_default_dir_mode,
    get_default_file_mode,
    set_file_permissions,
    make_executable,
    get_config_dir,
    get_cache_dir,
    get_temp_dir,
    is_windows,
    is_unix,
    is_macos,
    is_linux,
    safe_remove,
    get_path_separator,
    join_paths
)


class TestPlatformInfo:
    """Tests for platform information functions."""
    
    def test_get_platform_info(self):
        """Test getting platform information."""
        info = get_platform_info()
        assert isinstance(info, dict)
        assert 'os' in info
        assert 'architecture' in info
        assert 'platform' in info
        assert 'python_version' in info
    
    def test_platform_info_values(self):
        """Test platform info contains valid values."""
        info = get_platform_info()
        assert isinstance(info['os'], str)
        assert len(info['os']) > 0
        assert isinstance(info['architecture'], str)
        assert isinstance(info['python_version'], str)


class TestPathNormalization:
    """Tests for path normalization."""
    
    def test_normalize_path_string(self):
        """Test normalizing string path."""
        path = normalize_path("/tmp/test")
        assert isinstance(path, Path)
        assert path.is_absolute()
    
    def test_normalize_path_object(self):
        """Test normalizing Path object."""
        path = normalize_path(Path("/tmp/test"))
        assert isinstance(path, Path)
        assert path.is_absolute()
    
    def test_normalize_path_with_tilde(self):
        """Test normalizing path with tilde."""
        path = normalize_path("~/test")
        assert isinstance(path, Path)
        assert path.is_absolute()
        assert '~' not in str(path)
    
    def test_normalize_path_relative(self):
        """Test normalizing relative path."""
        path = normalize_path("test/path")
        assert isinstance(path, Path)
        assert path.is_absolute()
    
    def test_normalize_path_resolve_symlinks(self):
        """Test normalizing with symlink resolution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            real_path = Path(tmpdir) / "real"
            real_path.mkdir()
            
            path = normalize_path(real_path, resolve_symlinks=True)
            assert isinstance(path, Path)
            assert path.is_absolute()


class TestDirectoryOperations:
    """Tests for directory operations."""
    
    def test_ensure_directory_creates_dir(self):
        """Test ensure_directory creates directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test"
            result = ensure_directory(test_dir)
            assert test_dir.exists()
            assert test_dir.is_dir()
            assert isinstance(result, Path)
    
    def test_ensure_directory_with_parents(self):
        """Test ensure_directory creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "parent" / "child"
            result = ensure_directory(test_dir, parents=True)
            assert test_dir.exists()
            assert test_dir.is_dir()
    
    def test_ensure_directory_exists_ok(self):
        """Test ensure_directory with existing directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test"
            test_dir.mkdir()
            
            # Should not raise error
            result = ensure_directory(test_dir, exist_ok=True)
            assert test_dir.exists()
    
    def test_get_default_dir_mode(self):
        """Test get_default_dir_mode returns integer."""
        mode = get_default_dir_mode()
        assert isinstance(mode, int)
        assert mode > 0
    
    def test_get_default_file_mode(self):
        """Test get_default_file_mode returns integer."""
        mode = get_default_file_mode()
        assert isinstance(mode, int)
        assert mode > 0


class TestFilePermissions:
    """Tests for file permission operations."""
    
    def test_set_file_permissions(self):
        """Test setting file permissions."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            file_path = Path(f.name)
        
        try:
            # Should not raise error
            set_file_permissions(file_path, 0o644)
            assert file_path.exists()
        finally:
            file_path.unlink()
    
    def test_make_executable(self):
        """Test making file executable."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            file_path = Path(f.name)
        
        try:
            # Should not raise error
            make_executable(file_path)
            assert file_path.exists()
            
            # On Unix, check if executable bit is set
            if not is_windows():
                assert os.access(file_path, os.X_OK)
        finally:
            file_path.unlink()


class TestPlatformDirectories:
    """Tests for platform-specific directories."""
    
    def test_get_config_dir(self):
        """Test getting config directory."""
        config_dir = get_config_dir()
        assert isinstance(config_dir, Path)
        assert 'derpy' in str(config_dir).lower()
    
    def test_get_cache_dir(self):
        """Test getting cache directory."""
        cache_dir = get_cache_dir()
        assert isinstance(cache_dir, Path)
        assert 'derpy' in str(cache_dir).lower()
    
    def test_get_temp_dir(self):
        """Test getting temp directory."""
        temp_dir = get_temp_dir()
        assert isinstance(temp_dir, Path)
        assert 'derpy' in str(temp_dir).lower()


class TestPlatformDetection:
    """Tests for platform detection functions."""
    
    def test_is_windows(self):
        """Test Windows detection."""
        result = is_windows()
        assert isinstance(result, bool)
        # Should match actual platform
        expected = os.name == 'nt' or platform.system().lower() == 'windows'
        assert result == expected
    
    def test_is_unix(self):
        """Test Unix detection."""
        result = is_unix()
        assert isinstance(result, bool)
        expected = os.name == 'posix'
        assert result == expected
    
    def test_is_macos(self):
        """Test macOS detection."""
        result = is_macos()
        assert isinstance(result, bool)
        expected = platform.system().lower() == 'darwin'
        assert result == expected
    
    def test_is_linux(self):
        """Test Linux detection."""
        result = is_linux()
        assert isinstance(result, bool)
        expected = platform.system().lower() == 'linux'
        assert result == expected
    
    def test_platform_detection_exclusive(self):
        """Test that platform detection is mutually exclusive."""
        # At most one should be True (or none for other platforms)
        platforms = [is_windows(), is_macos(), is_linux()]
        true_count = sum(platforms)
        assert true_count <= 1


class TestSafeRemove:
    """Tests for safe_remove function."""
    
    def test_safe_remove_file(self):
        """Test removing a file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            file_path = Path(f.name)
        
        assert file_path.exists()
        result = safe_remove(file_path)
        assert result is True
        assert not file_path.exists()
    
    def test_safe_remove_directory(self):
        """Test removing a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test"
            test_dir.mkdir()
            
            assert test_dir.exists()
            result = safe_remove(test_dir)
            assert result is True
            assert not test_dir.exists()
    
    def test_safe_remove_missing_ok(self):
        """Test removing non-existent path with missing_ok."""
        non_existent = Path("/tmp/nonexistent_derpy_test_12345")
        result = safe_remove(non_existent, missing_ok=True)
        assert result is False
    
    def test_safe_remove_missing_not_ok(self):
        """Test removing non-existent path without missing_ok."""
        non_existent = Path("/tmp/nonexistent_derpy_test_12345")
        with pytest.raises(FileNotFoundError):
            safe_remove(non_existent, missing_ok=False)


class TestPathUtilities:
    """Tests for path utility functions."""
    
    def test_get_path_separator(self):
        """Test getting path separator."""
        separator = get_path_separator()
        assert isinstance(separator, str)
        assert separator == os.sep
    
    def test_join_paths_empty(self):
        """Test joining empty paths."""
        result = join_paths()
        assert isinstance(result, Path)
    
    def test_join_paths_single(self):
        """Test joining single path."""
        result = join_paths("test")
        assert isinstance(result, Path)
        assert "test" in str(result)
    
    def test_join_paths_multiple(self):
        """Test joining multiple paths."""
        result = join_paths("parent", "child", "grandchild")
        assert isinstance(result, Path)
        assert "parent" in str(result)
        assert "child" in str(result)
        assert "grandchild" in str(result)
    
    def test_join_paths_with_path_objects(self):
        """Test joining Path objects."""
        result = join_paths(Path("parent"), Path("child"))
        assert isinstance(result, Path)
        assert "parent" in str(result)
        assert "child" in str(result)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



class TestPlatformDirectoriesExtended:
    """Extended tests for platform directories."""
    
    def test_config_dir_contains_derpy(self):
        """Test config dir contains derpy."""
        config_dir = get_config_dir()
        assert 'derpy' in str(config_dir).lower()
    
    def test_cache_dir_contains_derpy(self):
        """Test cache dir contains derpy."""
        cache_dir = get_cache_dir()
        assert 'derpy' in str(cache_dir).lower()
    
    def test_temp_dir_contains_derpy(self):
        """Test temp dir contains derpy."""
        temp_dir = get_temp_dir()
        assert 'derpy' in str(temp_dir).lower()
    
    def test_config_dir_is_absolute(self):
        """Test config dir is absolute path."""
        config_dir = get_config_dir()
        assert config_dir.is_absolute()
    
    def test_cache_dir_is_absolute(self):
        """Test cache dir is absolute path."""
        cache_dir = get_cache_dir()
        assert cache_dir.is_absolute()


class TestNormalizePathExtended:
    """Extended tests for normalize_path."""
    
    def test_normalize_path_absolute(self):
        """Test normalizing absolute path."""
        path = normalize_path("/tmp/test")
        assert path.is_absolute()
    
    def test_normalize_path_returns_path_object(self):
        """Test normalize_path returns Path object."""
        path = normalize_path("test")
        assert isinstance(path, Path)
    
    def test_normalize_path_with_path_object(self):
        """Test normalize_path with Path object input."""
        input_path = Path("test")
        path = normalize_path(input_path)
        assert isinstance(path, Path)


class TestEnsureDirectoryExtended:
    """Extended tests for ensure_directory."""
    
    def test_ensure_directory_returns_path(self):
        """Test ensure_directory returns Path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test"
            result = ensure_directory(test_dir)
            assert isinstance(result, Path)
    
    def test_ensure_directory_creates_nested(self):
        """Test ensure_directory creates nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "a" / "b" / "c"
            result = ensure_directory(test_dir, parents=True)
            assert test_dir.exists()
            assert test_dir.is_dir()


class TestJoinPathsExtended:
    """Extended tests for join_paths."""
    
    def test_join_paths_single_string(self):
        """Test joining single string path."""
        result = join_paths("test")
        assert "test" in str(result)
    
    def test_join_paths_multiple_strings(self):
        """Test joining multiple string paths."""
        result = join_paths("a", "b", "c")
        assert "a" in str(result)
        assert "b" in str(result)
        assert "c" in str(result)
    
    def test_join_paths_mixed_types(self):
        """Test joining mixed Path and string."""
        result = join_paths(Path("a"), "b", Path("c"))
        assert isinstance(result, Path)


class TestSafeRemoveExtended:
    """Extended tests for safe_remove."""
    
    def test_safe_remove_returns_true_on_success(self):
        """Test safe_remove returns True on success."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            file_path = Path(f.name)
        
        result = safe_remove(file_path)
        assert result is True
        assert not file_path.exists()
    
    def test_safe_remove_returns_false_on_missing(self):
        """Test safe_remove returns False for missing file."""
        non_existent = Path("/tmp/nonexistent_derpy_test_99999")
        result = safe_remove(non_existent, missing_ok=True)
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



class TestPlatformInfoExtended:
    """Extended tests for platform info."""
    
    def test_platform_info_has_all_keys(self):
        """Test platform info has all required keys."""
        info = get_platform_info()
        
        required_keys = ['os', 'architecture', 'platform', 'python_version']
        for key in required_keys:
            assert key in info
    
    def test_platform_info_values_not_empty(self):
        """Test platform info values are not empty."""
        info = get_platform_info()
        
        assert len(info['os']) > 0
        assert len(info['architecture']) > 0
        assert len(info['platform']) > 0
        assert len(info['python_version']) > 0
    
    def test_platform_info_python_version_format(self):
        """Test Python version has expected format."""
        info = get_platform_info()
        
        # Should contain dots (e.g., "3.11.0")
        assert '.' in info['python_version']


class TestPathSeparator:
    """Tests for path separator."""
    
    def test_path_separator_is_string(self):
        """Test path separator is a string."""
        sep = get_path_separator()
        assert isinstance(sep, str)
    
    def test_path_separator_length(self):
        """Test path separator has length 1."""
        sep = get_path_separator()
        assert len(sep) == 1
    
    def test_path_separator_matches_os(self):
        """Test path separator matches OS."""
        import os
        sep = get_path_separator()
        assert sep == os.sep


class TestDefaultModes:
    """Tests for default permission modes."""
    
    def test_default_dir_mode_is_int(self):
        """Test default dir mode is integer."""
        mode = get_default_dir_mode()
        assert isinstance(mode, int)
    
    def test_default_file_mode_is_int(self):
        """Test default file mode is integer."""
        mode = get_default_file_mode()
        assert isinstance(mode, int)
    
    def test_default_modes_are_positive(self):
        """Test default modes are positive."""
        dir_mode = get_default_dir_mode()
        file_mode = get_default_file_mode()
        
        assert dir_mode > 0
        assert file_mode > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



class TestFilePermissionsExtended:
    """Extended tests for file permissions."""
    
    def test_set_file_permissions_on_file(self):
        """Test setting permissions on a file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            file_path = Path(f.name)
        
        try:
            # Should not raise error
            set_file_permissions(file_path, 0o644)
            assert file_path.exists()
        finally:
            file_path.unlink()
    
    def test_make_executable_on_file(self):
        """Test making file executable."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            file_path = Path(f.name)
            f.write(b"#!/bin/bash\necho hello")
        
        try:
            make_executable(file_path)
            assert file_path.exists()
        finally:
            file_path.unlink()


class TestDirectoryCreation:
    """Test directory creation variations."""
    
    def test_ensure_directory_without_parents(self):
        """Test ensure_directory without parents flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir) / "parent"
            parent.mkdir()
            
            child = parent / "child"
            result = ensure_directory(child, parents=False)
            
            assert result.exists()
    
    def test_ensure_directory_already_exists(self):
        """Test ensure_directory on existing directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "existing"
            test_dir.mkdir()
            
            # Should not raise error
            result = ensure_directory(test_dir, exist_ok=True)
            assert result.exists()


class TestSafeRemoveVariations:
    """Test safe_remove with various scenarios."""
    
    def test_safe_remove_directory_with_contents(self):
        """Test removing directory with contents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test"
            test_dir.mkdir()
            
            # Add some files
            (test_dir / "file1.txt").write_text("content1")
            (test_dir / "file2.txt").write_text("content2")
            
            result = safe_remove(test_dir)
            assert result is True
            assert not test_dir.exists()
    
    def test_safe_remove_nested_directories(self):
        """Test removing nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "parent" / "child" / "grandchild"
            test_dir.mkdir(parents=True)
            
            parent = Path(tmpdir) / "parent"
            result = safe_remove(parent)
            assert result is True
            assert not parent.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
