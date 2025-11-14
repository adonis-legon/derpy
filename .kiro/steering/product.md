Derpy is an independent container tool that builds, manages, and distributes OCI-compliant container images without depending on Docker, Podman, containerd, or any other container runtime. It's a Python CLI application that implements container functionality from scratch while maintaining full OCI compliance for interoperability with existing container ecosystems.

Version 0.1.0 (alpha) supports core Dockerfile instructions (FROM, RUN, CMD) and provides essential functionality for building images, managing a local repository, and pushing to OCI-compliant registries. The tool works cross-platform on Windows, Linux, and macOS.

## Registry Authentication Feature

Derpy includes comprehensive registry authentication support, enabling users to authenticate with Docker Hub, AWS ECR, and private container registries for both pulling base images during builds and pushing images to registries.

**Key capabilities:**

- `derpy login` command for authenticating with registries
- `derpy logout` command for removing stored credentials
- Secure credential storage at `~/.derpy/auth.json` with 0600 file permissions
- Docker Hub token authentication (OAuth2 bearer tokens) for anonymous and authenticated pulls
- HTTP Basic Authentication for private registries
- Automatic credential usage during builds and pushes
- Support for multiple registries with separate credentials
- Registry URL normalization (docker.io → registry-1.docker.io)

**Authentication workflow:**

1. User runs `derpy login [registry]` and provides credentials
2. Credentials are verified with the registry
3. Credentials are stored securely in `~/.derpy/auth.json` with base64 encoding
4. During builds, stored credentials are automatically used for pulling private base images
5. During pushes, stored credentials are automatically used for authentication
6. User can run `derpy logout [registry]` to remove credentials

**Docker Hub support:**

- Anonymous pulls: Automatically requests anonymous tokens for public images
- Authenticated pulls: Uses stored credentials for higher rate limits and private images
- Token caching: Tokens are cached in memory to minimize auth requests
- WWW-Authenticate header parsing: Automatically handles 401 challenges

**Security features:**

- File permissions: Auth file restricted to 0600 (owner read/write only)
- Password encoding: Passwords stored as base64 (not plaintext)
- Credential validation: Verifies credentials before storing
- HTTPS enforcement: Defaults to HTTPS for all registries
- Sudo support: When building with sudo, uses the user's credentials from their home directory

**Supported registries:**

- Docker Hub (registry-1.docker.io)
- AWS ECR (_.dkr.ecr._.amazonaws.com)
- Private registries with HTTP Basic Auth
- Any OCI-compliant registry

## Build Isolation Feature

Derpy includes build isolation support on Linux systems, enabling real-world container builds that depend on base image filesystems and distribution-specific package managers (apt, apk, yum, etc.).

**How it works:**

1. Downloads base images from OCI registries and caches them locally
2. Extracts base image layers into a temporary filesystem
3. Executes RUN commands in a chrooted environment with access to the base image's tools and filesystem
4. Captures filesystem changes as new layers using diff tracking
5. Combines base and new layers into the final OCI-compliant image

**Requirements:**

- Linux operating system
- Root privileges (sudo) or CAP_SYS_CHROOT capability
- Enabled by default on Linux, automatically disabled on macOS/Windows

**Configuration:**

- `build_settings.enable_isolation`: Enable/disable isolation (default: true)
- `build_settings.base_image_cache_dir`: Cache directory for base images (default: ~/.derpy/cache/base-images)
- `build_settings.chroot_timeout`: Timeout for chroot commands in seconds (default: 300)

**Fallback behavior:**
When isolation is unavailable (non-Linux, no root, or disabled), derpy falls back to v0.1.0 behavior where RUN commands execute on the host system. This limits functionality to simple commands that don't depend on base image filesystems.

Key design principles:

- Runtime independence: No dependency on existing container runtimes
- Minimal dependencies: Uses only essential Python packages (PyYAML, click, requests)
- OCI compliance: Ensures images work with Docker, Podman, Kubernetes, and other OCI-compatible tools
- Cross-platform: Consistent behavior across all major operating systems
- Graceful degradation: Falls back to non-isolated builds when isolation is unavailable
