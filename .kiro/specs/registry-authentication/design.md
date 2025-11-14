# Design Document: Registry Authentication

## Overview

This document describes the design for implementing registry authentication in Derpy. The feature enables users to authenticate with container registries using a `derpy login` command, with secure local credential storage and support for multiple authentication methods including Docker Hub token authentication, HTTP Basic Auth, and AWS ECR.

The design focuses on:

- User-friendly CLI commands (`login`, `logout`)
- Secure credential storage with proper file permissions
- Support for multiple authentication methods (token-based, basic auth)
- Seamless integration with existing build and push commands
- Compatibility with Docker Hub, AWS ECR, and private registries

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI Layer                            │
│  ┌──────────┐  ┌───────────┐  ┌────────┐  ┌──────────┐    │
│  │  login   │  │  logout   │  │ build  │  │   push   │    │
│  └────┬─────┘  └─────┬─────┘  └───┬────┘  └────┬─────┘    │
└───────┼──────────────┼────────────┼────────────┼───────────┘
        │              │            │            │
        └──────┬───────┘            │            │
               │                    │            │
        ┌──────▼────────────────────▼────────────▼──────┐
        │         AuthManager (New Component)            │
        │  - Store/retrieve credentials                  │
        │  - Manage auth.json file                       │
        │  - Handle file permissions                     │
        └──────┬─────────────────────────────────────────┘
               │
        ┌──────▼─────────────────────────────────────────┐
        │      RegistryClient (Enhanced)                 │
        │  - Token authentication (Docker Hub)           │
        │  - Basic authentication                        │
        │  - WWW-Authenticate header parsing             │
        │  - Automatic token refresh                     │
        └──────┬─────────────────────────────────────────┘
               │
        ┌──────▼─────────────────────────────────────────┐
        │         BaseImageManager (Enhanced)            │
        │  - Use AuthManager for credentials             │
        │  - Pass credentials to RegistryClient          │
        └────────────────────────────────────────────────┘
```

### Authentication Flow

#### Docker Hub Token Authentication (Anonymous)

```
1. User: derpy build . -t myapp:latest
2. BuildEngine: Pull base image nginx:alpine
3. BaseImageManager: Check for credentials (none found)
4. RegistryClient: GET /v2/library/nginx/manifests/alpine
5. Registry: 401 Unauthorized
   Www-Authenticate: Bearer realm="https://auth.docker.io/token",
                     service="registry.docker.io",
                     scope="repository:library/nginx:pull"
6. RegistryClient: Parse challenge, extract realm, service, scope
7. RegistryClient: GET https://auth.docker.io/token?service=...&scope=...
8. Auth Service: 200 OK { "token": "eyJhbGc..." }
9. RegistryClient: Retry GET /v2/library/nginx/manifests/alpine
   Authorization: Bearer eyJhbGc...
10. Registry: 200 OK (manifest data)
```

#### Authenticated Login Flow

```
1. User: derpy login registry.example.com
2. CLI: Prompt for username
3. User: enters "myuser"
4. CLI: Prompt for password (hidden)
5. User: enters password
6. AuthManager: Create RegistryClient with credentials
7. RegistryClient: Test authentication with GET /v2/
8. Registry: 200 OK (authenticated)
9. AuthManager: Store credentials in ~/.derpy/auth.json
10. AuthManager: Set file permissions to 0600
11. CLI: Display "Login Succeeded"
```

## Components and Interfaces

### 1. AuthManager (New)

**Location:** `derpy/core/auth.py`

**Purpose:** Manages registry credentials, including storage, retrieval, and secure file handling.

**Class Definition:**

```python
@dataclass
class RegistryCredentials:
    """Credentials for a container registry."""
    registry: str  # Normalized registry URL
    username: str
    password: str  # Base64 encoded for storage

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for JSON serialization."""
        pass

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "RegistryCredentials":
        """Create from dictionary during deserialization."""
        pass


class AuthManager:
    """Manages registry authentication credentials."""

    def __init__(self, auth_file: Optional[Path] = None):
        """Initialize AuthManager.

        Args:
            auth_file: Path to auth file (default: ~/.derpy/auth.json)
        """
        pass

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
            password: Password
            verify_auth: Whether to verify credentials with registry

        Raises:
            AuthenticationError: If verification fails
        """
        pass

    def logout(self, registry: str) -> bool:
        """Remove credentials for a registry.

        Args:
            registry: Registry URL

        Returns:
            True if credentials were removed, False if none existed
        """
        pass

    def get_credentials(self, registry: str) -> Optional[RegistryCredentials]:
        """Retrieve credentials for a registry.

        Args:
            registry: Registry URL

        Returns:
            RegistryCredentials if found, None otherwise
        """
        pass

    def list_registries(self) -> List[str]:
        """List all registries with stored credentials.

        Returns:
            List of registry URLs
        """
        pass

    def _normalize_registry(self, registry: str) -> str:
        """Normalize registry URL for consistent storage.

        Args:
            registry: Registry URL

        Returns:
            Normalized registry URL
        """
        pass

    def _load_auth_file(self) -> Dict[str, Dict[str, str]]:
        """Load credentials from auth file."""
        pass

    def _save_auth_file(self, auths: Dict[str, Dict[str, str]]) -> None:
        """Save credentials to auth file with proper permissions."""
        pass

    def _ensure_secure_permissions(self) -> None:
        """Ensure auth file has 0600 permissions."""
        pass
