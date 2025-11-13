"""Tests for IsolationExecutor."""

import pytest
import platform
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch, MagicMock
import subprocess

from derpy.build.isolation import IsolationExecutor
from derpy.build.models import ExecutionResult
from derpy.core.exceptions import IsolationError, PlatformNotSupportedError


class TestLinuxEnvironmentValidation:
    """Tests for Linux environment validation."""
    
    def test_validate_on_linux_as_root(self):
        """Test validation passes on Linux as root."""
        executor = IsolationExecutor()
        
        with patch('platform.system', return_value='Linux'):
            with patch('os.geteuid', return_value=0):
                # Should not raise
                executor.validate_linux_environment()
    
    def test_validate_on_non_linux(self):
        """Test validation fails on non-Linux platforms."""
        executor = IsolationExecutor()
        
        with patch('platform.system', return_value='Darwin'):
            with pytest.raises(PlatformNotSupportedError, match="Linux"):
                executor.validate_linux_environment()
    
    def test_validate_on_windows(self):
        """Test validation fails on Windows."""
        executor = IsolationExecutor()
        
        with patch('platform.system', return_value='Windows'):
            with pytest.raises(PlatformNotSupportedError, match="Linux"):
                executor.validate_linux_environment()
    
    def test_validate_without_root_no_capability(self):
        """Test validation fails without root and no capability."""
        executor = IsolationExecutor()
        
        with patch('platform.system', return_value='Linux'):
            with patch('os.geteuid', return_value=1000):
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value = Mock(returncode=0, stdout="current: =")
                    
                    with pytest.raises(IsolationError, match="Insufficient permissions"):
                        executor.validate_linux_environment()
    
    def test_validate_with_capability(self):
        """Test validation passes with CAP_SYS_CHROOT capability."""
        executor = IsolationExecutor()
        
        with patch('platform.system', return_value='Linux'):
            with patch('os.geteuid', return_value=1000):
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value = Mock(
                        returncode=0,
                        stdout="current: =ep cap_sys_chroot+ep"
                    )
                    
                    # Should not raise
                    executor.validate_linux_environment()


class TestChrootSetup:
    """Tests for chroot environment setup."""
    
    def test_setup_creates_mount_points(self):
        """Test that setup creates necessary mount points."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir) / "rootfs"
            rootfs.mkdir()
            (rootfs / "bin").mkdir()
            (rootfs / "bin" / "sh").touch()
            
            executor = IsolationExecutor()
            
            with patch('subprocess.run') as mock_run:
                with patch.object(executor, '_is_mounted', return_value=False):
                    mock_run.return_value = Mock(returncode=0)
                    
                    executor.setup_chroot_environment(rootfs)
                    
                    # Verify mount points were created
                    assert (rootfs / "proc").exists()
                    assert (rootfs / "sys").exists()
                    assert (rootfs / "dev").exists()
    
    def test_setup_copies_resolv_conf(self):
        """Test that setup copies resolv.conf."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir) / "rootfs"
            rootfs.mkdir()
            (rootfs / "bin").mkdir()
            (rootfs / "bin" / "sh").touch()
            (rootfs / "etc").mkdir()
            
            executor = IsolationExecutor()
            
            with patch('subprocess.run') as mock_run:
                with patch.object(executor, '_is_mounted', return_value=False):
                    mock_run.return_value = Mock(returncode=0)
                    
                    with patch('pathlib.Path.exists', return_value=True):
                        with patch('shutil.copy2') as mock_copy:
                            executor.setup_chroot_environment(rootfs)
                            
                            # Verify resolv.conf was copied
                            assert mock_copy.called
    
    def test_setup_fails_without_shell(self):
        """Test that setup fails if shell doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir) / "rootfs"
            rootfs.mkdir()
            
            executor = IsolationExecutor()
            
            # Mock subprocess to avoid actual mount attempts
            with patch('subprocess.run') as mock_run:
                with patch.object(executor, '_is_mounted', return_value=False):
                    mock_run.return_value = Mock(returncode=0)
                    
                    with pytest.raises(IsolationError, match="Shell not found"):
                        executor.setup_chroot_environment(rootfs)
    
    def test_setup_skips_already_mounted(self):
        """Test that setup skips already mounted filesystems."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir) / "rootfs"
            rootfs.mkdir()
            (rootfs / "bin").mkdir()
            (rootfs / "bin" / "sh").touch()
            
            executor = IsolationExecutor()
            
            with patch('subprocess.run') as mock_run:
                with patch.object(executor, '_is_mounted', return_value=True):
                    executor.setup_chroot_environment(rootfs)
                    
                    # Mount commands should not be called
                    assert not mock_run.called


