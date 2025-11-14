"""Registry authentication management.

This module provides authentication management for container registries,
including secure credential storage, retrieval, and verification.
"""

import base64
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List
from urllib.parse import urlparse

from derpy.core.exceptions import (
    AuthenticationError,
    CredentialStorageError,
    TokenAuthenticationError,
    InvalidCredentialsError
)
from derpy.core.logging import get_logger


@dataclass
class RegistryCredentials:
    """Credentials for a container registry."""
    
    registry: str  # Normalized registry URL
    username: str
    password: str  # Base64 encoded for storage
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for JSON serialization.
        
        Returns:
            Dictionary with username and password (base64 encoded)
        """
        return {
            'username': self.username,
            'password': self.password
        }
    
    @classmethod
    def from_dict(cls, registry: str, data: Dict[str, str]) -> "RegistryCredentials":
        """Create from dictionary during deserialization.
        
        Args:
            registry: Registry URL
            data: Dictionary with username and password
            
        Returns:
            RegistryCredentials instance
            
        Raises:
            CredentialStorageError: If data format is invalid
        """
        if 'username' not in data or 'password' not in data:
            raise CredentialStorageError("Invalid credential format: missing username or password")
        
        return cls(
            registry=registry,
            username=data['username'],
            password=data['password']
        )
    
    def decode_password(self) -> str:
        """Decode base64 password.
        
        Returns:
            Decoded password string
        """
        try:
            return base64.b64decode(self.password).decode('utf-8')
        except Exception as e:
            raise CredentialStorageError(f"Failed to decode password", cause=e)
    
    @staticmethod
    def encode_password(password: str) -> str:
        """Encode password to base64.
        
        Args:
            password: Plain text password
            
        Returns:
            Base64 encoded password
        """
        return base64.b64encode(password.encode('utf-8')).decode('utf-8')


class AuthManager:
    """Manages registry authentication credentials.
    
    Provides secure storage and retrieval of registry credentials with
    proper file permissions and registry URL normalization.
    """
    
    def __init__(self, auth_file: Optional[Path] = None):
        """Initialize AuthManager.
        
        Args:
            auth_file: Path to auth file (default: ~/.derpy/auth.json)
        """
        if auth_file is None:
            auth_file = Path.home() / ".derpy" / "auth.json"
        
        self.auth_file = Path(auth_file)
        self.logger = get_logger("auth")
        
        # Ensure parent directory exists
        self.auth_file.parent.mkdir(parents=True, exist_ok=True)
    
    def login(
        self,
        registry: str,
        username: str,
        password: str,
        verify_auth: bool = True
    ) -> None:
        """Store credentials for a registry.
        
        Args:
            registry: Registry URL
            username: Username
            password: Password (plain text, will be encoded)
            verify_auth: Whether to verify credentials with registry
            
        Raises:
            InvalidCredentialsError: If verification fails
            CredentialStorageError: If storage fails
        """
        # Normalize registry URL
        normalized_registry = self._normalize_registry(registry)
        
        # Verify credentials if requested
        if verify_auth:
            self._verify_credentials(normalized_registry, username, password)
        
        # Load existing auth file
        auths = self._load_auth_file()
        
        # Encode password
        encoded_password = RegistryCredentials.encode_password(password)
        
        # Store credentials
        auths[normalized_registry] = {
            'username': username,
            'password': encoded_password
        }
        
        # Save auth file
        self._save_auth_file(auths)
        
        self.logger.info(f"Stored credentials for registry: {normalized_registry}")
    
    def logout(self, registry: str) -> bool:
        """Remove credentials for a registry.
        
        Args:
            registry: Registry URL
            
        Returns:
            True if credentials were removed, False if none existed
            
        Raises:
            CredentialStorageError: If removal fails
        """
        # Normalize registry URL
        normalized_registry = self._normalize_registry(registry)
        
        # Load existing auth file
        auths = self._load_auth_file()
        
        # Check if credentials exist
        if normalized_registry not in auths:
            self.logger.info(f"No credentials found for registry: {normalized_registry}")
            return False
        
        # Remove credentials
        del auths[normalized_registry]
        
        # Save auth file
        self._save_auth_file(auths)
        
        self.logger.info(f"Removed credentials for registry: {normalized_registry}")
        return True
    
    def get_credentials(self, registry: str) -> Optional[RegistryCredentials]:
        """Retrieve credentials for a registry.
        
        Args:
            registry: Registry URL
            
        Returns:
            RegistryCredentials if found, None otherwise
        """
        # Normalize registry URL
        normalized_registry = self._normalize_registry(registry)
        
        # Load auth file
        auths = self._load_auth_file()
        
        # Check if credentials exist
        if normalized_registry not in auths:
            return None
        
        # Create RegistryCredentials object
        try:
            return RegistryCredentials.from_dict(
                normalized_registry,
                auths[normalized_registry]
            )
        except CredentialStorageError as e:
            self.logger.warning(f"Invalid credentials for {normalized_registry}: {e}")
            return None
    
    def list_registries(self) -> List[str]:
        """List all registries with stored credentials.
        
        Returns:
            List of registry URLs
        """
        auths = self._load_auth_file()
        return list(auths.keys())
    
    def _normalize_registry(self, registry: str) -> str:
        """Normalize registry URL for consistent storage.
        
        Handles Docker Hub aliases and ensures consistent formatting.
        
        Args:
            registry: Registry URL
            
        Returns:
            Normalized registry URL
        """
        # Handle Docker Hub aliases
        docker_hub_aliases = [
            'docker.io',
            'registry.hub.docker.com',
            'index.docker.io',
            ''  # Empty string defaults to Docker Hub
        ]
        
        if registry.lower() in docker_hub_aliases:
            return 'registry-1.docker.io'
        
        # Remove scheme if present
        if '://' in registry:
            parsed = urlparse(registry)
            registry = parsed.netloc
        
        # Convert to lowercase
        registry = registry.lower()
        
        # Remove trailing slashes
        registry = registry.rstrip('/')
        
        return registry
    
    def _load_auth_file(self) -> Dict[str, Dict[str, str]]:
        """Load credentials from auth file.
        
        Returns:
            Dictionary mapping registry URLs to credential dictionaries
            
        Raises:
            CredentialStorageError: If file cannot be read or parsed
        """
        # Return empty dict if file doesn't exist
        if not self.auth_file.exists():
            return {}
        
        # Check file permissions
        self._check_file_permissions()
        
        try:
            with open(self.auth_file, 'r') as f:
                data = json.load(f)
            
            # Validate format
            if not isinstance(data, dict):
                raise CredentialStorageError("Invalid auth file format: root must be an object")
            
            # Support both formats: {"auths": {...}} and direct {...}
            if 'auths' in data:
                auths = data['auths']
            else:
                auths = data
            
            if not isinstance(auths, dict):
                raise CredentialStorageError("Invalid auth file format: auths must be an object")
            
            return auths
            
        except json.JSONDecodeError as e:
            raise CredentialStorageError("Failed to parse auth file", cause=e)
        except IOError as e:
            raise CredentialStorageError("Failed to read auth file", cause=e)
    
    def _save_auth_file(self, auths: Dict[str, Dict[str, str]]) -> None:
        """Save credentials to auth file with proper permissions.
        
        Args:
            auths: Dictionary mapping registry URLs to credential dictionaries
            
        Raises:
            CredentialStorageError: If file cannot be written
        """
        try:
            # Create auth file structure
            data = {
                'auths': auths
            }
            
            # Write to file
            with open(self.auth_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Ensure secure permissions
            self._ensure_secure_permissions()
            
        except IOError as e:
            raise CredentialStorageError("Failed to write auth file", cause=e)
    
    def _ensure_secure_permissions(self) -> None:
        """Ensure auth file has 0600 permissions (owner read/write only).
        
        Raises:
            CredentialStorageError: If permissions cannot be set
        """
        try:
            # Set permissions to 0600 (owner read/write only)
            os.chmod(self.auth_file, stat.S_IRUSR | stat.S_IWUSR)
            self.logger.debug(f"Set auth file permissions to 0600: {self.auth_file}")
            
        except OSError as e:
            raise CredentialStorageError("Failed to set file permissions", cause=e)
    
    def _check_file_permissions(self) -> None:
        """Check auth file permissions and warn if insecure.
        
        Logs a warning if file permissions are too permissive.
        """
        try:
            file_stat = os.stat(self.auth_file)
            file_mode = stat.S_IMODE(file_stat.st_mode)
            
            # Check if file is readable by group or others
            if file_mode & (stat.S_IRGRP | stat.S_IROTH | stat.S_IWGRP | stat.S_IWOTH):
                self.logger.warning(
                    f"Auth file has insecure permissions: {oct(file_mode)}. "
                    f"Fixing permissions to 0600."
                )
                self._ensure_secure_permissions()
                
        except OSError as e:
            self.logger.warning(f"Failed to check file permissions: {e}")
    
    def _verify_credentials(
        self,
        registry: str,
        username: str,
        password: str
    ) -> None:
        """Verify credentials with the registry.
        
        Args:
            registry: Normalized registry URL
            username: Username
            password: Password (plain text)
            
        Raises:
            InvalidCredentialsError: If credentials are invalid
        """
        try:
            from derpy.core.config import RegistryConfig
            from derpy.registry.client import RegistryClient
            import requests
            
            # Construct registry URL with scheme
            registry_url = f"https://{registry}"
            
            # For Docker Hub, verify credentials by requesting a token
            # with credentials for a public repository
            if registry == 'registry-1.docker.io':
                # Request a token for a public repository to verify credentials
                # Use library/hello-world as it's always available
                auth_url = "https://auth.docker.io/token"
                params = {
                    'service': 'registry.docker.io',
                    'scope': 'repository:library/hello-world:pull'
                }
                
                response = requests.get(
                    auth_url,
                    params=params,
                    auth=requests.auth.HTTPBasicAuth(username, password),
                    timeout=10
                )
                
                # 200 means credentials are valid (or anonymous access granted)
                # 401 means credentials are invalid
                if response.status_code == 401:
                    raise InvalidCredentialsError(registry)
                elif response.status_code != 200:
                    # Other errors - log but don't fail
                    self.logger.warning(
                        f"Could not verify credentials for {registry}: "
                        f"HTTP {response.status_code}. "
                        "Credentials will be stored without verification."
                    )
                    return
                
                # Check if we got a token
                try:
                    token_data = response.json()
                    token = token_data.get('token') or token_data.get('access_token')
                    if not token:
                        # No token but 200 response - might be anonymous
                        # Try with credentials to see if they're accepted
                        pass
                except Exception:
                    pass
                
                self.logger.debug(f"Credentials verified for Docker Hub")
                return
            
            # For other registries, use the standard verification
            # Create registry config
            config = RegistryConfig(
                url=registry_url,
                username=username,
                password=password,
                insecure=False
            )
            
            # Create registry client
            with RegistryClient(config) as client:
                # Verify authentication
                if not client.verify_authentication():
                    raise InvalidCredentialsError(registry)
            
            self.logger.debug(f"Credentials verified for registry: {registry}")
            
        except InvalidCredentialsError:
            raise
        except Exception as e:
            # Don't fail on verification errors - just log and continue
            self.logger.warning(
                f"Could not verify credentials for {registry}: {e}. "
                "Credentials will be stored without verification."
            )