```

**Auth File Format:**

```json
{
  "auths": {
    "registry-1.docker.io": {
      "username": "myuser",
      "password": "bXlwYXNzd29yZA=="
    },
    "registry.example.com": {
      "username": "admin",
      "password": "YWRtaW5wYXNz"
    }
  }
}
```

### 2. RegistryClient (Enhanced)

**Location:** `derpy/registry/client.py`

**Enhancements:**

```python
class RegistryClient:
    """Client for interacting with OCI-compliant container registries."""

    def __init__(
        self,
        registry_config: RegistryConfig,
        enable_token_auth: bool = True
    ):
        """Initialize registry client.

        Args:
            registry_config: Registry configuration
            enable_token_auth: Enable automatic token authentication
        """
        # Existing initialization
        self.enable_token_auth = enable_token_auth
        self.token: Optional[str] = None
        self.token_scope: Optional[str] = None

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
            method: HTTP method
            url: Request URL
            **kwargs: Additional request arguments

        Returns:
            Response object

        Raises:
            RegistryAuthenticationError: If authentication fails
        """
        pass

    def _handle_auth_challenge(
        self,
        response: requests.Response,
        original_url: str
    ) -> Optional[str]:
        """Handle WWW-Authenticate challenge and obtain token.

        Args:
            response: 401 response with WWW-Authenticate header
            original_url: Original request URL for scope determination

        Returns:
            Bearer token if successful, None otherwise
        """
        pass

    def _parse_www_authenticate(
        self,
        header: str
    ) -> Dict[str, str]:
        """Parse WWW-Authenticate header.

        Example:
            Bearer realm="https://auth.docker.io/token",
                   service="registry.docker.io",
                   scope="repository:library/nginx:pull"

        Args:
            header: WWW-Authenticate header value

        Returns:
            Dictionary with realm, service, scope, etc.
        """
        pass

    def _request_token(
        self,
        realm: str,
        service: str,
        scope: str
    ) -> Optional[str]:
        """Request bearer token from auth service.

        Args:
            realm: Token endpoint URL
            service: Service name
            scope: Access scope

        Returns:
            Bearer token if successful, None otherwise
        """
        pass

    def verify_authentication(self) -> bool:
        """Verify credentials by testing /v2/ endpoint.

        Returns:
            True if authenticated, False otherwise
        """
        pass
```

### 3. CLI Commands (New)

**Location:** `derpy/cli/main.py`

**Login Command:**

```python
@cli.command()
@click.argument('registry', default='docker.io')
@click.option('--username', '-u', help='Username')
@click.option('--password', '-p', help='Password')
@click.option('--password-stdin', is_flag=True, help='Read password from stdin')
@click.pass_context
def login(
    ctx,
    registry: str,
    username: Optional[str],
    password: Optional[str],
    password_stdin: bool
):
    """Login to a container registry.

    Examples:

      derpy login

      derpy login registry.example.com

      derpy login -u myuser -p mypass registry.example.com

      echo "mypass" | derpy login --password-stdin registry.example.com
    """
    pass
```

**Logout Command:**

```python
@cli.command()
@click.argument('registry', default='docker.io')
@click.pass_context
def logout(ctx, registry: str):
    """Logout from a container registry.

    Examples:

      derpy logout

      derpy logout registry.example.com
    """
    pass
```

### 4. BaseImageManager (Enhanced)

**Location:** `derpy/build/base_image.py`

**Enhancements:**

```python
class BaseImageManager:
    """Manages base image retrieval and extraction."""

    def __init__(
        self,
        storage_manager: ImageManager,
        cache_dir: Optional[Path] = None,
        auth_manager: Optional[AuthManager] = None
    ):
        """Initialize BaseImageManager.

        Args:
            storage_manager: ImageManager for local storage
            cache_dir: Directory for caching base images
            auth_manager: AuthManager for registry credentials
        """
        self.storage = storage_manager
        self.cache_dir = cache_dir or Path.home() / ".derpy" / "cache" / "base-images"
        self.auth_manager = auth_manager or AuthManager()
        self.logger = get_logger("base_image")

    def pull_base_image(self, image_ref: str) -> Image:
        """Download base image from registry.

        Now checks for stored credentials and uses them.

        Args:
            image_ref: Image reference

        Returns:
            Image object
        """
        # Parse image reference
        registry_url, repository, tag = self.resolve_image_reference(image_ref)

        # Check for stored credentials
        credentials = self.auth_manager.get_credentials(registry_url)

        # Create registry config with credentials
        if credentials:
            registry_config = RegistryConfig(
                url=api_url,
                username=credentials.username,
                password=credentials.password,
                insecure=False
            )
        else:
            # No credentials - will use anonymous token auth for Docker Hub
            registry_config = RegistryConfig(
                url=api_url,
                username=None,
                password=None,
                insecure=False
            )

        # Continue with existing pull logic...
```

## Data Models

### RegistryCredentials

```python
@dataclass
class RegistryCredentials:
    """Credentials for a container registry."""
    registry: str
    username: str
    password: str  # Base64 encoded

    def decode_password(self) -> str:
        """Decode base64 password."""
        return base64.b64decode(self.password).decode('utf-8')

    @staticmethod
    def encode_password(password: str) -> str:
        """Encode password to base64."""
        return base64.b64encode(password.encode('utf-8')).decode('utf-8')
```

### TokenResponse

```python
@dataclass
class TokenResponse:
    """Response from token authentication endpoint."""
    token: str
    access_token: Optional[str] = None
    expires_in: Optional[int] = None
    issued_at: Optional[str] = None

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "TokenResponse":
        """Parse token response from JSON."""
        pass
```

## Error Handling

### New Exception Classes

```python
class AuthenticationError(DerpyError):
    """Base class for authentication errors."""
    pass


class CredentialStorageError(AuthenticationError):
    """Error storing or retrieving credentials."""
    pass


class TokenAuthenticationError(AuthenticationError):
    """Error during token authentication."""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Invalid username or password."""
    pass