class TestChrootExecution:
    """Tests for command execution in chroot."""
    
    def test_execute_successful_command(self):
        """Test executing a successful command."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir) / "rootfs"
            rootfs.mkdir()
            (rootfs / "bin").mkdir()
            (rootfs / "bin" / "sh").touch()
            
            executor = IsolationExecutor()
            
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(
                    returncode=0,
                    stdout="output",
                    stderr=""
                )
                
                result = executor.execute_in_chroot(rootfs, "echo hello")
                
                assert result.is_success()
                assert result.exit_code == 0
                assert result.stdout == "output"
                assert mock_run.called
    
    def test_execute_failed_command(self):
        """Test executing a failed command."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir) / "rootfs"
            rootfs.mkdir()
            (rootfs / "bin").mkdir()
            (rootfs / "bin" / "sh").touch()
            
            executor = IsolationExecutor()
            
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(
                    returncode=1,
                    stdout="",
                    stderr="error"
                )
                
                result = executor.execute_in_chroot(rootfs, "false")
                
                assert result.is_failure()
                assert result.exit_code == 1
                assert result.stderr == "error"
    
    def test_execute_with_timeout(self):
        """Test command execution with timeout."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir) / "rootfs"
            rootfs.mkdir()
            (rootfs / "bin").mkdir()
            (rootfs / "bin" / "sh").touch()
            
            executor = IsolationExecutor()
            
            with patch('subprocess.run') as mock_run:
                timeout_exc = subprocess.TimeoutExpired(
                    cmd="sleep 100",
                    timeout=5
                )
                timeout_exc.stdout = b""
                timeout_exc.stderr = b""
                mock_run.side_effect = timeout_exc
                
                result = executor.execute_in_chroot(rootfs, "sleep 100", timeout=5)
                
                assert result.is_failure()
                assert result.exit_code == 124  # Timeout exit code
                assert "timed out" in result.stderr
    
    def test_execute_with_custom_shell(self):
        """Test executing with custom shell."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir) / "rootfs"
            rootfs.mkdir()
            (rootfs / "bin").mkdir()
            (rootfs / "bin" / "bash").touch()
            
            executor = IsolationExecutor()
            
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
                
                executor.execute_in_chroot(rootfs, "echo test", shell="/bin/bash")
                
                # Verify bash was used
                call_args = mock_run.call_args[0][0]
                assert "/bin/bash" in call_args
    
    def test_execute_fails_with_missing_shell(self):
        """Test execution fails if shell doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir) / "rootfs"
            rootfs.mkdir()
            
            executor = IsolationExecutor()
            
            with pytest.raises(IsolationError, match="Shell not found"):
                executor.execute_in_chroot(rootfs, "echo test")
    
    def test_execute_fails_with_nonexistent_rootfs(self):
        """Test execution fails if rootfs doesn't exist."""
        executor = IsolationExecutor()
        
        with pytest.raises(IsolationError, match="does not exist"):
            executor.execute_in_chroot(Path("/nonexistent"), "echo test")


class TestChrootCleanup:
    """Tests for chroot environment cleanup."""
    
    def test_cleanup_unmounts_filesystems(self):
        """Test that cleanup unmounts filesystems."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir) / "rootfs"
            rootfs.mkdir()
            (rootfs / "proc").mkdir()
            (rootfs / "sys").mkdir()
            (rootfs / "dev").mkdir()
            
            executor = IsolationExecutor()
            
            with patch('subprocess.run') as mock_run:
                with patch.object(executor, '_is_mounted', return_value=True):
                    mock_run.return_value = Mock(returncode=0)
                    
                    executor.cleanup_chroot_environment(rootfs)
                    
                    # Verify unmount was called
                    assert mock_run.called
                    # Should be called 3 times (dev, sys, proc)
                    assert mock_run.call_count == 3
    
    def test_cleanup_handles_unmount_failure(self):
        """Test that cleanup handles unmount failures gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir) / "rootfs"
            rootfs.mkdir()
            (rootfs / "proc").mkdir()
            
            executor = IsolationExecutor()
            
            with patch('subprocess.run') as mock_run:
                with patch.object(executor, '_is_mounted', return_value=True):
                    mock_run.side_effect = subprocess.CalledProcessError(1, "umount")
                    
                    # Should not raise, just log warning
                    executor.cleanup_chroot_environment(rootfs)
    
    def test_cleanup_restores_resolv_conf(self):
        """Test that cleanup restores original resolv.conf."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir) / "rootfs"
            rootfs.mkdir()
            (rootfs / "etc").mkdir()
            (rootfs / "etc" / "resolv.conf").write_text("modified")
            (rootfs / "etc" / "resolv.conf.derpy-backup").write_text("original")
            
            executor = IsolationExecutor()
            
            with patch.object(executor, '_is_mounted', return_value=False):
                executor.cleanup_chroot_environment(rootfs)
                
                # Verify backup was restored
                assert (rootfs / "etc" / "resolv.conf").read_text() == "original"
                assert not (rootfs / "etc" / "resolv.conf.derpy-backup").exists()
    
    def test_cleanup_handles_nonexistent_rootfs(self):
        """Test that cleanup handles nonexistent rootfs gracefully."""
        executor = IsolationExecutor()
        
        # Should not raise
        executor.cleanup_chroot_environment(Path("/nonexistent"))


class TestExecutionResult:
    """Tests for ExecutionResult model."""
    
    def test_execution_result_success(self):
        """Test ExecutionResult for successful execution."""
        result = ExecutionResult(
            exit_code=0,
            stdout="output",
            stderr="",
            duration=1.5,
            command="echo test"
        )
        
        assert result.is_success()
        assert not result.is_failure()
        assert result.exit_code == 0
    
    def test_execution_result_failure(self):
        """Test ExecutionResult for failed execution."""
        result = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="error",
            duration=0.5,
            command="false"
        )
        
        assert result.is_failure()
        assert not result.is_success()
        assert result.exit_code == 1
    
    def test_execution_result_get_output(self):
        """Test getting combined output."""
        result = ExecutionResult(
            exit_code=0,
            stdout="out",
            stderr="err",
            duration=1.0
        )
        
        output = result.get_output()
        assert "out" in output
        assert "err" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
