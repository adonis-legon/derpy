# Requirements Document

## Introduction

This document specifies the requirements for implementing registry authentication in Derpy, enabling users to authenticate with container registries (Docker Hub, AWS ECR, private registries, etc.) for both pulling base images during builds and pushing images to registries. The feature will include a `derpy login` command similar to Docker's login functionality, with secure credential storage and support for multiple authentication methods.

## Glossary

- **Derpy**: The independent container tool that builds, manages, and distributes OCI-compliant container images
- **Registry**: An OCI-compliant container image registry (e.g., Docker Hub, AWS ECR, private registries)
- **Docker Hub**: The default public container registry at registry-1.docker.io
- **Token Authentication**: OAuth2-based authentication using bearer tokens (used by Docker Hub for anonymous and authenticated pulls)
- **Basic Authentication**: HTTP Basic Auth using username and password
- **Credential Store**: Local storage for registry credentials at ~/.derpy/auth.json
- **RegistryClient**: The component responsible for communicating with container registries
- **BaseImageManager**: The component responsible for downloading base images during builds

## Requirements

### Requirement 1: Login Command

**User Story:** As a developer, I want to authenticate with container registries using a login command, so that I can pull private images and push images to registries.

#### Acceptance Criteria

1. WHEN the user runs "derpy login [registry]" THEN Derpy SHALL prompt for username and password
2. WHEN the user provides valid credentials THEN Derpy SHALL authenticate with the registry and store the credentials securely
3. WHEN the user runs "derpy login [registry] --username [user] --password [pass]" THEN Derpy SHALL authenticate without prompting
4. WHEN the user runs "derpy login [registry] --password-stdin" THEN Derpy SHALL read the password from standard input
5. WHEN authentication succeeds THEN Derpy SHALL display a success message with the registry URL

### Requirement 2: Logout Command

**User Story:** As a developer, I want to remove stored credentials for a registry, so that I can manage my authentication state.

#### Acceptance Criteria

1. WHEN the user runs "derpy logout [registry]" THEN Derpy SHALL remove stored credentials for that registry
2. WHEN the user runs "derpy logout" without specifying a registry THEN Derpy SHALL remove credentials for the default registry (Docker Hub)
3. WHEN credentials are removed THEN Derpy SHALL display a confirmation message
4. WHEN the user attempts to logout from a registry with no stored credentials THEN Derpy SHALL display an informational message

### Requirement 3: Credential Storage

**User Story:** As a developer, I want my registry credentials stored securely on my local machine, so that I don't have to re-authenticate for every operation.

#### Acceptance Criteria

1. WHEN credentials are stored THEN Derpy SHALL save them to ~/.derpy/auth.json with file permissions 0600
2. WHEN the auth file is created THEN Derpy SHALL ensure only the owner can read and write the file
3. WHEN multiple registries are configured THEN Derpy SHALL store credentials for each registry separately
4. WHEN credentials are stored THEN Derpy SHALL encode passwords using base64 encoding
5. IF the auth file exists with incorrect permissions THEN Derpy SHALL warn the user and fix the permissions

### Requirement 4: Docker Hub Token Authentication

**User Story:** As a developer, I want to pull public images from Docker Hub without authentication, so that I can build images using popular base images.

#### Acceptance Criteria

1. WHEN pulling from Docker Hub without credentials THEN Derpy SHALL request an anonymous token from the Docker Hub auth service
2. WHEN a 401 response includes a Www-Authenticate header THEN Derpy SHALL parse the authentication challenge
3. WHEN the challenge specifies a bearer token realm THEN Derpy SHALL request a token from that realm
4. WHEN a token is received THEN Derpy SHALL retry the original request with the bearer token
5. WHEN pulling with stored credentials THEN Derpy SHALL use authenticated tokens for higher rate limits

### Requirement 5: Basic Authentication Support

**User Story:** As a developer, I want to authenticate with private registries using username and password, so that I can pull and push images to my organization's registry.

