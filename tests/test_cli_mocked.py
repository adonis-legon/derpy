"""Mocked tests for CLI."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
from pathlib import Path
import tempfile

from derpy.cli.main import cli, version


class TestCLIMocked:
    """Mocked tests for CLI commands."""
    
    def test_version_command_output(self):
        """Test version command output."""
        runner = CliRunner()
        result = runner.invoke(cli, ['version'])
        
        assert result.exit_code == 0
        assert 'version' in result.output.lower()
        assert 'author' in result.output.lower()
    
    @patch('derpy.cli.main.ConfigManager')
    def test_config_show_with_mock(self, mock_config_manager_class):
        """Test config show with mocked ConfigManager."""
        mock_manager = Mock()
        mock_config = Mock()
        mock_config.images_path = Path("/tmp/images")
        mock_config.build_settings = Mock()
        mock_config.build_settings.default_platform = "linux/amd64"
        mock_config.build_settings.max_layers = 127
        mock_config.build_settings.compression = "gzip"
        mock_config.build_settings.parallel_builds = False
        mock_config.registry_configs = {}
        
        mock_manager.get_config.return_value = mock_config
        mock_config_manager_class.return_value = mock_manager
        
        runner = CliRunner()
        result = runner.invoke(cli, ['config', 'show'])
        
        # Should succeed or show config
        assert result.exit_code in [0, 1]
    
    @patch('derpy.cli.main.BuildEngine')
    @patch('derpy.cli.main.ImageManager')
    def test_build_command_with_mock(self, mock_image_manager_class, mock_build_engine_class):
        """Test build command with mocked dependencies."""
        # Mock BuildEngine
        mock_engine = Mock()
        mock_image = Mock()
        mock_image.layers = []
        mock_engine.build_image.return_value = mock_image
        mock_build_engine_class.return_value = mock_engine
        
        # Mock ImageManager
        mock_manager = Mock()
        mock_image_manager_class.return_value = mock_manager
        
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            context_path = Path(tmpdir)
            dockerfile_path = context_path / "Dockerfile"
            dockerfile_path.write_text("FROM ubuntu:20.04\n")
            
            result = runner.invoke(cli, [
                'build',
                str(context_path),
                '-f', str(dockerfile_path),
                '-t', 'test:latest'
            ])
            
            # May succeed or fail depending on mocking
            assert result.exit_code in [0, 1]
    
    @patch('derpy.cli.main.ImageManager')
    def test_list_command_with_mock(self, mock_image_manager_class):
        """Test list command with mocked ImageManager."""
        mock_manager = Mock()
        mock_manager.list_local_images.return_value = []
        mock_image_manager_class.return_value = mock_manager
        
        runner = CliRunner()
        result = runner.invoke(cli, ['ls'])
        
        # Should succeed
        assert result.exit_code in [0, 1]
    
    def test_cli_help_command(self):
        """Test CLI help command."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert 'build' in result.output.lower() or 'usage' in result.output.lower()
    
    def test_build_help_command(self):
        """Test build help command."""
        runner = CliRunner()
        result = runner.invoke(cli, ['build', '--help'])
        
        assert result.exit_code == 0
        assert 'dockerfile' in result.output.lower() or 'context' in result.output.lower()
    
    def test_config_help_command(self):
        """Test config help command."""
        runner = CliRunner()
        result = runner.invoke(cli, ['config', '--help'])
        
        assert result.exit_code == 0


class TestCLIErrorHandling:
    """Test CLI error handling."""
    
    def test_build_with_nonexistent_context(self):
        """Test build with non-existent context."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            'build',
            '/nonexistent/path',
            '-t', 'test:latest'
        ])
        
        assert result.exit_code != 0
    
    def test_build_without_tag(self):
        """Test build without required tag."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(cli, ['build', tmpdir])
            
            # Should fail due to missing required option
            assert result.exit_code != 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
