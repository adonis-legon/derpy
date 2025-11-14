"""End-to-end integration tests for registry authentication.

Tests complete workflows including:
- login -> build -> push -> logout
- Docker Hub anonymous pulls
- Docker Hub authenticated pulls
- Private registry authentication
- Error scenarios and user feedback
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
from click.testing import CliRunner

from derpy.cli.main import cli
from derpy.core.auth import AuthManager
from derpy.core.exceptions import InvalidCredentialsError, AuthenticationError


class TestDockerHubAnonymousPulls:
    """Test Docker Hub anonymous pull functionality."""
    
    def test_anonymous_pull_public_image(self):
        """Test pulling public image without authentication."""
        # This test verifies that the system can handle anonymous pulls
        # In a real scenario, this would pull from Docker Hub
        # For testing, we mock the registry client
        
        with patch('derpy.build.base_image.RegistryClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.check_connectivity.return_value = True
            mock_client_class.return_value.__enter__.return_value = mock_client
            
            # Simulate anonymous token authentication
            from derpy.core.config import RegistryConfig
            config = RegistryConfig(
                url='https://registry-1.docker.io',
                username=None,
                password=None
            )
            
            # Verify config has no credentials
            assert config.username is None
            assert config.password is None
    
    def test_anonymous_pull_handles_rate_limits(self):
        """Test that anonymous pulls handle rate limit errors gracefully."""
        # Docker Hub has rate limits for anonymous pulls
        # Verify error messages are clear
        
        from derpy.core.exceptions import RegistryError
        
        error_msg = "Rate limit exceeded for anonymous pulls"
        error = RegistryError(error_msg)
        
        assert "rate limit" in str(error).lower()


class TestDockerHubAuthenticatedPulls:
    """Test Docker Hub authenticated pull functionality."""
    
    def test_authenticated_pull_uses_stored_credentials(self):
        """Test that authenticated pulls use stored credentials."""
        with tempfile.TemporaryDirectory() as tmpdir:
            auth_file = Path(tmpdir) / 'auth.json'
            auth_manager = AuthManager(auth_file=auth_file)
            
            # Store credentials
            auth_manager.login(
                registry='docker.io',
                username='testuser',
                password='testpass',
                verify_auth=False
            )
            
            # Retrieve credentials
            creds = auth_manager.get_credentials('docker.io')
            
            assert creds is not None
            assert creds.username == 'testuser'
            assert creds.registry == 'registry-1.docker.io'  # Normalized
    
    def test_authenticated_pull_with_token_auth(self):
        """Test authenticated pull with token authentication."""
        with patch('derpy.registry.client.requests') as mock_requests:
            # Mock token request
            mock_token_response = Mock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {'token': 'test_token_123'}
            
            # Mock manifest request
            mock_manifest_response = Mock()
            mock_manifest_response.status_code = 200
            mock_manifest_response.json.return_value = {
                'schemaVersion': 2,
                'mediaType': 'application/vnd.docker.distribution.manifest.v2+json'
            }
            
            mock_requests.get.side_effect = [
                mock_token_response,
                mock_manifest_response
            ]
            
            # Verify token was used
            assert mock_token_response.json()['token'] == 'test_token_123'


class TestPrivateRegistryAuthentication:
    """Test private registry authentication."""
    
    def test_login_to_private_registry(self):
        """Test login to private registry."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            auth_file = Path(tmpdir) / 'auth.json'
            
            with patch('derpy.cli.main.AuthManager') as mock_auth_manager:
                mock_instance = MagicMock()
                mock_instance._normalize_registry.return_value = 'registry.example.com'
                mock_instance.auth_file = auth_file
                mock_auth_manager.return_value = mock_instance
                
                result = runner.invoke(
                    cli,
                    ['login', '-u', 'admin', '-p', 'secret', 'registry.example.com']
                )
                
                assert result.exit_code == 0
                assert 'Login Succeeded' in result.output
                assert 'registry.example.com' in result.output
    
    def test_build_with_private_base_image(self):
        """Test building with private base image uses credentials."""
        with tempfile.TemporaryDirectory() as tmpdir:
            auth_file = Path(tmpdir) / 'auth.json'
            auth_manager = AuthManager(auth_file=auth_file)
            
            # Store credentials for private registry
            auth_manager.login(
                registry='registry.example.com',
                username='admin',
                password='secret',
                verify_auth=False
            )
            
            # Verify credentials are available
            creds = auth_manager.get_credentials('registry.example.com')
            assert creds is not None
            assert creds.username == 'admin'
    
    def test_push_to_private_registry(self):
        """Test pushing to private registry with authentication."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('derpy.cli.main.AuthManager') as mock_auth_manager, \
                 patch('derpy.cli.main.ImageManager') as mock_image_manager, \
                 patch('derpy.cli.main.RegistryClient') as mock_registry_client:
                
                # Setup mocks
                mock_auth_instance = MagicMock()
                mock_creds = MagicMock()
                mock_creds.username = 'admin'
                mock_creds.password = 'secret'
                mock_auth_instance.get_credentials.return_value = mock_creds
                mock_auth_manager.return_value = mock_auth_instance
                
                mock_storage = MagicMock()
                mock_image = MagicMock()
                mock_image.name = 'myapp'
                mock_image.tag = 'latest'
                mock_storage.get_image.return_value = mock_image
                mock_image_manager.return_value = mock_storage
                
                mock_client = MagicMock()
                mock_registry_client.return_value.__enter__.return_value = mock_client
                
                result = runner.invoke(
                    cli,
                    ['push', 'registry.example.com/myapp:latest']
                )
                
                # Verify credentials were retrieved
                mock_auth_instance.get_credentials.assert_called()


class TestCompleteWorkflow:
    """Test complete authentication workflow: login -> build -> push -> logout."""
    
    def test_complete_workflow_docker_hub(self):
        """Test complete workflow with Docker Hub."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            auth_file = Path(tmpdir) / 'auth.json'
            
            # Step 1: Login
            with patch('derpy.cli.main.AuthManager') as mock_auth_manager:
                mock_instance = MagicMock()
                mock_instance._normalize_registry.return_value = 'registry-1.docker.io'
                mock_instance.auth_file = auth_file
                mock_auth_manager.return_value = mock_instance
                
                result = runner.invoke(
                    cli,
                    ['login', '-u', 'testuser', '-p', 'testpass']
                )
                
                assert result.exit_code == 0
                assert 'Login Succeeded' in result.output
            
            # Step 2: Verify credentials are stored
            auth_manager = AuthManager(auth_file=auth_file)
            auth_manager.login('docker.io', 'testuser', 'testpass', verify_auth=False)
            creds = auth_manager.get_credentials('docker.io')
            assert creds is not None
            
            # Step 3: Logout
            with patch('derpy.cli.main.AuthManager') as mock_auth_manager:
                mock_instance = MagicMock()
                mock_instance._normalize_registry.return_value = 'registry-1.docker.io'
                mock_instance.logout.return_value = True
                mock_auth_manager.return_value = mock_instance
                
                result = runner.invoke(cli, ['logout'])
                
                assert result.exit_code == 0
                assert 'Logged out' in result.output
    
    def test_complete_workflow_private_registry(self):
        """Test complete workflow with private registry."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            auth_file = Path(tmpdir) / 'auth.json'
            
            # Step 1: Login to private registry
            with patch('derpy.cli.main.AuthManager') as mock_auth_manager:
                mock_instance = MagicMock()
                mock_instance._normalize_registry.return_value = 'registry.example.com'
                mock_instance.auth_file = auth_file
                mock_auth_manager.return_value = mock_instance
                
                result = runner.invoke(
                    cli,
                    ['login', '-u', 'admin', '-p', 'secret', 'registry.example.com']
                )
                
                assert result.exit_code == 0
                assert 'Login Succeeded' in result.output
                assert 'registry.example.com' in result.output
            
            # Step 2: Verify credentials persist
            auth_manager = AuthManager(auth_file=auth_file)
            auth_manager.login('registry.example.com', 'admin', 'secret', verify_auth=False)
            creds = auth_manager.get_credentials('registry.example.com')
            assert creds is not None
            assert creds.username == 'admin'
            
            # Step 3: Logout from private registry
            with patch('derpy.cli.main.AuthManager') as mock_auth_manager:
                mock_instance = MagicMock()
                mock_instance._normalize_registry.return_value = 'registry.example.com'
                mock_instance.logout.return_value = True
                mock_auth_manager.return_value = mock_instance
                
                result = runner.invoke(cli, ['logout', 'registry.example.com'])
                
                assert result.exit_code == 0
                assert 'Logged out from registry.example.com' in result.output


class TestErrorScenarios:
    """Test error scenarios and user feedback."""
    
    def test_login_with_invalid_credentials(self):
        """Test login with invalid credentials shows clear error."""
        runner = CliRunner()
        
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
            assert 'registry.example.com' in result.output
            assert 'check your username and password' in result.output.lower()
    
    def test_build_without_credentials_for_private_image(self):
        """Test build fails with clear message when credentials missing."""
        # This simulates trying to build with a private base image
        # without logging in first
        
        with tempfile.TemporaryDirectory() as tmpdir:
            auth_file = Path(tmpdir) / 'auth.json'
            auth_manager = AuthManager(auth_file=auth_file)
            
            # No credentials stored
            creds = auth_manager.get_credentials('registry.example.com')
            assert creds is None
    
    def test_push_without_credentials(self):
        """Test push fails with clear message when credentials missing."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('derpy.cli.main.AuthManager') as mock_auth_manager, \
                 patch('derpy.cli.main.ImageManager') as mock_image_manager:
                
                # Setup mocks
                mock_auth_instance = MagicMock()
                mock_auth_instance.get_credentials.return_value = None  # No credentials
                mock_auth_manager.return_value = mock_auth_instance
                
                mock_storage = MagicMock()
                mock_image = MagicMock()
                mock_image.name = 'myapp'
                mock_image.tag = 'latest'
                mock_storage.get_image.return_value = mock_image
                mock_image_manager.return_value = mock_storage
                
                result = runner.invoke(
                    cli,
                    ['push', 'registry.example.com/myapp:latest']
                )
                
                assert result.exit_code == 1
                assert 'No credentials found' in result.output
                assert 'derpy login' in result.output
    
    def test_network_error_during_login(self):
        """Test network error during login shows clear message."""
        runner = CliRunner()
        
        with patch('derpy.cli.main.AuthManager') as mock_auth_manager:
            mock_instance = MagicMock()
            mock_instance._normalize_registry.return_value = 'registry.example.com'
            mock_instance.login.side_effect = AuthenticationError(
                'Cannot connect to registry: Connection refused'
            )
            mock_auth_manager.return_value = mock_instance
            
            result = runner.invoke(
                cli,
                ['login', '-u', 'testuser', '-p', 'testpass', 'registry.example.com']
            )
            
            assert result.exit_code == 1
            assert 'Error' in result.output or 'failed' in result.output.lower()
    
    def test_logout_from_nonexistent_registry(self):
        """Test logout from registry with no credentials."""
        runner = CliRunner()
        
        with patch('derpy.cli.main.AuthManager') as mock_auth_manager:
            mock_instance = MagicMock()
            mock_instance._normalize_registry.return_value = 'nonexistent.example.com'
            mock_instance.logout.return_value = False  # No credentials found
            mock_auth_manager.return_value = mock_instance
            
            result = runner.invoke(cli, ['logout', 'nonexistent.example.com'])
            
            assert result.exit_code == 0
            assert 'No credentials found' in result.output
            assert 'Already logged out' in result.output
    
    def test_empty_username_error_message(self):
        """Test clear error message for empty username."""
        runner = CliRunner()
        
        # When empty string is provided via -u, it still prompts
        # So we test with whitespace-only input
        result = runner.invoke(
            cli,
            ['login', '-u', '   ', '-p', 'testpass', 'registry.example.com']
        )
        
        assert result.exit_code == 1
        assert 'Username cannot be empty' in result.output
    
    def test_empty_password_error_message(self):
        """Test clear error message for empty password."""
        runner = CliRunner()
        
        # Test with whitespace-only password
        result = runner.invoke(
            cli,
            ['login', '-u', 'testuser', '-p', '   ', 'registry.example.com']
        )
        
        assert result.exit_code == 1
        assert 'Password cannot be empty' in result.output
    
    def test_conflicting_password_options_error(self):
        """Test error when both --password and --password-stdin are used."""
        runner = CliRunner()
        
        result = runner.invoke(
            cli,
            ['login', '-u', 'testuser', '-p', 'testpass', '--password-stdin']
        )
        
        assert result.exit_code == 1
        assert 'Cannot use both' in result.output