```

### Error Messages

- **Authentication Failed:** "Authentication failed for registry: {registry}\nPlease check your credentials and try again.\nRun 'derpy login {registry}' to authenticate."

- **Credential Storage Failed:** "Failed to store credentials: {error}\nCheck file permissions for ~/.derpy/auth.json"

- **Token Request Failed:** "Failed to obtain authentication token from {realm}\nError: {error}"

- **No Credentials Found:** "No credentials found for registry: {registry}\nRun 'derpy login {registry}' to authenticate."

## Testing Strategy

### Unit Tests

1. **AuthManager Tests** (`tests/test_auth_manager.py`):

   - Test credential storage and retrieval
   - Test file permission handling
   - Test registry URL normalization
   - Test base64 encoding/decoding
   - Test multiple registry support

2. **RegistryClient Token Auth Tests** (`tests/test_registry_token_auth.py`):

   - Test WWW-Authenticate header parsing
   - Test token request and caching
   - Test automatic retry with token
   - Test token expiration handling
   - Mock Docker Hub auth service

3. **CLI Command Tests** (`tests/test_cli_auth.py`):
   - Test login command with various options
   - Test logout command
   - Test password input (mocked)
   - Test stdin password reading

### Integration Tests

1. **Docker Hub Anonymous Pull** (`tests/test_dockerhub_anonymous.py`):

   - Test pulling public image without credentials
   - Verify token authentication flow
   - Test rate limit handling

2. **Authenticated Pull** (`tests/test_authenticated_pull.py`):

   - Test login with valid credentials
   - Test pulling private image
   - Test credential persistence

3. **Build with Private Base Image** (`tests/test_build_private_base.py`):
   - Test building with private base image
   - Verify credentials are used
   - Test error handling for missing credentials

### Manual Testing

1. Test Docker Hub anonymous pulls
2. Test Docker Hub authenticated pulls
3. Test private registry (local registry container)
4. Test AWS ECR authentication
5. Test credential storage and retrieval
6. Test file permissions on auth.json
7. Test sudo builds with user credentials

## Security Considerations

1. **File Permissions:** Auth file must have 0600 permissions (owner read/write only)
2. **Password Encoding:** Passwords stored as base64 (not encryption, just encoding)
3. **Token Caching:** Tokens cached in memory only, not persisted
4. **HTTPS Enforcement:** Default to HTTPS for all registries
5. **Credential Validation:** Verify credentials before storing
6. **Error Messages:** Don't expose passwords in error messages or logs

## Implementation Notes

### Registry URL Normalization

```python
def normalize_registry_url(registry: str) -> str:
    """Normalize registry URL for consistent storage.

    Rules:
    - docker.io -> registry-1.docker.io
    - registry.hub.docker.com -> registry-1.docker.io
    - No scheme -> add https://
    - Remove trailing slashes
    - Lowercase hostname
    """
    # Handle Docker Hub aliases
    if registry in ('docker.io', 'registry.hub.docker.com', 'index.docker.io'):
        return 'registry-1.docker.io'

    # Add https:// if no scheme
    if '://' not in registry:
        registry = f'https://{registry}'

    # Parse and normalize
    parsed = urlparse(registry)
    normalized = parsed.netloc.lower()

    return normalized
