"""Unit tests for AuthManager.

Tests credential storage, retrieval, security features, and registry URL normalization.
"""

import base64
import json
import os
import stat
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from derpy.core.auth import AuthManager, RegistryCredentials
from derpy.core.exceptions import (
    AuthenticationError,
    CredentialStorageError,
    InvalidCredentialsError
)


class TestRegistryCredentials:
    """Test RegistryCredentials dataclass."""
    
    def test_to_dict(self):
        """Test converting credentials to dictionary."""
        creds = RegistryCredentials(
            registry='registry.example.com',
            username='testuser',
            password='cGFzc3dvcmQ='  # base64 encoded 'password'
        )
        
        result = creds.to_dict()
        
        assert result == {
            'username': 'testuser',
            'password': 'cGFzc3dvcmQ='
        }
    
    def test_from_dict(self):
        """Test creating credentials from dictionary."""
        data = {
            'username': 'testuser',
            'password': 'cGFzc3dvcmQ='
        }
        
        creds = RegistryCredentials.from_dict('registry.example.com', data)
        
        assert creds.registry == 'registry.example.com'
        assert creds.username == 'testuser'
        assert creds.password == 'cGFzc3dvcmQ='
    
    def test_from_dict_missing_fields(self):
        """Test from_dict with missing fields raises error."""
        data = {'username': 'testuser'}
        
        with pytest.raises(CredentialStorageError) as exc_info:
            RegistryCredentials.from_dict('registry.example.com', data)
        
        assert 'missing username or password' in str(exc_info.value).lower()
    
    def test_encode_password(self):
        """Test password encoding."""
        password = 'mypassword'
        encoded = RegistryCredentials.encode_password(password)
        
        # Verify it's base64 encoded
        decoded = base64.b64decode(encoded).decode('utf-8')
        assert decoded == password
    
    def test_decode_password(self):
        """Test password decoding."""
        password = 'mypassword'
        encoded = base64.b64encode(password.encode('utf-8')).decode('utf-8')
        
        creds = RegistryCredentials(
            registry='registry.example.com',
            username='testuser',
            password=encoded
        )
        
        decoded = creds.decode_password()
        assert decoded == password


