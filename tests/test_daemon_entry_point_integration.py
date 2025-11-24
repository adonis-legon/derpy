"""Integration tests for daemon entry point."""

import subprocess
import sys
import pytest


class TestDaemonEntryPoint:
    """Integration tests for derpyd entry point."""
    
    def test_daemon_help_flag(self):
        """Test that --help flag works."""
        result = subprocess.run(
            [sys.executable, '-m', 'derpy.daemon', '--help'],
            capture_output=True,
            text=True
        )
        
        # Should exit with 0
        assert result.returncode == 0
        
        # Should contain help text
        assert 'Derpy daemon for privileged container operations' in result.stdout
        assert '--socket' in result.stdout
        assert '--group' in result.stdout
        assert '--max-workers' in result.stdout
        assert '--log-level' in result.stdout
    
    def test_daemon_version_flag(self):
        """Test that --version flag works."""
        result = subprocess.run(
            [sys.executable, '-m', 'derpy.daemon', '--version'],
            capture_output=True,
            text=True
        )
        
        # Should exit with 0
        assert result.returncode == 0
        
        # Should contain version
        assert 'derpyd' in result.stdout
        assert '0.2.0' in result.stdout
    
    def test_daemon_invalid_log_level(self):
        """Test that invalid log level is rejected."""
        result = subprocess.run(
            [sys.executable, '-m', 'derpy.daemon', '--log-level', 'INVALID'],
            capture_output=True,
            text=True
        )
        
        # Should exit with non-zero
        assert result.returncode != 0
        
        # Should contain error message
        assert 'invalid choice' in result.stderr.lower()