```

### WWW-Authenticate Parsing

```python
def parse_www_authenticate(header: str) -> Dict[str, str]:
    """Parse WWW-Authenticate header.

    Example input:
        Bearer realm="https://auth.docker.io/token",
               service="registry.docker.io",
               scope="repository:library/nginx:pull"

    Returns:
        {
            'scheme': 'Bearer',
            'realm': 'https://auth.docker.io/token',
            'service': 'registry.docker.io',
            'scope': 'repository:library/nginx:pull'
        }
    """
    # Split scheme and parameters
    parts = header.split(' ', 1)
    if len(parts) != 2:
        return {}

    scheme, params_str = parts

    # Parse parameters
    params = {'scheme': scheme}
    for param in params_str.split(','):
        param = param.strip()
        if '=' in param:
            key, value = param.split('=', 1)
            # Remove quotes
            value = value.strip('"')
            params[key] = value

    return params
```

## Migration and Compatibility

### Backward Compatibility

- Existing push functionality continues to work with stored registry configs
- No breaking changes to existing APIs
- Auth file is optional - system works without it (anonymous pulls only)

### Migration Path

1. Users with existing registry configs in config.yaml can continue using them
2. New auth.json file is created on first login
3. Both systems can coexist (config.yaml for registry URLs, auth.json for credentials)

## Performance Considerations

1. **Token Caching:** Cache tokens in memory to avoid repeated auth requests
2. **Credential Lookup:** O(1) lookup using dictionary
3. **File I/O:** Only read auth file when needed, cache in memory
4. **Network Requests:** Minimize auth requests by caching tokens

## Future Enhancements

1. **Credential Helpers:** Support Docker credential helpers (docker-credential-\*)
2. **OAuth2 Device Flow:** Support device flow for web-based authentication
3. **Token Refresh:** Automatic token refresh before expiration
4. **Keychain Integration:** Use system keychain on macOS/Windows
5. **Multi-Factor Authentication:** Support MFA for registries that require it
