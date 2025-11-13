"""Additional tests for RegistryClient to increase coverage."""

import pytest
from unittest.mock import Mock, patch
from derpy.registry.client import RegistryClient
from derpy.core.config import RegistryConfig
from derpy.core.exceptions import RegistryError


class TestRegistryClientValidation:
    """Test URL validation in RegistryClient."""
    
    def test_validate_empty_url(self):
        """Test that empty URL raises error."""
        with pytest.raises(RegistryError, match="cannot be empty"):
            config = RegistryConfig(url="")
            RegistryClient(config)
    
    def test_validate_invalid_url_format(self):
        """Test that invalid URL format raises error."""
        with pytest.raises(RegistryError, match="Invalid registry URL"):
            config = RegistryConfig(url="not-a-valid-url")
            RegistryClient(config)
    
    def test_validate_invalid_scheme(self):
        """Test that invalid scheme raises error."""
        with pytest.raises(RegistryError):
            config = RegistryConfig(url="ftp://registry.example.com")
            RegistryClient(config)
    
    def test_normalize_url_with_trailing_slash(self):
        """Test URL normalization removes trailing slash."""
        config = RegistryConfig(url="https://registry.example.com/")
        client = RegistryClient(config)
        
        assert client.registry_url == "https://registry.example.com"
        assert not client.registry_url.endswith("/")
    
    def test_normalize_url_without_trailing_slash(self):
        """Test URL normalization preserves URL without trailing slash."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        assert client.registry_url == "https://registry.example.com"


class TestRegistryClientImageReference:
    """Test image reference parsing."""
    
    def test_parse_image_reference_with_tag(self):
        """Test parsing image reference with tag."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        repo, tag = client._parse_image_reference("myapp:v1.0")
        
        assert repo == "myapp"
        assert tag == "v1.0"
    
    def test_parse_image_reference_without_tag(self):
        """Test parsing image reference without tag defaults to latest."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        repo, tag = client._parse_image_reference("myapp")
        
        assert repo == "myapp"
        assert tag == "latest"
    
    def test_parse_image_reference_with_org(self):
        """Test parsing image reference with organization."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        repo, tag = client._parse_image_reference("myorg/myapp:v2.0")
        
        assert repo == "myorg/myapp"
        assert tag == "v2.0"
    
    def test_parse_image_reference_empty_repository(self):
        """Test parsing empty repository raises error."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        with pytest.raises(RegistryError, match="repository cannot be empty"):
            client._parse_image_reference(":latest")
    
    def test_parse_image_reference_invalid_repository_uppercase(self):
        """Test parsing repository with uppercase raises error."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        with pytest.raises(RegistryError, match="Invalid repository name"):
            client._parse_image_reference("MyApp:latest")
    
    def test_parse_image_reference_invalid_tag_format(self):
        """Test parsing invalid tag format raises error."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        with pytest.raises(RegistryError, match="Invalid tag format"):
            client._parse_image_reference("myapp:-invalid")


class TestRegistryClientURLGeneration:
    """Test URL generation methods."""
    
    def test_get_blob_upload_url(self):
        """Test blob upload URL generation."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        url = client._get_blob_upload_url("myrepo")
        
        assert url == "https://registry.example.com/v2/myrepo/blobs/uploads/"
    
    def test_get_blob_url(self):
        """Test blob URL generation."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        url = client._get_blob_url("myrepo", "sha256:abc123")
        
        assert url == "https://registry.example.com/v2/myrepo/blobs/sha256:abc123"
    
    def test_get_manifest_url(self):
        """Test manifest URL generation."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        url = client._get_manifest_url("myrepo", "latest")
        
        assert url == "https://registry.example.com/v2/myrepo/manifests/latest"


class TestRegistryClientBlobOperations:
    """Test blob operations with mocking."""
    
    def test_blob_exists_true(self):
        """Test blob_exists returns True when blob exists."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        mock_response = Mock()
        mock_response.status_code = 200
        client.session.head = Mock(return_value=mock_response)
        
        result = client.blob_exists("myrepo", "sha256:abc123")
        
        assert result is True
    
    def test_blob_exists_false(self):
        """Test blob_exists returns False when blob doesn't exist."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        mock_response = Mock()
        mock_response.status_code = 404
        client.session.head = Mock(return_value=mock_response)
        
        result = client.blob_exists("myrepo", "sha256:abc123")
        
        assert result is False
    
    def test_blob_exists_error(self):
        """Test blob_exists raises error on request failure."""
        import requests
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        client.session.head = Mock(side_effect=requests.RequestException("Network error"))
        
        with pytest.raises(RegistryError, match="Failed to check blob existence"):
            client.blob_exists("myrepo", "sha256:abc123")


