"""Tests for registry client."""

import pytest
from derpy.registry.client import RegistryClient, RegistryConfig, RegistryError


class TestRegistryClient:
    """Tests for RegistryClient."""
    
    def test_registry_client_initialization(self):
        """Test creating RegistryClient instance."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config)
        assert client is not None
        assert hasattr(client, 'config')
        assert client.config.url == "https://registry.example.com"
    
    def test_registry_client_with_credentials(self):
        """Test RegistryClient with credentials."""
        config = RegistryConfig(
            url="https://registry.example.com",
            username="testuser",
            password="testpass"
        )
        client = RegistryClient(config)
        assert client.config.username == "testuser"
        assert client.config.password == "testpass"
    
    def test_registry_client_insecure_flag(self):
        """Test RegistryClient with insecure flag."""
        config = RegistryConfig(
            url="http://localhost:5000",
            username="user",
            password="pass",
            insecure=True
        )
        client = RegistryClient(config)
        assert client.config.insecure is True
    
    def test_registry_client_has_required_methods(self):
        """Test RegistryClient has required methods."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config)
        
        assert hasattr(client, 'check_connectivity')
        assert hasattr(client, 'verify_authentication')
        assert hasattr(client, 'push_image')
        
        assert callable(getattr(client, 'check_connectivity', None))
        assert callable(getattr(client, 'verify_authentication', None))
        assert callable(getattr(client, 'push_image', None))
    
    def test_registry_client_context_manager(self):
        """Test RegistryClient as context manager."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        
        # Should support context manager protocol
        with RegistryClient(config) as client:
            assert client is not None
    
    def test_registry_error_exception(self):
        """Test RegistryError exception."""
        error = RegistryError("Test error")
        assert isinstance(error, Exception)
        assert "Test error" in str(error)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
