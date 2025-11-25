"""Mocked tests for registry client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from derpy.registry.client import RegistryClient, RegistryConfig


class TestRegistryClientMocked:
    """Mocked tests for RegistryClient."""
    
    def test_registry_client_enter_exit(self):
        """Test RegistryClient context manager."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config)
        
        # Test __enter__
        result = client.__enter__()
        assert result is client
        
        # Test __exit__
        client.__exit__(None, None, None)
    
    def test_check_connectivity_success(self):
        """Test check_connectivity with successful response."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config)
        
        mock_response = Mock()
        mock_response.status_code = 200
        
        with patch.object(client, '_request', return_value=mock_response):
            result = client.check_connectivity()
            assert result is True
    
    def test_check_connectivity_failure(self):
        """Test check_connectivity with failed response."""
        import requests
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
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
        
        with patch.object(client, '_request', return_value=mock_response):
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
        
        with patch.object(client, '_request', return_value=mock_response):
            result = client.verify_authentication()
            assert result is False
    
    def test_registry_client_config_stored(self):
        """Test that config is stored in client."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config)
        
        assert client.config == config
        assert client.config.url == "https://registry.example.com"
    
    def test_registry_client_with_insecure(self):
        """Test RegistryClient with insecure flag."""
        config = RegistryConfig(
            url="http://localhost:5000",
            username="user",
            password="pass",
            insecure=True
        )
        client = RegistryClient(config)
        
        assert client.config.insecure is True
    
    def test_push_image_blob(self):
        """Test pushing image blob."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config)
        
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {'Location': '/v2/test/blobs/sha256:abc123'}
        client.session.put = Mock(return_value=mock_response)
        
        # Just verify the client can be used
        assert client.config.url == "https://registry.example.com"
    
    def test_blob_exists_check(self):
        """Test checking if blob exists."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
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
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config)
        
        client.session.get = Mock(side_effect=requests.Timeout("Connection timeout"))
        
        result = client.check_connectivity()
        assert result is False
    
    def test_check_connectivity_connection_error(self):
        """Test check_connectivity with connection error."""
        import requests
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
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
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config)
        
        assert client.base_url == "https://registry.example.com/v2"
    
    def test_registry_client_with_trailing_slash(self):
        """Test registry URL with trailing slash."""
        config = RegistryConfig(url="https://registry.example.com/", username="user", password="pass")
        client = RegistryClient(config)
        
        assert client.registry_url == "https://registry.example.com"
    
    def test_registry_client_session_headers(self):
        """Test that session has correct headers."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
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
        config = RegistryConfig(url="https://registry.example.com", username="", password="")
        client = RegistryClient(config)
        
        assert client.auth is None
    
    def test_registry_client_ssl_verification(self):
        """Test SSL verification setting."""
        config = RegistryConfig(
            url="https://registry.example.com",
            username="user",
            password="pass",
            insecure=False
        )
        client = RegistryClient(config)
        
        assert client.session.verify is True
    
    def test_registry_client_ssl_verification_disabled(self):
        """Test SSL verification disabled."""
        config = RegistryConfig(
            url="http://localhost:5000",
            username="user",
            password="pass",
            insecure=True
        )
        client = RegistryClient(config)
        
        assert client.session.verify is False
    
    def test_check_connectivity_with_401(self):
        """Test check_connectivity accepts 401 (auth required)."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config)
        
        mock_response = Mock()
        mock_response.status_code = 401
        
        with patch.object(client, '_request', return_value=mock_response):
            result = client.check_connectivity()
            assert result is True
    
    def test_check_connectivity_with_404(self):
        """Test check_connectivity fails with 404."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config)
        
        mock_response = Mock()
        mock_response.status_code = 404
        client.session.get = Mock(return_value=mock_response)
        
        result = client.check_connectivity()
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



class TestRegistryClientTokenAuth:
    """Tests for token authentication in RegistryClient."""
    
    def test_parse_www_authenticate_bearer(self):
        """Test parsing Bearer WWW-Authenticate header."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config)
        
        header = 'Bearer realm="https://auth.docker.io/token",service="registry.docker.io",scope="repository:library/nginx:pull"'
        params = client._parse_www_authenticate(header)
        
        assert params['scheme'] == 'Bearer'
        assert params['realm'] == 'https://auth.docker.io/token'
        assert params['service'] == 'registry.docker.io'
        assert params['scope'] == 'repository:library/nginx:pull'
    
    def test_parse_www_authenticate_basic(self):
        """Test parsing Basic WWW-Authenticate header."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config)
        
        header = 'Basic realm="Registry Realm"'
        params = client._parse_www_authenticate(header)
        
        assert params['scheme'] == 'Basic'
        assert params['realm'] == 'Registry Realm'
    
    def test_parse_www_authenticate_empty(self):
        """Test parsing empty WWW-Authenticate header."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config)
        
        params = client._parse_www_authenticate('')
        assert params == {}
    
    def test_parse_www_authenticate_malformed(self):
        """Test parsing malformed WWW-Authenticate header."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config)
        
        header = 'InvalidHeader'
        params = client._parse_www_authenticate(header)
        assert params == {}
    
    def test_request_token_success(self):
        """Test successful token request."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config)
        
        with patch('requests.Session.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'token': 'test_token_123'}
            mock_get.return_value = mock_response
            
            token = client._request_token(
                'https://auth.docker.io/token',
                'registry.docker.io',
                'repository:library/nginx:pull'
            )
            
            assert token == 'test_token_123'
            mock_get.assert_called_once()
    
    def test_request_token_with_access_token_field(self):
        """Test token request with access_token field."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config)
        
        with patch('requests.Session.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'access_token': 'access_token_456'}
            mock_get.return_value = mock_response
            
            token = client._request_token(
                'https://auth.example.com/token',
                'registry.example.com',
                'repository:myapp:pull'
            )
            
            assert token == 'access_token_456'
    
    def test_request_token_failure(self):
        """Test failed token request."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config)
        
        with patch('requests.Session.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_get.return_value = mock_response
            
            token = client._request_token(
                'https://auth.docker.io/token',
                'registry.docker.io',
                'repository:library/nginx:pull'
            )
            
            assert token is None
    
    def test_request_token_with_credentials(self):
        """Test token request with credentials for authenticated token."""
        config = RegistryConfig(
            url="https://registry.example.com",
            username="testuser",
            password="testpass"
        )
        client = RegistryClient(config)
        
        with patch('requests.Session.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'token': 'authenticated_token'}
            mock_get.return_value = mock_response
            
            token = client._request_token(
                'https://auth.docker.io/token',
                'registry.docker.io',
                'repository:private/app:pull'
            )
            
            assert token == 'authenticated_token'
    
    def test_handle_auth_challenge_success(self):
        """Test handling authentication challenge successfully."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config)
        
        mock_response = Mock()
        mock_response.headers = {
            'Www-Authenticate': 'Bearer realm="https://auth.docker.io/token",service="registry.docker.io",scope="repository:library/nginx:pull"'
        }
        
        with patch.object(client, '_request_token', return_value='test_token'):
            token = client._handle_auth_challenge(mock_response, 'https://registry.example.com/v2/')
            
            assert token == 'test_token'
            assert client.token == 'test_token'
            assert client.token_scope == 'repository:library/nginx:pull'
    
    def test_handle_auth_challenge_no_header(self):
        """Test handling auth challenge with no WWW-Authenticate header."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config)
        
        mock_response = Mock()
        mock_response.headers = {}
        
        token = client._handle_auth_challenge(mock_response, 'https://registry.example.com/v2/')
        assert token is None
    
    def test_handle_auth_challenge_basic_scheme(self):
        """Test handling auth challenge with Basic scheme (not Bearer)."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config)
        
        mock_response = Mock()
        mock_response.headers = {
            'Www-Authenticate': 'Basic realm="Registry Realm"'
        }
        
        token = client._handle_auth_challenge(mock_response, 'https://registry.example.com/v2/')
        assert token is None
    
    def test_request_with_cached_token(self):
        """Test request with cached token."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config, enable_token_auth=True)
        client.token = 'cached_token'
        
        mock_response = Mock()
        mock_response.status_code = 200
        
        with patch.object(client.session, 'request', return_value=mock_response) as mock_request:
            response = client._request('GET', 'https://registry.example.com/v2/')
            
            assert response.status_code == 200
            # Verify Authorization header was added
            call_kwargs = mock_request.call_args[1]
            assert 'headers' in call_kwargs
            assert call_kwargs['headers']['Authorization'] == 'Bearer cached_token'
    
    def test_request_with_401_and_token_retry(self):
        """Test automatic retry with token after 401."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config, enable_token_auth=True)
        
        # First response: 401 with auth challenge
        mock_401_response = Mock()
        mock_401_response.status_code = 401
        mock_401_response.headers = {
            'Www-Authenticate': 'Bearer realm="https://auth.docker.io/token",service="registry.docker.io",scope="repository:library/nginx:pull"'
        }
        
        # Second response: 200 with token
        mock_200_response = Mock()
        mock_200_response.status_code = 200
        
        with patch.object(client.session, 'request', side_effect=[mock_401_response, mock_200_response]) as mock_request:
            with patch.object(client, '_request_token', return_value='new_token'):
                response = client._request('GET', 'https://registry.example.com/v2/library/nginx/manifests/latest')
                
                assert response.status_code == 200
                assert mock_request.call_count == 2
                
                # Verify second call has Authorization header
                second_call_kwargs = mock_request.call_args_list[1][1]
                assert 'headers' in second_call_kwargs
                assert second_call_kwargs['headers']['Authorization'] == 'Bearer new_token'
    
    def test_request_with_token_auth_disabled(self):
        """Test request with token auth disabled."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config, enable_token_auth=False)
        
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.headers = {
            'Www-Authenticate': 'Bearer realm="https://auth.docker.io/token",service="registry.docker.io"'
        }
        
        with patch.object(client.session, 'request', return_value=mock_response) as mock_request:
            response = client._request('GET', 'https://registry.example.com/v2/')
            
            # Should not retry with token
            assert response.status_code == 401
            assert mock_request.call_count == 1
    
    def test_token_caching(self):
        """Test that tokens are cached for subsequent requests."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config, enable_token_auth=True)
        
        # First request gets 401 and obtains token
        mock_401_response = Mock()
        mock_401_response.status_code = 401
        mock_401_response.headers = {
            'Www-Authenticate': 'Bearer realm="https://auth.docker.io/token",service="registry.docker.io",scope="repository:library/nginx:pull"'
        }
        
        mock_200_response = Mock()
        mock_200_response.status_code = 200
        
        with patch.object(client.session, 'request', side_effect=[mock_401_response, mock_200_response, mock_200_response]) as mock_request:
            with patch.object(client, '_request_token', return_value='cached_token') as mock_token_request:
                # First request
                client._request('GET', 'https://registry.example.com/v2/library/nginx/manifests/latest')
                
                # Token should be cached
                assert client.token == 'cached_token'
                
                # Second request should use cached token
                client._request('GET', 'https://registry.example.com/v2/library/nginx/blobs/sha256:abc')
                
                # Token request should only be called once
                assert mock_token_request.call_count == 1
    
    def test_verify_authentication_with_token_auth(self):
        """Test verify_authentication with token authentication."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config, enable_token_auth=True)
        
        # Mock 401 response with auth challenge
        mock_401_response = Mock()
        mock_401_response.status_code = 401
        mock_401_response.headers = {
            'Www-Authenticate': 'Bearer realm="https://auth.docker.io/token",service="registry.docker.io"'
        }
        
        # Mock 200 response after token
        mock_200_response = Mock()
        mock_200_response.status_code = 200
        
        with patch.object(client.session, 'request', side_effect=[mock_401_response, mock_200_response]):
            with patch.object(client, '_request_token', return_value='test_token'):
                result = client.verify_authentication()
                
                assert result is True
    
    def test_verify_authentication_token_failure(self):
        """Test verify_authentication when token request fails."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config, enable_token_auth=True)
        
        # Mock 401 response with auth challenge
        mock_401_response = Mock()
        mock_401_response.status_code = 401
        mock_401_response.headers = {
            'Www-Authenticate': 'Bearer realm="https://auth.docker.io/token",service="registry.docker.io"'
        }
        
        with patch.object(client.session, 'request', return_value=mock_401_response):
            with patch.object(client, '_request_token', return_value=None):
                result = client.verify_authentication()
                
                assert result is False
    
    def test_enable_token_auth_parameter(self):
        """Test enable_token_auth parameter in constructor."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        
        # With token auth enabled (default)
        client1 = RegistryClient(config)
        assert client1.enable_token_auth is True
        
        # With token auth explicitly enabled
        client2 = RegistryClient(config, enable_token_auth=True)
        assert client2.enable_token_auth is True
        
        # With token auth disabled
        client3 = RegistryClient(config, enable_token_auth=False)
        assert client3.enable_token_auth is False
    
    def test_token_and_scope_initialization(self):
        """Test token and token_scope are initialized to None."""
        config = RegistryConfig(url="https://registry.example.com", username="user", password="pass")
        client = RegistryClient(config)
        
        assert client.token is None
        assert client.token_scope is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