class TestRegistryClientUploadBlob:
    """Test blob upload functionality."""
    
    def test_upload_blob_already_exists(self):
        """Test upload_blob skips upload if blob exists."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        # Mock blob_exists to return True
        client.blob_exists = Mock(return_value=True)
        
        progress_called = []
        def progress_callback(uploaded, total):
            progress_called.append((uploaded, total))
        
        client.upload_blob("myrepo", b"data", "sha256:abc123", progress_callback)
        
        # Should call progress callback with full size
        assert len(progress_called) == 1
        assert progress_called[0] == (4, 4)
    
    def test_upload_blob_initiate_failure(self):
        """Test upload_blob raises error if initiation fails."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        client.blob_exists = Mock(return_value=False)
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal error"
        client.session.post = Mock(return_value=mock_response)
        
        with pytest.raises(RegistryError, match="Failed to initiate blob upload"):
            client.upload_blob("myrepo", b"data", "sha256:abc123")
    
    def test_upload_blob_no_location_header(self):
        """Test upload_blob raises error if no Location header."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        client.blob_exists = Mock(return_value=False)
        
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.headers = {}
        client.session.post = Mock(return_value=mock_response)
        
        with pytest.raises(RegistryError, match="did not provide upload location"):
            client.upload_blob("myrepo", b"data", "sha256:abc123")
    
    def test_upload_blob_timeout(self):
        """Test upload_blob raises error on timeout."""
        import requests
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        client.blob_exists = Mock(return_value=False)
        client.session.post = Mock(side_effect=requests.Timeout("Upload timeout"))
        
        with pytest.raises(RegistryError, match="Blob upload timeout"):
            client.upload_blob("myrepo", b"data", "sha256:abc123")


class TestRegistryClientManifestOperations:
    """Test manifest operations."""
    
    def test_upload_manifest_success(self):
        """Test successful manifest upload."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {'Docker-Content-Digest': 'sha256:manifest123'}
        client.session.put = Mock(return_value=mock_response)
        
        digest = client.upload_manifest(
            "myrepo",
            "latest",
            b'{"test": "manifest"}',
            "application/vnd.oci.image.manifest.v1+json"
        )
        
        assert digest == "sha256:manifest123"
    
    def test_upload_manifest_failure(self):
        """Test manifest upload failure."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server error"
        client.session.put = Mock(return_value=mock_response)
        
        with pytest.raises(RegistryError, match="Failed to upload manifest"):
            client.upload_manifest(
                "myrepo",
                "latest",
                b'{"test": "manifest"}',
                "application/vnd.oci.image.manifest.v1+json"
            )
    
    def test_upload_manifest_timeout(self):
        """Test manifest upload timeout."""
        import requests
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        client.session.put = Mock(side_effect=requests.Timeout("Timeout"))
        
        with pytest.raises(RegistryError, match="Manifest upload timeout"):
            client.upload_manifest(
                "myrepo",
                "latest",
                b'{"test": "manifest"}',
                "application/vnd.oci.image.manifest.v1+json"
            )


class TestRegistryClientVerifyAuth:
    """Test authentication verification."""
    
    def test_verify_authentication_unexpected_status(self):
        """Test verify_authentication with unexpected status code."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        mock_response = Mock()
        mock_response.status_code = 500
        client.session.get = Mock(return_value=mock_response)
        
        with pytest.raises(RegistryError, match="unexpected status"):
            client.verify_authentication()
    
    def test_verify_authentication_timeout(self):
        """Test verify_authentication with timeout."""
        import requests
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        client.session.get = Mock(side_effect=requests.Timeout("Timeout"))
        
        with pytest.raises(RegistryError, match="connection timeout"):
            client.verify_authentication()
    
    def test_verify_authentication_connection_error(self):
        """Test verify_authentication with connection error."""
        import requests
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        client.session.get = Mock(side_effect=requests.ConnectionError("Cannot connect"))
        
        with pytest.raises(RegistryError, match="Failed to connect"):
            client.verify_authentication()


class TestRegistryClientClose:
    """Test client cleanup."""
    
    def test_close_session(self):
        """Test close method closes session."""
        config = RegistryConfig(url="https://registry.example.com")
        client = RegistryClient(config)
        
        client.session.close = Mock()
        client.close()
        
        client.session.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
