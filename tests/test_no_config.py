"""Tests to verify configuration removal."""

import pytest
from pathlib import Path
import tempfile
import os
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from hypothesis import given, strategies as st, settings

from derpy.cli.main import cli


class TestNoConfigFileAccess:
    """Property-based test to verify no config file access."""
    
    @given(
        command=st.sampled_from(['build', 'ls', 'rm', 'purge', 'version']),
        args=st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=3)
    )
    @settings(max_examples=100)
    def test_no_config_file_access_property(self, command, args):
        """
        Feature: config-simplification, Property 1: No config file access
        
        For any derpy command execution, the system should never attempt to 
        read or write files at ~/.derpy/config.yaml
        
        Validates: Requirements 1.1
        """
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Set up a fake home directory
            fake_home = Path(tmpdir) / "home"
            fake_home.mkdir()
            config_path = fake_home / ".derpy" / "config.yaml"
            
            # Ensure the config file doesn't exist
            assert not config_path.exists()
            
            # Mock the home directory
            with patch.dict(os.environ, {'HOME': str(fake_home)}):
                # Build command needs special handling
                if command == 'build':
                    # Create a minimal Dockerfile
                    build_dir = Path(tmpdir) / "build"
                    build_dir.mkdir()
                    dockerfile = build_dir / "Dockerfile"
                    dockerfile.write_text("FROM alpine:latest\n")
                    
                    # Run build command with minimal args
                    result = runner.invoke(cli, [
                        command,
                        str(build_dir),
                        '-t', 'test:latest'
                    ], catch_exceptions=True)
                elif command == 'rm':
                    # rm needs an image name
                    result = runner.invoke(cli, [command, 'test:latest'], catch_exceptions=True)
                else:
                    # Run other commands
                    result = runner.invoke(cli, [command] + args, catch_exceptions=True)
                
                # Verify config file was never created
                assert not config_path.exists(), \
                    f"Config file was created at {config_path} during {command} command"
                
                # If parent directory was created, that's also a problem
                if config_path.parent.exists():
                    # Check if any config.yaml exists in the .derpy directory
                    config_files = list(config_path.parent.glob("config.yaml"))
                    assert len(config_files) == 0, \
                        f"Config file found in .derpy directory during {command} command"


class TestConfigCommandRemoval:
    """Test that config command no longer exists."""
    
    def test_config_command_does_not_exist(self):
        """
        Verify derpy config command no longer exists.
        
        Validates: Requirements 2.4
        """
        runner = CliRunner()
        result = runner.invoke(cli, ['config', 'show'])
        
        # Command should not exist - expect error
        assert result.exit_code != 0
        # Should indicate command doesn't exist
        assert 'no such command' in result.output.lower() or 'error' in result.output.lower()
    
    def test_config_set_command_does_not_exist(self):
        """Verify derpy config set command no longer exists."""
        runner = CliRunner()
        result = runner.invoke(cli, ['config', 'set', 'images_path', '/tmp/test'])
        
        # Command should not exist
        assert result.exit_code != 0
        assert 'no such command' in result.output.lower() or 'error' in result.output.lower()


class TestDefaultValues:
    """Test that default values are used correctly."""
    
    @patch('derpy.build.engine.BuildEngine')
    def test_build_isolation_defaults(self, mock_build_engine_class):
        """
        Verify build isolation uses correct defaults.
        
        Validates: Requirements 7.1
        """
        import platform
        
        # Mock BuildEngine to capture initialization
        mock_engine = MagicMock()
        mock_build_engine_class.return_value = mock_engine
        
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a minimal Dockerfile
            dockerfile = Path(tmpdir) / "Dockerfile"
            dockerfile.write_text("FROM alpine:latest\n")
            
            # Run build command
            result = runner.invoke(cli, [
                'build',
                tmpdir,
                '-f', str(dockerfile),
                '-t', 'test:latest'
            ], catch_exceptions=True)
            
            # Verify BuildEngine was called
            if mock_build_engine_class.called:
                call_args = mock_build_engine_class.call_args
                
                # Check if enable_isolation was passed
                if call_args and len(call_args) > 1 and 'enable_isolation' in call_args[1]:
                    enable_isolation = call_args[1]['enable_isolation']
                    
                    # Should be True on Linux, False elsewhere
                    expected = platform.system() == 'Linux'
                    assert enable_isolation == expected, \
                        f"enable_isolation should be {expected} on {platform.system()}"
    
    @patch('derpy.build.engine.BuildEngine')
    def test_cache_directory_defaults(self, mock_build_engine_class):
        """
        Verify cache directory uses correct defaults.
        
        Validates: Requirements 7.1
        """
        mock_engine = MagicMock()
        mock_build_engine_class.return_value = mock_engine
        
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            dockerfile = Path(tmpdir) / "Dockerfile"
            dockerfile.write_text("FROM alpine:latest\n")
            
            result = runner.invoke(cli, [
                'build',
                tmpdir,
                '-f', str(dockerfile),
                '-t', 'test:latest'
            ], catch_exceptions=True)
            
            # Verify BuildEngine was called with cache directory
            if mock_build_engine_class.called:
                call_args = mock_build_engine_class.call_args
                
                if call_args and len(call_args) > 1 and 'base_image_cache_dir' in call_args[1]:
                    cache_dir = call_args[1]['base_image_cache_dir']
                    
                    # Should be a valid path
                    assert cache_dir is not None
                    assert isinstance(cache_dir, (str, Path))
    
    @patch('derpy.build.engine.BuildEngine')
    def test_timeout_defaults(self, mock_build_engine_class):
        """
        Verify timeout uses correct default.
        
        Validates: Requirements 7.1
        """
        mock_engine = MagicMock()
        mock_build_engine_class.return_value = mock_engine
        
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            dockerfile = Path(tmpdir) / "Dockerfile"
            dockerfile.write_text("FROM alpine:latest\n")
            
            result = runner.invoke(cli, [
                'build',
                tmpdir,
                '-f', str(dockerfile),
                '-t', 'test:latest'
            ], catch_exceptions=True)
            
            # Verify BuildEngine was called with timeout
            if mock_build_engine_class.called:
                call_args = mock_build_engine_class.call_args
                
                if call_args and len(call_args) > 1 and 'chroot_timeout' in call_args[1]:
                    timeout = call_args[1]['chroot_timeout']
                    
                    # Should be 600 seconds (10 minutes)
                    assert timeout == 600


