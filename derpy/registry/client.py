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
from derpy.core.logging import get_logger


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
    
    def __init__(self, registry_config: RegistryConfig, enable_token_auth: bool = True):
        """Initialize registry client.
        
        Args:
            registry_config: Registry configuration with URL and credentials
            enable_token_auth: Enable automatic token authentication (default: True)
            
        Raises:
            RegistryError: If registry configuration is invalid
        """
        self.config = registry_config
        self._validate_registry_url(registry_config.url)
        
        # Normalize registry URL
        self.registry_url = self._normalize_url(registry_config.url)
        self.base_url = f"{self.registry_url}/{self.API_VERSION}"
        
        # Setup logging
        self.logger = get_logger("registry")
        
        # Setup authentication
        self.auth: Optional[HTTPBasicAuth] = None
        if registry_config.username and registry_config.password:
            self.auth = HTTPBasicAuth(
                registry_config.username,
                registry_config.password
            )
        
        # Token authentication support
        self.enable_token_auth = enable_token_auth
        self.token: Optional[str] = None
        self.token_scope: Optional[str] = None
        
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
            response = self._request('GET', self.base_url + "/", timeout=10)
            
            # Registry should return 200 or 401 (if auth required)
            if response.status_code in (200, 401):
                return True
            
            return False
            
        except requests.exceptions.RequestException:
            return False
    
    def verify_authentication(self) -> bool:
        """Verify that authentication credentials are valid.
        
        Tests credentials by making a GET request to the /v2/ endpoint.
        Handles both Basic and Bearer token authentication.
        
        Returns:
            True if authenticated successfully, False otherwise
            
        Raises:
            RegistryError: If registry is unreachable
        """
        try:
            response = self._request('GET', self.base_url + "/", timeout=10)
            
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
            response = self._request('HEAD', url, timeout=10)
            
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
            blob_size_mb = len(blob_data) / (1024 * 1024)
            self.logger.info(f"Uploading blob {digest[:12]}... ({blob_size_mb:.2f} MB)")
            
            # Check if blob already exists
            if self.blob_exists(repository, digest):
                self.logger.info(f"Blob {digest[:12]}... already exists, skipping upload")
                if progress_callback:
                    progress_callback(len(blob_data), len(blob_data))
                return
            
            # Initiate upload
            self.logger.debug(f"Initiating blob upload for {digest[:12]}...")
            upload_url = self._get_blob_upload_url(repository)
            response = self._request('POST', upload_url, timeout=30)
            
            if response.status_code not in (202, 201):
                raise RegistryError(
                    f"Failed to initiate blob upload: {response.status_code} {response.text}"
                )
            
            # Get upload location from response
            location = response.headers.get('Location')
            if not location:
                raise RegistryError("Registry did not provide upload location")
            
            self.logger.debug(f"Upload location: {location}")
            
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
            
            self.logger.debug(f"Uploading {blob_size_mb:.2f} MB to {upload_location[:100]}...")
            
            response = self._request(
                'PUT',
                upload_location,
                data=blob_data,
                headers=headers,
                timeout=600  # 10 minutes for large blob uploads
            )
            
            if response.status_code not in (201, 204):
                raise RegistryError(
                    f"Failed to upload blob: {response.status_code} {response.text}"
                )
            
            self.logger.info(f"Successfully uploaded blob {digest[:12]}... ({blob_size_mb:.2f} MB)")
            
            # Report progress
            if progress_callback:
                progress_callback(len(blob_data), len(blob_data))
            
        except RegistryError:
            raise
        except requests.exceptions.Timeout as e:
            self.logger.error(f"Blob upload timeout for {digest[:12]}... ({blob_size_mb:.2f} MB)")
            raise RegistryError(
                f"Blob upload timeout after 600 seconds. "
                f"The blob size is {blob_size_mb:.2f} MB. "
                f"This may be due to slow network connection or registry issues."
            )
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to upload blob {digest[:12]}...: {e}")
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
            
            response = self._request(
                'PUT',
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
            
            self.logger.info(f"Pushing image {repository}:{tag}")
            
            # Calculate total size for progress tracking
            total_size = len(config_data) + sum(len(data) for _, data in layers_data)
            uploaded_size = 0
            
            self.logger.info(f"Total upload size: {total_size / (1024 * 1024):.2f} MB")
            
            # Upload config blob
            import hashlib
            config_digest = f"sha256:{hashlib.sha256(config_data).hexdigest()}"
            
            self.logger.info(f"Uploading config blob...")
            
            def config_progress(uploaded, total):
                nonlocal uploaded_size
                if progress_callback:
                    progress_callback(uploaded_size + uploaded, total_size)
            
            self.upload_blob(repository, config_data, config_digest, config_progress)
            uploaded_size += len(config_data)
            
            # Upload layer blobs
            self.logger.info(f"Uploading {len(layers_data)} layer(s)...")
            for i, (layer_digest, layer_data) in enumerate(layers_data, 1):
                self.logger.info(f"Uploading layer {i}/{len(layers_data)}: {layer_digest[:12]}...")
                
                def layer_progress(uploaded, total):
                    nonlocal uploaded_size
                    if progress_callback:
                        progress_callback(uploaded_size + uploaded, total_size)
                
                self.upload_blob(repository, layer_data, layer_digest, layer_progress)
                uploaded_size += len(layer_data)
            
            # Upload manifest
            self.logger.info(f"Uploading manifest...")
            from derpy.oci.models import MEDIA_TYPE_IMAGE_MANIFEST
            manifest_digest = self.upload_manifest(
                repository,
                tag,
                manifest_data,
                MEDIA_TYPE_IMAGE_MANIFEST
            )
            
            self.logger.info(f"Successfully pushed image {repository}:{tag}")
            
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
            
            response = self._request('GET', url, headers=headers, timeout=30)
            
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
            
            response = self._request('GET', url, stream=True, timeout=30)
            
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
        progress_callback: Optional[callable] = None,
        platform: Optional[str] = None
    ) -> tuple[bytes, bytes, list[tuple[str, bytes]]]:
        """Download complete image (manifest + config + all layers).
        
        Downloads all components of an image from the registry. This is the
        high-level method for pulling images. Automatically handles manifest
        lists by selecting the appropriate platform-specific manifest.
        
        Args:
            repository: Repository name (e.g., "library/ubuntu")
            tag: Image tag (e.g., "22.04")
            progress_callback: Optional callback for overall progress
            platform: Platform string (e.g., "linux/amd64"). If None, uses current platform.
            
        Returns:
            Tuple of (manifest_bytes, config_bytes, [(layer_digest, layer_bytes), ...])
            
        Raises:
            RegistryError: If pull fails
        """
        try:
            import json
            import platform as platform_module
            
            # Download manifest
            manifest_bytes, media_type = self.download_manifest(repository, tag)
            manifest_dict = json.loads(manifest_bytes.decode('utf-8'))
            
            # Check if this is a manifest list (multi-platform)
            manifest_list_types = [
                'application/vnd.docker.distribution.manifest.list.v2+json',
                'application/vnd.oci.image.index.v1+json'
            ]
            
            if media_type in manifest_list_types or manifest_dict.get('mediaType') in manifest_list_types:
                # This is a manifest list - select platform-specific manifest
                self.logger.debug(f"Received manifest list, selecting platform-specific manifest")
                
                # Determine target platform
                if platform is None:
                    # Use current platform
                    os_name = platform_module.system().lower()
                    machine = platform_module.machine().lower()
                    
                    # Map machine architecture to Docker architecture names
                    arch_map = {
                        'x86_64': 'amd64',
                        'amd64': 'amd64',
                        'aarch64': 'arm64',
                        'arm64': 'arm64',
                        'armv7l': 'arm',
                        'armv6l': 'arm',
                    }
                    arch = arch_map.get(machine, machine)
                    platform = f"{os_name}/{arch}"
                
                # Parse platform string
                platform_parts = platform.split('/')
                target_os = platform_parts[0] if len(platform_parts) > 0 else 'linux'
                target_arch = platform_parts[1] if len(platform_parts) > 1 else 'amd64'
                target_variant = platform_parts[2] if len(platform_parts) > 2 else None
                
                # Find matching manifest in the list
                manifests = manifest_dict.get('manifests', [])
                selected_manifest = None
                
                for manifest_desc in manifests:
                    platform_info = manifest_desc.get('platform', {})
                    if (platform_info.get('os') == target_os and 
                        platform_info.get('architecture') == target_arch):
                        # Check variant if specified
                        if target_variant:
                            if platform_info.get('variant') == target_variant:
                                selected_manifest = manifest_desc
                                break
                        else:
                            selected_manifest = manifest_desc
                            break
                
                if not selected_manifest:
                    raise RegistryError(
                        f"No manifest found for platform {platform} in manifest list. "
                        f"Available platforms: {[m.get('platform') for m in manifests]}"
                    )
                
                # Download the platform-specific manifest
                manifest_digest = selected_manifest['digest']
                self.logger.debug(f"Selected manifest for {platform}: {manifest_digest}")
                manifest_bytes, media_type = self.download_manifest(repository, manifest_digest)
                manifest_dict = json.loads(manifest_bytes.decode('utf-8'))
            
            # Parse manifest (now guaranteed to be a single-platform manifest)
            from derpy.oci.models import Manifest
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
    
    def _parse_www_authenticate(self, header: str) -> Dict[str, str]:
        """Parse WWW-Authenticate header.
        
        Parses authentication challenges from WWW-Authenticate headers,
        supporting both Bearer and Basic authentication schemes.
        
        Example input:
            Bearer realm="https://auth.docker.io/token",
                   service="registry.docker.io",
                   scope="repository:library/nginx:pull"
        
        Args:
            header: WWW-Authenticate header value
            
        Returns:
            Dictionary with scheme and parameters (realm, service, scope, etc.)
            Returns empty dict if parsing fails
        """
        if not header:
            return {}
        
        # Split scheme and parameters
        parts = header.split(' ', 1)
        if len(parts) != 2:
            return {}
        
        scheme, params_str = parts
        
        # Parse parameters
        params = {'scheme': scheme}
        
        # Handle comma-separated key=value pairs
        # Use regex to handle quoted values properly
        import re
        param_pattern = re.compile(r'(\w+)="([^"]*)"')
        
        for match in param_pattern.finditer(params_str):
            key, value = match.groups()
            params[key] = value
        
        return params
    
    def _request_token(
        self,
        realm: str,
        service: str,
        scope: str
    ) -> Optional[str]:
        """Request bearer token from auth service.
        
        Makes a GET request to the token endpoint to obtain a bearer token
        for accessing registry resources. Includes credentials if available
        for authenticated tokens.
        
        Args:
            realm: Token endpoint URL
            service: Service name (e.g., "registry.docker.io")
            scope: Access scope (e.g., "repository:library/nginx:pull")
            
        Returns:
            Bearer token if successful, None otherwise
        """
        try:
            # Build token request URL
            params = {
                'service': service,
                'scope': scope
            }
            
            # Create a new session for token request (don't use self.session)
            # to avoid auth loops
            token_session = requests.Session()
            token_session.verify = self.session.verify
            
            # Include credentials if available for authenticated tokens
            auth = None
            if self.auth:
                auth = self.auth
            
            response = token_session.get(
                realm,
                params=params,
                auth=auth,
                timeout=10
            )
            
            if response.status_code != 200:
                return None
            
            # Parse token response
            token_data = response.json()
            
            # Token can be in 'token' or 'access_token' field
            token = token_data.get('token') or token_data.get('access_token')
            
            return token
            
        except Exception:
            # Silently fail and return None
            return None
    
    def _handle_auth_challenge(
        self,
        response: requests.Response,
        original_url: str
    ) -> Optional[str]:
        """Handle WWW-Authenticate challenge and obtain token.
        
        Parses the WWW-Authenticate header from a 401 response and
        requests a bearer token from the authentication service.
        
        Args:
            response: 401 response with WWW-Authenticate header
            original_url: Original request URL for scope determination
            
        Returns:
            Bearer token if successful, None otherwise
        """
        # Get WWW-Authenticate header
        www_auth = response.headers.get('Www-Authenticate')
        if not www_auth:
            return None
        
        # Parse authentication challenge
        auth_params = self._parse_www_authenticate(www_auth)
        
        # Only handle Bearer authentication
        if auth_params.get('scheme') != 'Bearer':
            return None
        
        # Extract required parameters
        realm = auth_params.get('realm')
        service = auth_params.get('service')
        scope = auth_params.get('scope')
        
        if not realm or not service:
            return None
        
        # If no scope in challenge, try to infer from URL
        if not scope:
            scope = ''
        
        # Request token
        token = self._request_token(realm, service, scope)
        
        # Cache token and scope
        if token:
            self.token = token
            self.token_scope = scope
        
        return token
    
    def _request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> requests.Response:
        """Make HTTP request with automatic token authentication.
        
        Handles 401 responses by:
        1. Parsing WWW-Authenticate header
        2. Requesting token from auth service
        3. Retrying request with token
        
        Args:
            method: HTTP method (GET, POST, PUT, etc.)
            url: Request URL
            **kwargs: Additional request arguments
            
        Returns:
            Response object
            
        Raises:
            RegistryAuthenticationError: If authentication fails
        """
        # If we have a cached token, use it
        if self.token and self.enable_token_auth:
            if 'headers' not in kwargs:
                kwargs['headers'] = {}
            kwargs['headers']['Authorization'] = f'Bearer {self.token}'
        
        # Make the request
        response = self.session.request(method, url, **kwargs)
        
        # Handle 401 with token authentication
        if response.status_code == 401 and self.enable_token_auth:
            # Try to get a token
            token = self._handle_auth_challenge(response, url)
            
            if token:
                # Retry with token
                if 'headers' not in kwargs:
                    kwargs['headers'] = {}
                kwargs['headers']['Authorization'] = f'Bearer {token}'
                
                response = self.session.request(method, url, **kwargs)
        
        return response
    
    def close(self) -> None:
        """Close the registry client session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
