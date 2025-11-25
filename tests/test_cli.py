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


class TestLoginCommand:
    """Tests for login command."""
    
    def test_login_help(self):
        """Test login command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['login', '--help'])
        assert result.exit_code == 0
        assert 'login' in result.output.lower()
        assert 'registry' in result.output.lower()
    
    def test_login_with_username_and_password_options(self):
        """Test login with username and password options."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            auth_file = Path(tmpdir) / "auth.json"
            # Mock the AuthManager to avoid actual network calls
            from unittest.mock import patch, MagicMock
            
            with patch('derpy.cli.main.AuthManager') as mock_auth_manager:
                mock_instance = MagicMock()
                mock_instance._normalize_registry.return_value = 'registry-1.docker.io'
                mock_auth_manager.return_value = mock_instance
                
                result = runner.invoke(
                    cli,
                    ['login', '-u', 'testuser', '-p', 'testpass', 'docker.io']
                )
                
                # Verify login was called
                mock_instance.login.assert_called_once_with(
                    registry='docker.io',
                    username='testuser',
                    password='testpass',
                    verify_auth=True
                )
                
                assert result.exit_code == 0
                assert 'Login Succeeded' in result.output
                assert 'registry-1.docker.io' in result.output
    
    def test_login_with_interactive_prompts(self):
        """Test login with interactive prompts (mocked)."""
        runner = CliRunner()
        from unittest.mock import patch, MagicMock
        
        with patch('derpy.cli.main.AuthManager') as mock_auth_manager, \
             patch('derpy.cli.main.getpass.getpass') as mock_getpass:
            
            mock_instance = MagicMock()
            mock_instance._normalize_registry.return_value = 'registry.example.com'
            mock_auth_manager.return_value = mock_instance
            
            # Mock getpass to return password without prompting
            mock_getpass.return_value = 'testpass'
            
            # Simulate user input for username only
            result = runner.invoke(
                cli,
                ['login', 'registry.example.com'],
                input='testuser\n'
            )
            
            # Verify login was called
            mock_instance.login.assert_called_once()
            call_args = mock_instance.login.call_args
            assert call_args[1]['registry'] == 'registry.example.com'
            assert call_args[1]['username'] == 'testuser'
            assert call_args[1]['password'] == 'testpass'
            
            assert result.exit_code == 0
            assert 'Login Succeeded' in result.output
    
    def test_login_with_password_stdin(self):
        """Test login with --password-stdin."""
        runner = CliRunner()
        from unittest.mock import patch, MagicMock
        
        with patch('derpy.cli.main.AuthManager') as mock_auth_manager:
            mock_instance = MagicMock()
            mock_instance._normalize_registry.return_value = 'registry.example.com'
            mock_auth_manager.return_value = mock_instance
            
            # Simulate password from stdin
            result = runner.invoke(
                cli,
                ['login', '-u', 'testuser', '--password-stdin', 'registry.example.com'],
                input='testpass\n'
            )
            
            # Verify login was called
            mock_instance.login.assert_called_once()
            call_args = mock_instance.login.call_args
            assert call_args[1]['username'] == 'testuser'
            assert call_args[1]['password'] == 'testpass'
            
            assert result.exit_code == 0
            assert 'Login Succeeded' in result.output
    
    def test_login_with_default_registry(self):
        """Test login with default registry (docker.io)."""
        runner = CliRunner()
        from unittest.mock import patch, MagicMock
        
        with patch('derpy.cli.main.AuthManager') as mock_auth_manager:
            mock_instance = MagicMock()
            mock_instance._normalize_registry.return_value = 'registry-1.docker.io'
            mock_auth_manager.return_value = mock_instance
            
            result = runner.invoke(
                cli,
                ['login', '-u', 'testuser', '-p', 'testpass']
            )
            
            # Verify login was called with docker.io (default)
            mock_instance.login.assert_called_once()
            call_args = mock_instance.login.call_args
            assert call_args[1]['registry'] == 'docker.io'
            
            assert result.exit_code == 0
            assert 'registry-1.docker.io' in result.output
    
    def test_login_with_custom_registry(self):
        """Test login with custom registry."""
        runner = CliRunner()
        from unittest.mock import patch, MagicMock
        
        with patch('derpy.cli.main.AuthManager') as mock_auth_manager:
            mock_instance = MagicMock()
            mock_instance._normalize_registry.return_value = 'my-registry.example.com'
            mock_auth_manager.return_value = mock_instance
            
            result = runner.invoke(
                cli,
                ['login', '-u', 'testuser', '-p', 'testpass', 'my-registry.example.com']
            )
            
            # Verify login was called with custom registry
            mock_instance.login.assert_called_once()
            call_args = mock_instance.login.call_args
            assert call_args[1]['registry'] == 'my-registry.example.com'
            
            assert result.exit_code == 0
            assert 'my-registry.example.com' in result.output
    
    def test_login_error_handling_invalid_credentials(self):
        """Test error handling for invalid credentials."""
        runner = CliRunner()
        from unittest.mock import patch, MagicMock
        from derpy.core.exceptions import InvalidCredentialsError
        
        with patch('derpy.cli.main.AuthManager') as mock_auth_manager:
            mock_instance = MagicMock()
            mock_instance._normalize_registry.return_value = 'registry.example.com'
            mock_instance.login.side_effect = InvalidCredentialsError('registry.example.com')
            mock_auth_manager.return_value = mock_instance
            
            result = runner.invoke(
                cli,
                ['login', '-u', 'baduser', '-p', 'badpass', 'registry.example.com']
            )
            
            assert result.exit_code == 1
            assert 'Authentication failed' in result.output
            assert 'check your username and password' in result.output.lower()
    
    def test_login_empty_username_error(self):
        """Test error when username is whitespace only."""
        runner = CliRunner()
        from unittest.mock import patch, MagicMock
        
        with patch('derpy.cli.main.AuthManager') as mock_auth_manager:
            mock_instance = MagicMock()
            mock_auth_manager.return_value = mock_instance
            
            # Test with whitespace-only username
            result = runner.invoke(
                cli,
                ['login', '-u', '   ', '-p', 'testpass', 'registry.example.com']
            )
            
            assert result.exit_code == 1
            assert 'Username cannot be empty' in result.output
    
    def test_login_empty_password_error(self):
        """Test error when password is empty."""
        runner = CliRunner()
        from unittest.mock import patch
        
        with patch('derpy.cli.main.AuthManager'):
            result = runner.invoke(
                cli,
                ['login', '-u', 'testuser', '-p', '', 'registry.example.com']
            )
            
            assert result.exit_code == 1
            assert 'Password cannot be empty' in result.output
    
    def test_login_password_and_stdin_conflict(self):
        """Test error when both --password and --password-stdin are used."""
        runner = CliRunner()
        from unittest.mock import patch
        
        with patch('derpy.cli.main.AuthManager'):
            result = runner.invoke(
                cli,
                ['login', '-u', 'testuser', '-p', 'testpass', '--password-stdin', 'registry.example.com']
            )
            
            assert result.exit_code == 1
            assert 'Cannot use both --password and --password-stdin' in result.output