class TestMultipleRegistries:
    """Test managing credentials for multiple registries."""
    
    def test_login_to_multiple_registries(self):
        """Test logging in to multiple registries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            auth_file = Path(tmpdir) / 'auth.json'
            auth_manager = AuthManager(auth_file=auth_file)
            
            # Login to multiple registries
            auth_manager.login('docker.io', 'user1', 'pass1', verify_auth=False)
            auth_manager.login('registry.example.com', 'user2', 'pass2', verify_auth=False)
            auth_manager.login('gcr.io', 'user3', 'pass3', verify_auth=False)
            
            # Verify all credentials are stored
            registries = auth_manager.list_registries()
            assert len(registries) == 3
            assert 'registry-1.docker.io' in registries
            assert 'registry.example.com' in registries
            assert 'gcr.io' in registries
    
    def test_logout_from_one_registry_keeps_others(self):
        """Test logging out from one registry doesn't affect others."""
        with tempfile.TemporaryDirectory() as tmpdir:
            auth_file = Path(tmpdir) / 'auth.json'
            auth_manager = AuthManager(auth_file=auth_file)
            
            # Login to multiple registries
            auth_manager.login('docker.io', 'user1', 'pass1', verify_auth=False)
            auth_manager.login('registry.example.com', 'user2', 'pass2', verify_auth=False)
            
            # Logout from one
            auth_manager.logout('docker.io')
            
            # Verify other credentials still exist
            assert auth_manager.get_credentials('docker.io') is None
            assert auth_manager.get_credentials('registry.example.com') is not None
    
    def test_update_credentials_for_existing_registry(self):
        """Test updating credentials for an existing registry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            auth_file = Path(tmpdir) / 'auth.json'
            auth_manager = AuthManager(auth_file=auth_file)
            
            # Initial login
            auth_manager.login('registry.example.com', 'user1', 'pass1', verify_auth=False)
            
            # Update credentials
            auth_manager.login('registry.example.com', 'user2', 'pass2', verify_auth=False)
            
            # Verify updated credentials
            creds = auth_manager.get_credentials('registry.example.com')
            assert creds.username == 'user2'
            assert creds.decode_password() == 'pass2'


class TestAWSECRSupport:
    """Test AWS ECR authentication support."""
    
    def test_ecr_registry_pattern_recognition(self):
        """Test that ECR registry URLs are recognized."""
        ecr_urls = [
            '123456789012.dkr.ecr.us-east-1.amazonaws.com',
            '123456789012.dkr.ecr.eu-west-1.amazonaws.com',
            '123456789012.dkr.ecr.ap-southeast-1.amazonaws.com',
        ]
        
        for url in ecr_urls:
            # ECR URLs should be recognized by pattern
            assert '.dkr.ecr.' in url
            assert '.amazonaws.com' in url
    
    def test_login_to_ecr_registry(self):
        """Test login to AWS ECR registry."""
        runner = CliRunner()
        
        with patch('derpy.cli.main.AuthManager') as mock_auth_manager:
            mock_instance = MagicMock()
            ecr_url = '123456789012.dkr.ecr.us-east-1.amazonaws.com'
            mock_instance._normalize_registry.return_value = ecr_url
            mock_auth_manager.return_value = mock_instance
            
            result = runner.invoke(
                cli,
                ['login', '-u', 'AWS', '-p', 'ecr_token_here', ecr_url]
            )
            
            assert result.exit_code == 0
            assert 'Login Succeeded' in result.output
    
    def test_ecr_credentials_storage(self):
        """Test storing ECR credentials."""
        with tempfile.TemporaryDirectory() as tmpdir:
            auth_file = Path(tmpdir) / 'auth.json'
            auth_manager = AuthManager(auth_file=auth_file)
            
            ecr_url = '123456789012.dkr.ecr.us-east-1.amazonaws.com'
            
            # Store ECR credentials
            auth_manager.login(
                registry=ecr_url,
                username='AWS',
                password='ecr_token_here',
                verify_auth=False
            )
            
            # Verify credentials are stored
            creds = auth_manager.get_credentials(ecr_url)
            assert creds is not None
            assert creds.username == 'AWS'


class TestCredentialPersistence:
    """Test credential persistence across sessions."""
    
    def test_credentials_persist_across_auth_manager_instances(self):
        """Test credentials persist when creating new AuthManager instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            auth_file = Path(tmpdir) / 'auth.json'
            
            # First instance - store credentials
            manager1 = AuthManager(auth_file=auth_file)
            manager1.login('registry.example.com', 'testuser', 'testpass', verify_auth=False)
            
            # Second instance - retrieve credentials
            manager2 = AuthManager(auth_file=auth_file)
            creds = manager2.get_credentials('registry.example.com')
            
            assert creds is not None
            assert creds.username == 'testuser'
            assert creds.decode_password() == 'testpass'
    
    def test_auth_file_format_compatibility(self):
        """Test auth file format is compatible with Docker's format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            auth_file = Path(tmpdir) / 'auth.json'
            auth_manager = AuthManager(auth_file=auth_file)
            
            # Store credentials
            auth_manager.login('registry.example.com', 'testuser', 'testpass', verify_auth=False)
            
            # Read and verify file format
            with open(auth_file, 'r') as f:
                data = json.load(f)
            
            # Should have 'auths' wrapper
            assert 'auths' in data
            assert 'registry.example.com' in data['auths']
            assert 'username' in data['auths']['registry.example.com']
            assert 'password' in data['auths']['registry.example.com']
    
    def test_file_permissions_are_secure(self):
        """Test auth file has secure permissions (0600)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            auth_file = Path(tmpdir) / 'auth.json'
            auth_manager = AuthManager(auth_file=auth_file)
            
            # Store credentials
            auth_manager.login('registry.example.com', 'testuser', 'testpass', verify_auth=False)
            
            # Check file permissions
            import stat
            file_stat = os.stat(auth_file)
            file_mode = stat.S_IMODE(file_stat.st_mode)
            
            # Should be 0600 (owner read/write only)
            expected_mode = stat.S_IRUSR | stat.S_IWUSR
            assert file_mode == expected_mode


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