#### Acceptance Criteria

1. WHEN stored credentials exist for a registry THEN Derpy SHALL use HTTP Basic Authentication for all requests
2. WHEN the registry requires authentication THEN Derpy SHALL include the Authorization header with base64-encoded credentials
3. WHEN authentication fails with 401 THEN Derpy SHALL display a clear error message indicating authentication failure
4. WHEN the registry URL includes a custom port THEN Derpy SHALL correctly match stored credentials
5. WHEN the registry uses HTTPS THEN Derpy SHALL verify SSL certificates by default

### Requirement 6: Build Command Integration

**User Story:** As a developer, I want base image pulls during builds to use my stored credentials, so that I can build images using private base images.

#### Acceptance Criteria

1. WHEN building an image with a FROM instruction THEN Derpy SHALL check for stored credentials for the base image registry
2. WHEN credentials exist THEN Derpy SHALL use them to authenticate when pulling the base image
3. WHEN credentials do not exist for Docker Hub THEN Derpy SHALL attempt anonymous token authentication
4. WHEN base image authentication fails THEN Derpy SHALL display a clear error message with the registry URL
5. WHEN building with sudo THEN Derpy SHALL use the current user's credentials from their home directory

### Requirement 7: Push Command Integration

**User Story:** As a developer, I want image pushes to use my stored credentials, so that I can push images to authenticated registries.

#### Acceptance Criteria

1. WHEN pushing an image THEN Derpy SHALL check for stored credentials for the target registry
2. WHEN credentials exist THEN Derpy SHALL use them to authenticate the push operation
3. WHEN credentials do not exist THEN Derpy SHALL display an error message prompting the user to login
4. WHEN push authentication fails THEN Derpy SHALL display a clear error message with authentication details
5. WHEN the registry requires authentication THEN Derpy SHALL not attempt the push without credentials

### Requirement 8: Registry URL Normalization

**User Story:** As a developer, I want registry URLs to be handled consistently, so that my credentials work regardless of how I specify the registry.

#### Acceptance Criteria

1. WHEN the user specifies "docker.io" THEN Derpy SHALL normalize it to "registry-1.docker.io"
2. WHEN the user specifies a registry without a scheme THEN Derpy SHALL default to HTTPS
3. WHEN the user specifies "registry.hub.docker.com" THEN Derpy SHALL normalize it to "registry-1.docker.io"
4. WHEN matching credentials THEN Derpy SHALL use normalized registry URLs for comparison
5. WHEN displaying registry information THEN Derpy SHALL show the normalized URL

### Requirement 9: Error Handling and User Feedback

**User Story:** As a developer, I want clear error messages when authentication fails, so that I can troubleshoot and resolve issues quickly.

#### Acceptance Criteria

1. WHEN authentication fails with 401 THEN Derpy SHALL display "Authentication failed" with the registry URL
2. WHEN the network is unreachable THEN Derpy SHALL display "Cannot connect to registry" with the URL
3. WHEN credentials are invalid THEN Derpy SHALL suggest running "derpy login [registry]"
4. WHEN a registry is not found (404) THEN Derpy SHALL display "Registry or repository not found"
5. WHEN rate limits are exceeded THEN Derpy SHALL display the rate limit information and suggest authentication

### Requirement 10: AWS ECR Support

**User Story:** As a developer, I want to authenticate with AWS ECR using AWS credentials, so that I can use ECR as my private registry.

#### Acceptance Criteria

1. WHEN the registry URL matches an ECR pattern THEN Derpy SHALL recognize it as an ECR registry
2. WHEN authenticating with ECR THEN Derpy SHALL accept AWS access key ID as username
3. WHEN authenticating with ECR THEN Derpy SHALL accept the ECR authorization token as password
4. WHEN ECR credentials are stored THEN Derpy SHALL use them for pull and push operations
5. WHEN ECR tokens expire THEN Derpy SHALL display an error message indicating token expiration
