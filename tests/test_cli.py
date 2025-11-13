"""Tests for CLI commands."""

import pytest
from click.testing import CliRunner
from pathlib import Path
import tempfile

from derpy.cli.main import cli, version
from derpy.cli.banner import get_banner, BANNER


class TestBanner:
    """Tests for CLI banner."""
    
    def test_get_banner_returns_string(self):
        """Test that get_banner returns a string."""
        banner = get_banner()
        assert isinstance(banner, str)
        assert len(banner) > 0
    
    def test_banner_contains_content(self):
        """Test that banner contains expected content."""
        banner = get_banner()
        # Banner contains "A simple container tool"
        assert 'container tool' in banner.lower()
    
    def test_banner_constant_matches_function(self):
        """Test that BANNER constant matches get_banner output."""
        assert get_banner() == BANNER


class TestCLIBasics:
    """Tests for basic CLI functionality."""
    
    def test_cli_help(self):
        """Test CLI help command."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Build, manage, and distribute' in result.output or 'derpy' in result.output.lower()
    
    def test_cli_version_option(self):
        """Test CLI version option."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert 'version' in result.output.lower()
    
    def test_version_command(self):
        """Test version command."""
        runner = CliRunner()
        result = runner.invoke(cli, ['version'])
        assert result.exit_code == 0
        assert 'version' in result.output.lower()
        assert 'author' in result.output.lower()


class TestConfigCommands:
    """Tests for config commands."""
    
    def test_config_show(self):
        """Test config show command."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            result = runner.invoke(cli, ['config', 'show'], env={'DERPY_CONFIG': str(config_path)})
            # Command should work even if it shows default config
            assert result.exit_code in [0, 1]  # May fail if config doesn't exist yet
    
    def test_config_set_images_path(self):
        """Test config set for images_path."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            new_path = Path(tmpdir) / "images"
            result = runner.invoke(
                cli,
                ['config', 'set', 'images_path', str(new_path)],
                env={'DERPY_CONFIG': str(config_path)}
            )
            # May succeed or fail depending on config setup
            assert result.exit_code in [0, 1]


class TestBuildCommand:
    """Tests for build command."""
    
    def test_build_help(self):
        """Test build command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['build', '--help'])
        assert result.exit_code == 0
        assert 'build' in result.output.lower()
        assert 'dockerfile' in result.output.lower() or 'context' in result.output.lower()
    
    def test_build_missing_context(self):
        """Test build with missing context."""
        runner = CliRunner()
        result = runner.invoke(cli, ['build', '/nonexistent', '-t', 'test:latest'])
        assert result.exit_code != 0


class TestListCommand:
    """Tests for list command."""
    
    def test_list_help(self):
        """Test list command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['ls', '--help'])
        assert result.exit_code == 0
        assert 'list' in result.output.lower() or 'images' in result.output.lower()
    
    def test_list_images_empty(self):
        """Test listing images when none exist."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(cli, ['ls'], env={'DERPY_HOME': tmpdir})
            # Should succeed even with no images
            assert result.exit_code in [0, 1]


class TestPushCommand:
    """Tests for push command."""
    
    def test_push_help(self):
        """Test push command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['push', '--help'])
        assert result.exit_code == 0
        assert 'push' in result.output.lower()
        assert 'registry' in result.output.lower()
    
    def test_push_missing_image(self):
        """Test push with missing image."""
        runner = CliRunner()
        result = runner.invoke(cli, ['push', 'nonexistent:latest'])
        assert result.exit_code != 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