class TestAuthManager:
    """Test AuthManager functionality."""
    
    @pytest.fixture
    def temp_auth_file(self):
        """Create temporary auth file for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / 'auth.json'
            yield temp_path
    
    @pytest.fixture
    def auth_manager(self, temp_auth_file):
        """Create AuthManager with temporary auth file."""
        return AuthManager(auth_file=temp_auth_file)
    
    def test_init_creates_parent_directory(self):
        """Test that AuthManager creates parent directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            auth_file = Path(tmpdir) / 'subdir' / 'auth.json'
            
            manager = AuthManager(auth_file=auth_file)
            
            assert auth_file.parent.exists()
    
    def test_normalize_registry_docker_hub(self, auth_manager):
        """Test Docker Hub registry normalization."""
        test_cases = [
            ('docker.io', 'registry-1.docker.io'),
            ('Docker.IO', 'registry-1.docker.io'),
            ('registry.hub.docker.com', 'registry-1.docker.io'),
            ('index.docker.io', 'registry-1.docker.io'),
            ('', 'registry-1.docker.io'),
        ]
        
        for input_registry, expected in test_cases:
            result = auth_manager._normalize_registry(input_registry)
            assert result == expected, f"Failed for input: {input_registry}"
    
    def test_normalize_registry_custom(self, auth_manager):
        """Test custom registry normalization."""
        test_cases = [
            ('registry.example.com', 'registry.example.com'),
            ('Registry.Example.COM', 'registry.example.com'),
            ('https://registry.example.com', 'registry.example.com'),
            ('http://registry.example.com', 'registry.example.com'),
            ('registry.example.com/', 'registry.example.com'),
            ('registry.example.com:5000', 'registry.example.com:5000'),
        ]
        
        for input_registry, expected in test_cases:
            result = auth_manager._normalize_registry(input_registry)
            assert result == expected, f"Failed for input: {input_registry}"
    
    def test_login_stores_credentials(self, auth_manager):
        """Test login stores credentials correctly."""
        with patch('derpy.registry.client.RegistryClient') as mock_client_class:
            # Mock registry client verification
            mock_client = MagicMock()
            mock_client.verify_authentication.return_value = True
            mock_client_class.return_value.__enter__.return_value = mock_client
            
            auth_manager.login(
                registry='registry.example.com',
                username='testuser',
                password='testpass',
                verify_auth=True
            )
            
            # Verify credentials were stored
            creds = auth_manager.get_credentials('registry.example.com')
            assert creds is not None
            assert creds.username == 'testuser'
            assert creds.decode_password() == 'testpass'
    
    def test_login_without_verification(self, auth_manager):
        """Test login without credential verification."""
        auth_manager.login(
            registry='registry.example.com',
            username='testuser',
            password='testpass',
            verify_auth=False
        )
        
        # Verify credentials were stored
        creds = auth_manager.get_credentials('registry.example.com')
        assert creds is not None
        assert creds.username == 'testuser'
    
    def test_login_verification_failure(self, auth_manager):
        """Test login with invalid credentials raises error."""
        with patch('derpy.registry.client.RegistryClient') as mock_client_class:
            # Mock registry client verification failure
            mock_client = MagicMock()
            mock_client.verify_authentication.return_value = False
            mock_client_class.return_value.__enter__.return_value = mock_client
            
            with pytest.raises(InvalidCredentialsError) as exc_info:
                auth_manager.login(
                    registry='registry.example.com',
                    username='testuser',
                    password='wrongpass',
                    verify_auth=True
                )
            
            assert 'invalid credentials' in str(exc_info.value).lower()
            assert 'registry.example.com' in str(exc_info.value)
    
    def test_login_multiple_registries(self, auth_manager):
        """Test storing credentials for multiple registries."""
        # Login to multiple registries
        auth_manager.login('registry1.example.com', 'user1', 'pass1', verify_auth=False)
        auth_manager.login('registry2.example.com', 'user2', 'pass2', verify_auth=False)
        auth_manager.login('docker.io', 'user3', 'pass3', verify_auth=False)
        
        # Verify all credentials are stored
        creds1 = auth_manager.get_credentials('registry1.example.com')
        creds2 = auth_manager.get_credentials('registry2.example.com')
        creds3 = auth_manager.get_credentials('docker.io')
        
        assert creds1.username == 'user1'
        assert creds2.username == 'user2'
        assert creds3.username == 'user3'
    
    def test_logout_removes_credentials(self, auth_manager):
        """Test logout removes stored credentials."""
        # Store credentials
        auth_manager.login('registry.example.com', 'testuser', 'testpass', verify_auth=False)
        
        # Verify credentials exist
        assert auth_manager.get_credentials('registry.example.com') is not None
        
        # Logout
        result = auth_manager.logout('registry.example.com')
        
        assert result is True
        assert auth_manager.get_credentials('registry.example.com') is None
    
    def test_logout_nonexistent_registry(self, auth_manager):
        """Test logout from registry with no stored credentials."""
        result = auth_manager.logout('nonexistent.example.com')
        
        assert result is False
    
    def test_get_credentials_nonexistent(self, auth_manager):
        """Test getting credentials for nonexistent registry."""
        creds = auth_manager.get_credentials('nonexistent.example.com')
        
        assert creds is None
    
    def test_list_registries(self, auth_manager):
        """Test listing all registries with stored credentials."""
        # Store credentials for multiple registries
        auth_manager.login('registry1.example.com', 'user1', 'pass1', verify_auth=False)
        auth_manager.login('registry2.example.com', 'user2', 'pass2', verify_auth=False)
        auth_manager.login('docker.io', 'user3', 'pass3', verify_auth=False)
        
        registries = auth_manager.list_registries()
        
        assert len(registries) == 3
        assert 'registry1.example.com' in registries
        assert 'registry2.example.com' in registries
        assert 'registry-1.docker.io' in registries  # Normalized
    
    def test_list_registries_empty(self, auth_manager):
        """Test listing registries when none are stored."""
        registries = auth_manager.list_registries()
        
        assert registries == []
    
    def test_file_permissions_set_correctly(self, auth_manager):
        """Test that auth file has correct permissions (0600)."""
        auth_manager.login('registry.example.com', 'testuser', 'testpass', verify_auth=False)
        
        # Check file permissions
        file_stat = os.stat(auth_manager.auth_file)
        file_mode = stat.S_IMODE(file_stat.st_mode)
        
        # Should be 0600 (owner read/write only)
        expected_mode = stat.S_IRUSR | stat.S_IWUSR
        assert file_mode == expected_mode
    
    def test_load_auth_file_with_auths_wrapper(self, auth_manager):
        """Test loading auth file with 'auths' wrapper."""
        # Create auth file with 'auths' wrapper
        auth_data = {
            'auths': {
                'registry.example.com': {
                    'username': 'testuser',
                    'password': base64.b64encode(b'testpass').decode('utf-8')
                }
            }
        }
        
        with open(auth_manager.auth_file, 'w') as f:
            json.dump(auth_data, f)
        
        # Load credentials
        creds = auth_manager.get_credentials('registry.example.com')
        
        assert creds is not None
        assert creds.username == 'testuser'
    
    def test_load_auth_file_without_auths_wrapper(self, auth_manager):
        """Test loading auth file without 'auths' wrapper."""
        # Create auth file without 'auths' wrapper
        auth_data = {
            'registry.example.com': {
                'username': 'testuser',
                'password': base64.b64encode(b'testpass').decode('utf-8')
            }
        }
        
        with open(auth_manager.auth_file, 'w') as f:
            json.dump(auth_data, f)
        
        # Load credentials
        creds = auth_manager.get_credentials('registry.example.com')
        
        assert creds is not None
        assert creds.username == 'testuser'
    
    def test_load_auth_file_invalid_json(self, auth_manager):
        """Test loading invalid JSON raises error."""
        # Write invalid JSON
        with open(auth_manager.auth_file, 'w') as f:
            f.write('{ invalid json }')
        
        with pytest.raises(CredentialStorageError) as exc_info:
            auth_manager.get_credentials('registry.example.com')
        
        assert 'failed to parse' in str(exc_info.value).lower()
    
    def test_load_auth_file_invalid_format(self, auth_manager):
        """Test loading auth file with invalid format."""
        # Write invalid format (not a dict)
        with open(auth_manager.auth_file, 'w') as f:
            json.dump(['not', 'a', 'dict'], f)
        
        with pytest.raises(CredentialStorageError) as exc_info:
            auth_manager.get_credentials('registry.example.com')
        
        assert 'invalid auth file format' in str(exc_info.value).lower()
    
    def test_credentials_persist_across_instances(self):
        """Test credentials persist across AuthManager instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_auth_file = Path(tmpdir) / 'auth.json'
            
            # Create first instance and store credentials
            manager1 = AuthManager(auth_file=temp_auth_file)
            manager1.login('registry.example.com', 'testuser', 'testpass', verify_auth=False)
            
            # Create second instance and retrieve credentials
            manager2 = AuthManager(auth_file=temp_auth_file)
            creds = manager2.get_credentials('registry.example.com')
            
            assert creds is not None
            assert creds.username == 'testuser'
            assert creds.decode_password() == 'testpass'
    
    def test_password_encoding_decoding(self, auth_manager):
        """Test password is properly encoded and decoded."""
        password = 'my$ecure!P@ssw0rd'
        
        auth_manager.login('registry.example.com', 'testuser', password, verify_auth=False)
        
        # Retrieve and decode
        creds = auth_manager.get_credentials('registry.example.com')
        decoded_password = creds.decode_password()
        
        assert decoded_password == password
    
    def test_registry_url_normalization_in_storage(self, auth_manager):
        """Test that registry URLs are normalized when stored."""
        # Login with various forms of Docker Hub
        auth_manager.login('docker.io', 'user1', 'pass1', verify_auth=False)
        
        # Try to retrieve with different alias
        creds = auth_manager.get_credentials('registry.hub.docker.com')
        
        assert creds is not None
        assert creds.username == 'user1'
    
    def test_login_updates_existing_credentials(self, auth_manager):
        """Test that login updates existing credentials."""
        # Store initial credentials
        auth_manager.login('registry.example.com', 'user1', 'pass1', verify_auth=False)
        
        # Update credentials
        auth_manager.login('registry.example.com', 'user2', 'pass2', verify_auth=False)
        
        # Verify updated credentials
        creds = auth_manager.get_credentials('registry.example.com')
        assert creds.username == 'user2'
        assert creds.decode_password() == 'pass2'
    
    def test_empty_auth_file_returns_empty_dict(self, auth_manager):
        """Test that non-existent auth file returns empty dict."""
        # Ensure file doesn't exist
        if auth_manager.auth_file.exists():
            auth_manager.auth_file.unlink()
        
        auths = auth_manager._load_auth_file()
        
        assert auths == {}
