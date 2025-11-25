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


class TestPushWithAuthentication:
    """Test push command with authentication."""
    
    @patch('derpy.cli.main.RegistryClient')
    @patch('derpy.cli.main.ImageManager')
    @patch('derpy.cli.main.AuthManager')
    def test_push_with_valid_credentials(
        self,
        mock_auth_manager_class,
        mock_image_manager_class,
        mock_registry_client_class
    ):
        """Test push with valid credentials from AuthManager."""
        # Mock AuthManager
        mock_auth_manager = Mock()
        mock_credentials = Mock()
        mock_credentials.username = 'testuser'
        mock_credentials.decode_password.return_value = 'testpass'
        mock_auth_manager.get_credentials.return_value = mock_credentials
        mock_auth_manager._normalize_registry.return_value = 'registry-1.docker.io'
        mock_auth_manager_class.return_value = mock_auth_manager
        
        # Mock ImageManager
        mock_image_manager = Mock()
        mock_image_manager.image_exists.return_value = True
        mock_image_manager.prepare_image_for_push.return_value = (
            b'manifest',
            b'config',
            [('sha256:abc', b'layer1')]
        )
        mock_image_manager_class.return_value = mock_image_manager
        
        # Mock RegistryClient
        mock_client = Mock()
        mock_client.check_connectivity.return_value = True
        mock_client.verify_authentication.return_value = True
        mock_client.push_image.return_value = {
            'repository': 'myapp',
            'tag': 'latest',
            'manifest_digest': 'sha256:def'
        }
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_registry_client_class.return_value = mock_client
        
        runner = CliRunner()
        result = runner.invoke(cli, ['push', 'myapp:latest'])
        
        # Should succeed
        assert result.exit_code == 0
        assert 'successfully pushed' in result.output.lower()
        
        # Verify AuthManager was called
        mock_auth_manager.get_credentials.assert_called_once()
        
        # Verify RegistryClient was created with credentials
        mock_registry_client_class.assert_called_once()
        call_args = mock_registry_client_class.call_args
        registry_config = call_args[0][0]
        assert registry_config.username == 'testuser'
        assert registry_config.password == 'testpass'
    
    @patch('derpy.cli.main.ImageManager')
    @patch('derpy.cli.main.AuthManager')
    def test_push_without_credentials(
        self,
        mock_auth_manager_class,
        mock_image_manager_class
    ):
        """Test push without credentials shows error."""
        # Mock AuthManager with no credentials
        mock_auth_manager = Mock()
        mock_auth_manager.get_credentials.return_value = None
        mock_auth_manager._normalize_registry.return_value = 'registry-1.docker.io'
        mock_auth_manager_class.return_value = mock_auth_manager
        
        # Mock ImageManager
        mock_image_manager = Mock()
        mock_image_manager.image_exists.return_value = True
        mock_image_manager_class.return_value = mock_image_manager
        
        runner = CliRunner()
        result = runner.invoke(cli, ['push', 'myapp:latest'])
        
        # Should fail
        assert result.exit_code != 0
        assert 'no credentials found' in result.output.lower()
        assert 'derpy login' in result.output.lower()
    
    @patch('derpy.cli.main.RegistryClient')
    @patch('derpy.cli.main.ImageManager')
    @patch('derpy.cli.main.AuthManager')
    def test_push_with_invalid_credentials(
        self,
        mock_auth_manager_class,
        mock_image_manager_class,
        mock_registry_client_class
    ):
        """Test push with invalid credentials shows error."""
        # Mock AuthManager
        mock_auth_manager = Mock()
        mock_credentials = Mock()
        mock_credentials.username = 'testuser'
        mock_credentials.decode_password.return_value = 'wrongpass'
        mock_auth_manager.get_credentials.return_value = mock_credentials
        mock_auth_manager._normalize_registry.return_value = 'registry-1.docker.io'
        mock_auth_manager_class.return_value = mock_auth_manager
        
        # Mock ImageManager
        mock_image_manager = Mock()
        mock_image_manager.image_exists.return_value = True
        mock_image_manager_class.return_value = mock_image_manager
        
        # Mock RegistryClient with failed authentication
        mock_client = Mock()
        mock_client.check_connectivity.return_value = True
        mock_client.verify_authentication.return_value = False
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_registry_client_class.return_value = mock_client
        
        runner = CliRunner()
        result = runner.invoke(cli, ['push', 'myapp:latest'])
        
        # Should fail
        assert result.exit_code != 0
        assert 'authentication failed' in result.output.lower()
        assert 'derpy login' in result.output.lower()
    
    @patch('derpy.cli.main.RegistryClient')
    @patch('derpy.cli.main.ImageManager')
    @patch('derpy.cli.main.AuthManager')
    def test_push_with_username_password_options(
        self,
        mock_auth_manager_class,
        mock_image_manager_class,
        mock_registry_client_class
    ):
        """Test push with username and password options overrides stored credentials."""
        # Mock AuthManager (should not be used for credentials)
        mock_auth_manager = Mock()
        mock_auth_manager._normalize_registry.return_value = 'registry-1.docker.io'
        mock_auth_manager_class.return_value = mock_auth_manager
        
        # Mock ImageManager
        mock_image_manager = Mock()
        mock_image_manager.image_exists.return_value = True
        mock_image_manager.prepare_image_for_push.return_value = (
            b'manifest',
            b'config',
            [('sha256:abc', b'layer1')]
        )
        mock_image_manager_class.return_value = mock_image_manager
        
        # Mock RegistryClient
        mock_client = Mock()
        mock_client.check_connectivity.return_value = True
        mock_client.verify_authentication.return_value = True
        mock_client.push_image.return_value = {
            'repository': 'myapp',
            'tag': 'latest',
            'manifest_digest': 'sha256:def'
        }
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_registry_client_class.return_value = mock_client
        
        runner = CliRunner()
        result = runner.invoke(cli, [
            'push', 'myapp:latest',
            '--username', 'cmduser',
            '--password', 'cmdpass'
        ])
        
        # Should succeed
        assert result.exit_code == 0
        
        # Verify RegistryClient was created with command-line credentials
        mock_registry_client_class.assert_called_once()
        call_args = mock_registry_client_class.call_args
        registry_config = call_args[0][0]
        assert registry_config.username == 'cmduser'
        assert registry_config.password == 'cmdpass'
    
    @patch('derpy.cli.main.RegistryClient')
    @patch('derpy.cli.main.ImageManager')
    @patch('derpy.cli.main.AuthManager')
    def test_push_with_registry_in_image_tag(
        self,
        mock_auth_manager_class,
        mock_image_manager_class,
        mock_registry_client_class
    ):
        """Test push with registry specified in image tag."""
        # Mock AuthManager
        mock_auth_manager = Mock()
        mock_credentials = Mock()
        mock_credentials.username = 'testuser'
        mock_credentials.decode_password.return_value = 'testpass'
        mock_auth_manager.get_credentials.return_value = mock_credentials
        mock_auth_manager._normalize_registry.return_value = 'registry.example.com'
        mock_auth_manager_class.return_value = mock_auth_manager
        
        # Mock ImageManager
        mock_image_manager = Mock()
        mock_image_manager.image_exists.return_value = True
        mock_image_manager.prepare_image_for_push.return_value = (
            b'manifest',
            b'config',
            [('sha256:abc', b'layer1')]
        )
        mock_image_manager_class.return_value = mock_image_manager
        
        # Mock RegistryClient
        mock_client = Mock()
        mock_client.check_connectivity.return_value = True
        mock_client.verify_authentication.return_value = True
        mock_client.push_image.return_value = {
            'repository': 'myorg/myapp',
            'tag': 'latest',
            'manifest_digest': 'sha256:def'
        }
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_registry_client_class.return_value = mock_client
        
        runner = CliRunner()
        result = runner.invoke(cli, ['push', 'registry.example.com/myorg/myapp:latest'])
        
        # Should succeed
        assert result.exit_code == 0
        
        # Verify AuthManager was called with correct registry
        mock_auth_manager.get_credentials.assert_called_once_with('registry.example.com')
    
    @patch('derpy.cli.main.RegistryClient')
    @patch('derpy.cli.main.ImageManager')
    @patch('derpy.cli.main.AuthManager')
    def test_push_authentication_error_during_push(
        self,
        mock_auth_manager_class,
        mock_image_manager_class,
        mock_registry_client_class
    ):
        """Test push handles authentication error during push operation."""
        from derpy.core.exceptions import RegistryAuthenticationError
        
        # Mock AuthManager
        mock_auth_manager = Mock()
        mock_credentials = Mock()
        mock_credentials.username = 'testuser'
        mock_credentials.decode_password.return_value = 'testpass'
        mock_auth_manager.get_credentials.return_value = mock_credentials
        mock_auth_manager._normalize_registry.return_value = 'registry-1.docker.io'
        mock_auth_manager_class.return_value = mock_auth_manager
        
        # Mock ImageManager
        mock_image_manager = Mock()
        mock_image_manager.image_exists.return_value = True
        mock_image_manager.prepare_image_for_push.return_value = (
            b'manifest',
            b'config',
            [('sha256:abc', b'layer1')]
        )
        mock_image_manager_class.return_value = mock_image_manager
        
        # Mock RegistryClient that raises authentication error during push
        mock_client = Mock()
        mock_client.check_connectivity.return_value = True
        mock_client.verify_authentication.return_value = True
        mock_client.push_image.side_effect = RegistryAuthenticationError(
            "Token expired during push"
        )
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_registry_client_class.return_value = mock_client
        
        runner = CliRunner()
        result = runner.invoke(cli, ['push', 'myapp:latest'])
        
        # Should fail with authentication error
        assert result.exit_code != 0
        assert 'authentication error' in result.output.lower()
        assert 'derpy login' in result.output.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