class TestLogoutCommand:
    """Tests for logout command."""
    
    def test_logout_help(self):
        """Test logout command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['logout', '--help'])
        assert result.exit_code == 0
        assert 'logout' in result.output.lower()
        assert 'registry' in result.output.lower()
    
    def test_logout_with_specified_registry(self):
        """Test logout with specified registry."""
        runner = CliRunner()
        from unittest.mock import patch, MagicMock
        
        with patch('derpy.cli.main.AuthManager') as mock_auth_manager:
            mock_instance = MagicMock()
            mock_instance._normalize_registry.return_value = 'registry.example.com'
            mock_instance.logout.return_value = True  # Credentials were removed
            mock_auth_manager.return_value = mock_instance
            
            result = runner.invoke(
                cli,
                ['logout', 'registry.example.com']
            )
            
            # Verify logout was called
            mock_instance.logout.assert_called_once_with('registry.example.com')
            
            assert result.exit_code == 0
            assert 'Logged out from registry.example.com' in result.output
            assert 'Credentials removed' in result.output
    
    def test_logout_with_default_registry(self):
        """Test logout with default registry (docker.io)."""
        runner = CliRunner()
        from unittest.mock import patch, MagicMock
        
        with patch('derpy.cli.main.AuthManager') as mock_auth_manager:
            mock_instance = MagicMock()
            mock_instance._normalize_registry.return_value = 'registry-1.docker.io'
            mock_instance.logout.return_value = True  # Credentials were removed
            mock_auth_manager.return_value = mock_instance
            
            result = runner.invoke(
                cli,
                ['logout']
            )
            
            # Verify logout was called with docker.io (default)
            mock_instance.logout.assert_called_once_with('docker.io')
            
            assert result.exit_code == 0
            assert 'Logged out from registry-1.docker.io' in result.output
            assert 'Credentials removed' in result.output
    
    def test_logout_when_credentials_exist(self):
        """Test logout when credentials exist."""
        runner = CliRunner()
        from unittest.mock import patch, MagicMock
        
        with patch('derpy.cli.main.AuthManager') as mock_auth_manager:
            mock_instance = MagicMock()
            mock_instance._normalize_registry.return_value = 'registry.example.com'
            mock_instance.logout.return_value = True  # Credentials were removed
            mock_auth_manager.return_value = mock_instance
            
            result = runner.invoke(
                cli,
                ['logout', 'registry.example.com']
            )
            
            assert result.exit_code == 0
            assert 'Logged out from registry.example.com' in result.output
            assert 'Credentials removed' in result.output
    
    def test_logout_when_no_credentials_exist(self):
        """Test logout when no credentials exist."""
        runner = CliRunner()
        from unittest.mock import patch, MagicMock
        
        with patch('derpy.cli.main.AuthManager') as mock_auth_manager:
            mock_instance = MagicMock()
            mock_instance._normalize_registry.return_value = 'registry.example.com'
            mock_instance.logout.return_value = False  # No credentials to remove
            mock_auth_manager.return_value = mock_instance
            
            result = runner.invoke(
                cli,
                ['logout', 'registry.example.com']
            )
            
            assert result.exit_code == 0
            assert 'No credentials found for registry.example.com' in result.output
            assert 'Already logged out or never logged in' in result.output


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