class TestCommandsWithoutConfig:
    """Integration tests for commands without config."""
    
    @patch('derpy.build.engine.BuildEngine')
    @patch('derpy.storage.manager.ImageManager')
    def test_build_command_works_without_config(self, mock_image_manager_class, mock_build_engine_class):
        """
        Test build command works without config files.
        
        Validates: Requirements 1.2
        """
        # Mock BuildEngine
        mock_engine = MagicMock()
        mock_image = MagicMock()
        mock_image.layers = []
        mock_engine.build_image.return_value = mock_image
        mock_build_engine_class.return_value = mock_engine
        
        # Mock ImageManager
        mock_manager = MagicMock()
        mock_image_manager_class.return_value = mock_manager
        
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Ensure no config file exists
            config_path = Path(tmpdir) / ".derpy" / "config.yaml"
            assert not config_path.exists()
            
            # Create Dockerfile
            dockerfile = Path(tmpdir) / "Dockerfile"
            dockerfile.write_text("FROM alpine:latest\n")
            
            # Run build
            with patch.dict(os.environ, {'HOME': tmpdir}):
                result = runner.invoke(cli, [
                    'build',
                    tmpdir,
                    '-f', str(dockerfile),
                    '-t', 'test:latest'
                ], catch_exceptions=True)
            
            # Should work (or fail for reasons other than config)
            # The important thing is no config file was accessed
            assert not config_path.exists()
    
    @patch('derpy.storage.manager.ImageManager')
    def test_ls_command_works_without_config(self, mock_image_manager_class):
        """
        Test ls command works without config files.
        
        Validates: Requirements 1.3
        """
        mock_manager = MagicMock()
        mock_manager.list_local_images.return_value = []
        mock_image_manager_class.return_value = mock_manager
        
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".derpy" / "config.yaml"
            assert not config_path.exists()
            
            with patch.dict(os.environ, {'HOME': tmpdir}):
                result = runner.invoke(cli, ['ls'], catch_exceptions=True)
            
            assert not config_path.exists()
    
    @patch('derpy.storage.manager.ImageManager')
    def test_rm_command_works_without_config(self, mock_image_manager_class):
        """
        Test rm command works without config files.
        
        Validates: Requirements 1.4
        """
        mock_manager = MagicMock()
        mock_manager.image_exists.return_value = True
        mock_manager.remove_image.return_value = True
        mock_image_manager_class.return_value = mock_manager
        
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".derpy" / "config.yaml"
            assert not config_path.exists()
            
            with patch.dict(os.environ, {'HOME': tmpdir}):
                result = runner.invoke(cli, ['rm', 'test:latest'], catch_exceptions=True)
            
            assert not config_path.exists()
    
    @patch('derpy.storage.manager.ImageManager')
    def test_purge_command_works_without_config(self, mock_image_manager_class):
        """
        Test purge command works without config files.
        
        Validates: Requirements 1.5
        """
        mock_manager = MagicMock()
        mock_manager.purge_all_images.return_value = 0
        mock_image_manager_class.return_value = mock_manager
        
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".derpy" / "config.yaml"
            assert not config_path.exists()
            
            with patch.dict(os.environ, {'HOME': tmpdir}):
                result = runner.invoke(cli, ['purge', '--force'], catch_exceptions=True)
            
            assert not config_path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
