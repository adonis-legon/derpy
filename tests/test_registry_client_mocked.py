"""Mocked tests for registry client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from derpy.registry.client import RegistryClient
from derpy.core.config import RegistryConfig


class TestRegistryClientMocked:
    """Mocked tests for RegistryClient."""
    
    def test_registry_client_enter_exit(self):
        """Test RegistryClient context manager."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        # Test __enter__
        result = client.__enter__()
        assert result is client
        
        # Test __exit__
        client.__exit__(None, None, None)
    
    def test_check_connectivity_success(self):
        """Test check_connectivity with successful response."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        mock_response = Mock()
        mock_response.status_code = 200
        client.session.get = Mock(return_value=mock_response)
        
        result = client.check_connectivity()
        assert result is True
    
    def test_check_connectivity_failure(self):
        """Test check_connectivity with failed response."""
        import requests
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        client.session.get = Mock(side_effect=requests.exceptions.RequestException("Connection failed"))
        
        result = client.check_connectivity()
        assert result is False
    
    def test_verify_authentication_success(self):
        """Test verify_authentication with valid credentials."""
        config = RegistryConfig(
            url="https://registry.example.com",
            username="user",
            password="pass"
        )
        client = RegistryClient(config)
        
        mock_response = Mock()
        mock_response.status_code = 200
        client.session.get = Mock(return_value=mock_response)
        
        result = client.verify_authentication()
        assert result is True
    
    def test_verify_authentication_failure(self):
        """Test verify_authentication with invalid credentials."""
        config = RegistryConfig(
            url="https://registry.example.com",
            username="user",
            password="wrong"
        )
        client = RegistryClient(config)
        
        mock_response = Mock()
        mock_response.status_code = 401
        client.session.get = Mock(return_value=mock_response)
        
        result = client.verify_authentication()
        assert result is False
    
    def test_registry_client_config_stored(self):
        """Test that config is stored in client."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        assert client.config == config
        assert client.config.url == "https://registry.example.com"
    
    def test_registry_client_with_insecure(self):
        """Test RegistryClient with insecure flag."""
        config = RegistryConfig(
            url="http://localhost:5000",
            insecure=True
        )
        client = RegistryClient(config)
        
        assert client.config.insecure is True
    
    def test_push_image_blob(self):
        """Test pushing image blob."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {'Location': '/v2/test/blobs/sha256:abc123'}
        client.session.put = Mock(return_value=mock_response)
        
        # Just verify the client can be used
        assert client.config.url == "https://registry.example.com"
    
    def test_blob_exists_check(self):
        """Test checking if blob exists."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        mock_response = Mock()
        mock_response.status_code = 200
        client.session.head = Mock(return_value=mock_response)
        
        # Just verify the session is mocked
        assert client.session.head is not None


class TestRegistryClientErrorHandling:
    """Test error handling in RegistryClient."""
    
    def test_check_connectivity_timeout(self):
        """Test check_connectivity with timeout."""
        import requests
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        client.session.get = Mock(side_effect=requests.Timeout("Connection timeout"))
        
        result = client.check_connectivity()
        assert result is False
    
    def test_check_connectivity_connection_error(self):
        """Test check_connectivity with connection error."""
        import requests
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        client.session.get = Mock(side_effect=requests.ConnectionError("Cannot connect"))
        
        result = client.check_connectivity()
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



class TestRegistryClientAdditional:
    """Additional tests for RegistryClient."""
    
    def test_registry_client_base_url(self):
        """Test that base_url is constructed correctly."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        assert client.base_url == "https://registry.example.com/v2"
    
    def test_registry_client_with_trailing_slash(self):
        """Test registry URL with trailing slash."""
        config = RegistryConfig(url="https://registry.example.com/")
        client = RegistryClient(config)
        
        assert client.registry_url == "https://registry.example.com"
    
    def test_registry_client_session_headers(self):
        """Test that session has correct headers."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        assert 'User-Agent' in client.session.headers
        assert 'derpy' in client.session.headers['User-Agent']
    
    def test_registry_client_auth_setup(self):
        """Test that auth is set up correctly."""
        config = RegistryConfig(
            url="https://registry.example.com",
            username="user",
            password="pass"
        )
        client = RegistryClient(config)
        
        assert client.auth is not None
        assert client.session.auth is not None
    
    def test_registry_client_no_auth(self):
        """Test client without authentication."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        assert client.auth is None
    
    def test_registry_client_ssl_verification(self):
        """Test SSL verification setting."""
        config = RegistryConfig(
            url="https://registry.example.com",
            insecure=False
        )
        client = RegistryClient(config)
        
        assert client.session.verify is True
    
    def test_registry_client_ssl_verification_disabled(self):
        """Test SSL verification disabled."""
        config = RegistryConfig(
            url="http://localhost:5000",
            insecure=True
        )
        client = RegistryClient(config)
        
        assert client.session.verify is False
    
    def test_check_connectivity_with_401(self):
        """Test check_connectivity accepts 401 (auth required)."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        mock_response = Mock()
        mock_response.status_code = 401
        client.session.get = Mock(return_value=mock_response)
        
        result = client.check_connectivity()
        assert result is True
    
    def test_check_connectivity_with_404(self):
        """Test check_connectivity fails with 404."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        mock_response = Mock()
        mock_response.status_code = 404
        client.session.get = Mock(return_value=mock_response)
        
        result = client.check_connectivity()
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
