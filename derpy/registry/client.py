"""OCI registry client implementation.

This module implements the OCI Distribution Specification for pushing and
pulling container images to/from remote registries.
"""

import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse, urljoin
import requests
from requests.auth import HTTPBasicAuth

from derpy.core.config import RegistryConfig
from derpy.core.exceptions import (
    RegistryError,
    RegistryConnectionError,
    RegistryAuthenticationError,
    ImagePushError
)


class RegistryClient:
    """Client for interacting with OCI-compliant container registries.
    
    Implements the OCI Distribution Specification for image distribution.
    """
    
    # OCI Distribution API version
    API_VERSION = "v2"
    
    # Registry URL pattern validation
    REGISTRY_URL_PATTERN = re.compile(
        r'^https?://[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?'
        r'(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*'
        r'(:[0-9]{1,5})?(/.*)?$'
    )
    
    def __init__(self, registry_config: RegistryConfig):
        """Initialize registry client.
        
        Args:
            registry_config: Registry configuration with URL and credentials
            
        Raises:
            RegistryError: If registry configuration is invalid
        """
        self.config = registry_config
        self._validate_registry_url(registry_config.url)
        
        # Normalize registry URL
        self.registry_url = self._normalize_url(registry_config.url)
        self.base_url = f"{self.registry_url}/{self.API_VERSION}"
        
        # Setup authentication
        self.auth: Optional[HTTPBasicAuth] = None
        if registry_config.username and registry_config.password:
            self.auth = HTTPBasicAuth(
                registry_config.username,
                registry_config.password
            )
        
        # Setup session
        self.session = requests.Session()
        if self.auth:
            self.session.auth = self.auth
        
        # Configure SSL verification
        self.session.verify = not registry_config.insecure
        
        # Set default headers
        self.session.headers.update({
            'User-Agent': 'derpy/0.1.0',
        })
    
    def _validate_registry_url(self, url: str) -> None:
        """Validate registry URL format.
        
        Args:
            url: Registry URL to validate
            
        Raises:
            RegistryError: If URL is invalid
        """
        if not url:
            raise RegistryError("Registry URL cannot be empty")
        
        if not self.REGISTRY_URL_PATTERN.match(url):
            raise RegistryError(f"Invalid registry URL format: {url}")
        
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            raise RegistryError(
                f"Registry URL must use http or https scheme: {url}"
            )
    
    def _normalize_url(self, url: str) -> str:
        """Normalize registry URL by removing trailing slashes.
        
        Args:
            url: Registry URL to normalize
            
        Returns:
            Normalized URL
        """
        return url.rstrip('/')
    
    def check_connectivity(self) -> bool:
        """Check if the registry is reachable and supports OCI distribution.
        
        Performs a GET request to the /v2/ endpoint to verify registry
        availability and API version support.
        
        Returns:
            True if registry is reachable and compatible, False otherwise
        """
        try:
            response = self.session.get(
                self.base_url + "/",
                timeout=10
            )
            
            # Registry should return 200 or 401 (if auth required)
            if response.status_code in (200, 401):
                return True
            
            return False
            
        except requests.exceptions.RequestException:
            return False
    
    def verify_authentication(self) -> bool:
        """Verify that authentication credentials are valid.
        
        Returns:
            True if authenticated successfully, False otherwise
            
        Raises:
            RegistryError: If registry is unreachable
        """
        try:
            response = self.session.get(
                self.base_url + "/",
                timeout=10
            )
            
            # 200 means authenticated or no auth required
            if response.status_code == 200:
                return True
            
            # 401 means authentication failed
            if response.status_code == 401:
                return False
            
            # Other status codes indicate registry issues
            raise RegistryError(
                f"Registry returned unexpected status: {response.status_code}"
            )
            
        except requests.exceptions.Timeout:
            raise RegistryError("Registry connection timeout")
        except requests.exceptions.ConnectionError as e:
            raise RegistryError(f"Failed to connect to registry: {e}")
        except requests.exceptions.RequestException as e:
            raise RegistryError(f"Registry request failed: {e}")
    
    def _parse_image_reference(self, image_ref: str) -> tuple[str, str]:
        """Parse image reference into repository and tag.
        
        Args:
            image_ref: Image reference (e.g., "myapp:latest" or "org/myapp:v1.0")
            
        Returns:
            Tuple of (repository, tag)
            
        Raises:
            RegistryError: If image reference format is invalid
        """
        if ':' in image_ref:
            repository, tag = image_ref.rsplit(':', 1)
        else:
            repository = image_ref
            tag = 'latest'
        
        if not repository:
            raise RegistryError("Image repository cannot be empty")
        
        if not tag:
            raise RegistryError("Image tag cannot be empty")
        
        # Validate repository name format
        # Repository names must be lowercase and can contain slashes
        if not re.match(r'^[a-z0-9]+([._-][a-z0-9]+)*(\/[a-z0-9]+([._-][a-z0-9]+)*)*$', repository):
            raise RegistryError(
                f"Invalid repository name format: {repository}. "
                "Repository names must be lowercase and can contain "
                "alphanumeric characters, dots, dashes, underscores, and slashes."
            )
        
        # Validate tag format
        if not re.match(r'^[a-zA-Z0-9_][a-zA-Z0-9._-]{0,127}$', tag):
            raise RegistryError(
                f"Invalid tag format: {tag}. "
                "Tags must start with alphanumeric or underscore and can contain "
                "alphanumeric characters, dots, dashes, and underscores (max 128 chars)."
            )
        
        return repository, tag
    
    def _get_blob_upload_url(self, repository: str) -> str:
        """Get URL for initiating blob upload.
        
        Args:
            repository: Repository name
            
        Returns:
            Blob upload URL
        """
        return f"{self.base_url}/{repository}/blobs/uploads/"
    
    def _get_blob_url(self, repository: str, digest: str) -> str:
        """Get URL for blob operations.
        
        Args:
            repository: Repository name
            digest: Blob digest
            
        Returns:
            Blob URL
        """
        return f"{self.base_url}/{repository}/blobs/{digest}"
    
    def _get_manifest_url(self, repository: str, reference: str) -> str:
        """Get URL for manifest operations.
        
        Args:
            repository: Repository name
            reference: Tag or digest
            
        Returns:
            Manifest URL
        """
        return f"{self.base_url}/{repository}/manifests/{reference}"
    
    def blob_exists(self, repository: str, digest: str) -> bool:
        """Check if a blob exists in the registry.
        
        Args:
            repository: Repository name
            digest: Blob digest
            
        Returns:
            True if blob exists, False otherwise
            
        Raises:
            RegistryError: If check fails
        """
        try:
            url = self._get_blob_url(repository, digest)
            response = self.session.head(url, timeout=10)
            
            return response.status_code == 200
            
        except requests.exceptions.RequestException as e:
            raise RegistryError(f"Failed to check blob existence: {e}")
    
    def upload_blob(
        self,
        repository: str,
        blob_data: bytes,
        digest: str,
        progress_callback: Optional[callable] = None
    ) -> None:
        """Upload a blob to the registry.
        
        Uses the monolithic upload approach for simplicity.
        
        Args:
            repository: Repository name
            blob_data: Blob content
            digest: Expected digest of the blob
            progress_callback: Optional callback for progress tracking (bytes_uploaded, total_bytes)
            
        Raises:
            RegistryError: If upload fails
        """
        try:
            # Check if blob already exists
            if self.blob_exists(repository, digest):
                if progress_callback:
                    progress_callback(len(blob_data), len(blob_data))
                return
            
            # Initiate upload
            upload_url = self._get_blob_upload_url(repository)
            response = self.session.post(upload_url, timeout=30)
            
            if response.status_code not in (202, 201):
                raise RegistryError(
                    f"Failed to initiate blob upload: {response.status_code} {response.text}"
                )
            
            # Get upload location from response
            location = response.headers.get('Location')
            if not location:
                raise RegistryError("Registry did not provide upload location")
            
            # Make location absolute if it's relative
            if not location.startswith('http'):
                location = urljoin(self.registry_url, location)
            
            # Add digest parameter to complete upload
            if '?' in location:
                upload_location = f"{location}&digest={digest}"
            else:
                upload_location = f"{location}?digest={digest}"
            
            # Upload blob data
            headers = {
                'Content-Type': 'application/octet-stream',
                'Content-Length': str(len(blob_data))
            }
            
            response = self.session.put(
                upload_location,
                data=blob_data,
                headers=headers,
                timeout=300
            )
            
            if response.status_code not in (201, 204):
                raise RegistryError(
                    f"Failed to upload blob: {response.status_code} {response.text}"
                )
            
            # Report progress
            if progress_callback:
                progress_callback(len(blob_data), len(blob_data))
            
        except RegistryError:
            raise
        except requests.exceptions.Timeout:
            raise RegistryError("Blob upload timeout")
        except requests.exceptions.RequestException as e:
            raise RegistryError(f"Failed to upload blob: {e}")
    
    def upload_manifest(
        self,
        repository: str,
        tag: str,
        manifest_data: bytes,
        media_type: str
    ) -> str:
        """Upload an image manifest to the registry.
        
        Args:
            repository: Repository name
            tag: Image tag
            manifest_data: Manifest JSON content
            media_type: Manifest media type
            
        Returns:
            Digest of the uploaded manifest
            
        Raises:
            RegistryError: If upload fails
        """
        try:
            url = self._get_manifest_url(repository, tag)
            
            headers = {
                'Content-Type': media_type
            }
            
            response = self.session.put(
                url,
                data=manifest_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code not in (201, 200):
                raise RegistryError(
                    f"Failed to upload manifest: {response.status_code} {response.text}"
                )
            
            # Get digest from response header
            digest = response.headers.get('Docker-Content-Digest')
            if not digest:
                # Calculate digest if not provided
                import hashlib
                digest = f"sha256:{hashlib.sha256(manifest_data).hexdigest()}"
            
            return digest
            
        except RegistryError:
            raise
        except requests.exceptions.Timeout:
            raise RegistryError("Manifest upload timeout")
        except requests.exceptions.RequestException as e:
            raise RegistryError(f"Failed to upload manifest: {e}")
    
    def push_image(
        self,
        image_ref: str,
        manifest_data: bytes,
        config_data: bytes,
        layers_data: list[tuple[str, bytes]],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Push a complete image to the registry.
        
        Args:
            image_ref: Image reference (e.g., "myapp:latest")
            manifest_data: Manifest JSON bytes
            config_data: Config JSON bytes
            layers_data: List of (digest, layer_bytes) tuples
            progress_callback: Optional callback for progress tracking
            
        Returns:
            Dictionary with push results including manifest digest
            
        Raises:
            RegistryError: If push fails
        """
        try:
            # Parse image reference
            repository, tag = self._parse_image_reference(image_ref)
            
            # Calculate total size for progress tracking
            total_size = len(config_data) + sum(len(data) for _, data in layers_data)
            uploaded_size = 0
            
            # Upload config blob
            import hashlib
            config_digest = f"sha256:{hashlib.sha256(config_data).hexdigest()}"
            
            def config_progress(uploaded, total):
                nonlocal uploaded_size
                if progress_callback:
                    progress_callback(uploaded_size + uploaded, total_size)
            
            self.upload_blob(repository, config_data, config_digest, config_progress)
            uploaded_size += len(config_data)
            
            # Upload layer blobs
            for layer_digest, layer_data in layers_data:
                def layer_progress(uploaded, total):
                    nonlocal uploaded_size
                    if progress_callback:
                        progress_callback(uploaded_size + uploaded, total_size)
                
                self.upload_blob(repository, layer_data, layer_digest, layer_progress)
                uploaded_size += len(layer_data)
            
            # Upload manifest
            from derpy.oci.models import MEDIA_TYPE_IMAGE_MANIFEST
            manifest_digest = self.upload_manifest(
                repository,
                tag,
                manifest_data,
                MEDIA_TYPE_IMAGE_MANIFEST
            )
            
            return {
                'repository': repository,
                'tag': tag,
                'manifest_digest': manifest_digest,
                'size': total_size
            }
            
        except RegistryError:
            raise
        except Exception as e:
            raise RegistryError(f"Failed to push image: {e}")
    
    def download_manifest(
        self,
        repository: str,
        reference: str
    ) -> tuple[bytes, str]:
        """Download image manifest from registry.
        
        Fetches the manifest for a specific image tag or digest. Supports both
        Docker v2 and OCI manifest formats.
        
        Args:
            repository: Repository name (e.g., "library/ubuntu")
            reference: Tag or digest (e.g., "22.04" or "sha256:abc...")
            
        Returns:
            Tuple of (manifest_bytes, media_type)
            
        Raises:
            RegistryError: If download fails
        """
        try:
            url = self._get_manifest_url(repository, reference)
            
            # Accept both Docker v2 and OCI manifest formats
            headers = {
                'Accept': ', '.join([
                    'application/vnd.oci.image.manifest.v1+json',
                    'application/vnd.docker.distribution.manifest.v2+json',
                    'application/vnd.docker.distribution.manifest.list.v2+json'
                ])
            }
            
            response = self.session.get(url, headers=headers, timeout=30)
            
            if response.status_code == 404:
                raise RegistryError(
                    f"Manifest not found: {repository}:{reference}"
                )
            
            if response.status_code != 200:
                raise RegistryError(
                    f"Failed to download manifest: {response.status_code} {response.text}"
                )
            
            # Get media type from response
            media_type = response.headers.get('Content-Type', 'application/vnd.oci.image.manifest.v1+json')
            
            return response.content, media_type
            
        except RegistryError:
            raise
        except requests.exceptions.Timeout:
            raise RegistryError("Manifest download timeout")
        except requests.exceptions.RequestException as e:
            raise RegistryError(f"Failed to download manifest: {e}")
    
    def download_blob(
        self,
        repository: str,
        digest: str,
        progress_callback: Optional[callable] = None
    ) -> bytes:
        """Download a blob (layer or config) from registry.
        
        Downloads a content-addressable blob identified by its digest.
        
        Args:
            repository: Repository name
            digest: Blob digest (e.g., "sha256:abc...")
            progress_callback: Optional callback for progress tracking (bytes_downloaded, total_bytes)
            
        Returns:
            Blob content as bytes
            
        Raises:
            RegistryError: If download fails
        """
        try:
            url = self._get_blob_url(repository, digest)
            
            response = self.session.get(url, stream=True, timeout=30)
            
            if response.status_code == 404:
                raise RegistryError(
                    f"Blob not found: {digest}"
                )
            
            if response.status_code != 200:
                raise RegistryError(
                    f"Failed to download blob: {response.status_code} {response.text}"
                )
            
            # Get total size from headers
            total_size = int(response.headers.get('Content-Length', 0))
            
            # Download blob in chunks
            blob_data = bytearray()
            downloaded = 0
            
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    blob_data.extend(chunk)
                    downloaded += len(chunk)
                    
                    if progress_callback and total_size > 0:
                        progress_callback(downloaded, total_size)
            
            # Final progress update
            if progress_callback and total_size > 0:
                progress_callback(downloaded, total_size)
            
            return bytes(blob_data)
            
        except RegistryError:
            raise
        except requests.exceptions.Timeout:
            raise RegistryError("Blob download timeout")
        except requests.exceptions.RequestException as e:
            raise RegistryError(f"Failed to download blob: {e}")
    
    def pull_image(
        self,
        repository: str,
        tag: str,
        progress_callback: Optional[callable] = None
    ) -> tuple[bytes, bytes, list[tuple[str, bytes]]]:
        """Download complete image (manifest + config + all layers).
        
        Downloads all components of an image from the registry. This is the
        high-level method for pulling images.
        
        Args:
            repository: Repository name (e.g., "library/ubuntu")
            tag: Image tag (e.g., "22.04")
            progress_callback: Optional callback for overall progress
            
        Returns:
            Tuple of (manifest_bytes, config_bytes, [(layer_digest, layer_bytes), ...])
            
        Raises:
            RegistryError: If pull fails
        """
        try:
            # Download manifest
            manifest_bytes, media_type = self.download_manifest(repository, tag)
            
            # Parse manifest
            from derpy.oci.models import Manifest
            import json
            manifest_dict = json.loads(manifest_bytes.decode('utf-8'))
            manifest = Manifest.from_dict(manifest_dict)
            
            # Download config blob
            if not manifest.config:
                raise RegistryError("Manifest does not contain config descriptor")
            
            config_bytes = self.download_blob(
                repository,
                manifest.config.digest,
                progress_callback
            )
            
            # Download all layer blobs
            layers_data = []
            for i, layer_desc in enumerate(manifest.layers):
                layer_bytes = self.download_blob(
                    repository,
                    layer_desc.digest,
                    progress_callback
                )
                layers_data.append((layer_desc.digest, layer_bytes))
            
            return manifest_bytes, config_bytes, layers_data
            
        except RegistryError:
            raise
        except Exception as e:
            raise RegistryError(f"Failed to pull image: {e}")
    
    def close(self) -> None:
        """Close the registry client session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
