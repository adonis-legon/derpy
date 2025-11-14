# Implementation Plan

- [ ] 1. Create AuthManager core component

  - Create derpy/core/auth.py with AuthManager class
  - Implement RegistryCredentials dataclass with to_dict/from_dict methods
  - Implement credential storage with base64 encoding
  - Implement file permission management (0600)
  - Implement registry URL normalization
  - _Requirements: 1.1, 1.2, 3.1, 3.2, 3.3, 3.4, 8.1, 8.2, 8.3, 8.4_

- [ ] 1.1 Implement credential storage and retrieval

  - Implement \_load_auth_file() to read ~/.derpy/auth.json
  - Implement \_save_auth_file() to write credentials with proper format
  - Implement get_credentials() to retrieve credentials for a registry
  - Implement list_registries() to list all stored registries
  - _Requirements: 3.1, 3.2, 3.3_

- [ ] 1.2 Implement login and logout methods

  - Implement login() method to store credentials
  - Implement logout() method to remove credentials
  - Implement credential verification with RegistryClient
  - Handle errors for invalid credentials
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3_

- [ ] 1.3 Implement security features

  - Implement \_ensure_secure_permissions() to set file permissions to 0600
  - Add permission check on file load with warning if incorrect
  - Implement base64 encoding/decoding for passwords
  - Add validation for auth file format
  - _Requirements: 3.1, 3.2, 3.5_

- [ ] 1.4 Write unit tests for AuthManager

  - Test credential storage and retrieval
  - Test file permission handling
  - Test registry URL normalization
  - Test base64 encoding/decoding
  - Test multiple registry support
  - Test error handling for invalid files
  - _Requirements: All Requirement 3 criteria_

- [ ] 2. Enhance RegistryClient with token authentication

  - Add enable_token_auth parameter to **init**
  - Add token and token_scope instance variables
  - Implement \_parse_www_authenticate() to parse authentication challenges
  - Implement \_request_token() to obtain bearer tokens
  - Implement \_handle_auth_challenge() to handle 401 responses
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.1, 5.2_

- [ ] 2.1 Implement WWW-Authenticate header parsing

  - Parse Bearer authentication challenges
  - Extract realm, service, and scope parameters
  - Handle malformed headers gracefully
  - Support both Bearer and Basic schemes
  - _Requirements: 4.2_

- [ ] 2.2 Implement token request logic

  - Make GET request to token endpoint with service and scope
  - Include credentials if available for authenticated tokens
  - Parse token response JSON
  - Handle token request errors
  - _Requirements: 4.3, 4.4, 4.5_

- [ ] 2.3 Implement automatic retry with token

  - Modify \_request() method to handle 401 responses
  - Call \_handle_auth_challenge() on 401
  - Retry original request with Authorization: Bearer header
  - Cache token for subsequent requests with same scope
  - _Requirements: 4.4_

- [ ] 2.4 Add verify_authentication method

  - Implement verify_authentication() to test credentials
  - Make GET request to /v2/ endpoint
  - Return True if 200, False if 401
  - Handle network errors gracefully
  - _Requirements: 1.2, 5.3_

- [ ] 2.5 Write unit tests for token authentication

  - Test WWW-Authenticate header parsing
  - Test token request with mocked auth service
  - Test automatic retry with token
  - Test token caching
  - Test error handling for invalid tokens
  - _Requirements: All Requirement 4 criteria_

- [ ] 3. Implement login CLI command

  - Add login command to derpy/cli/main.py
  - Add --username and --password options
  - Add --password-stdin flag
  - Implement interactive prompts for username and password
  - Use getpass for secure password input
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [ ] 3.1 Implement credential prompting

  - Prompt for username if not provided
  - Prompt for password if not provided and not using stdin
  - Use getpass.getpass() to hide password input
  - Read password from stdin if --password-stdin is used
  - Validate that username and password are not empty
  - _Requirements: 1.1, 1.4_

- [ ] 3.2 Implement authentication verification

  - Create AuthManager instance
  - Call login() method with provided credentials
  - Display success message with registry URL
  - Display error message if authentication fails
  - Suggest checking credentials on failure
  - _Requirements: 1.2, 1.5, 9.1, 9.3_

- [ ] 3.3 Handle registry URL normalization

  - Default to docker.io if no registry specified
  - Normalize registry URL before passing to AuthManager
  - Display normalized URL in success message
  - _Requirements: 8.1, 8.2, 8.3, 8.5_

- [ ] 3.4 Write tests for login command

  - Test login with username and password options
  - Test login with interactive prompts (mocked)
  - Test login with --password-stdin
  - Test login with default registry (docker.io)
  - Test login with custom registry
  - Test error handling for invalid credentials
  - _Requirements: All Requirement 1 criteria_

- [ ] 4. Implement logout CLI command

  - Add logout command to derpy/cli/main.py
  - Accept optional registry argument (default: docker.io)
  - Call AuthManager.logout() to remove credentials
  - Display confirmation message
  - Display informational message if no credentials exist
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [ ] 4.1 Write tests for logout command

  - Test logout with specified registry
  - Test logout with default registry
  - Test logout when credentials exist
  - Test logout when no credentials exist
  - _Requirements: All Requirement 2 criteria_

- [ ] 5. Integrate AuthManager with BaseImageManager

  - Add auth_manager parameter to BaseImageManager.**init**
  - Create AuthManager instance if not provided
  - Call auth_manager.get_credentials() in pull_base_image()
  - Pass credentials to RegistryClient via RegistryConfig
  - Handle case when no credentials exist (anonymous pull)
  - _Requirements: 6.1, 6.2, 6.3_

- [ ] 5.1 Update pull_base_image method

  - Check for stored credentials before creating RegistryClient
  - Create RegistryConfig with credentials if available
  - Create RegistryConfig without credentials for anonymous pulls
  - Pass enable_token_auth=True to RegistryClient for Docker Hub
  - Log whether using authenticated or anonymous pull
  - _Requirements: 6.1, 6.2, 6.3_

- [ ] 5.2 Handle authentication errors during build

  - Catch RegistryAuthenticationError during base image pull
  - Display clear error message with registry URL
  - Suggest running "derpy login [registry]" if authentication fails
  - Include original error details in error message
  - _Requirements: 6.4, 9.1, 9.3_

- [ ] 5.3 Handle sudo builds with user credentials

  - Detect if running as root (os.geteuid() == 0)
  - If root, check for SUDO_USER environment variable
  - Use SUDO_USER's home directory for auth file
  - Fall back to root's auth file if SUDO_USER not set
  - Log which auth file is being used
  - _Requirements: 6.5_

- [ ] 5.4 Write integration tests for build with authentication

  - Test building with private base image (mocked registry)
  - Test building without credentials (anonymous pull)
  - Test building with invalid credentials
  - Test sudo build using user credentials
  - _Requirements: All Requirement 6 criteria_

- [ ] 6. Integrate AuthManager with push command

  - Update push command in derpy/cli/main.py
  - Create AuthManager instance
  - Get credentials for target registry
  - Pass credentials to RegistryClient
  - Display error if no credentials found
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 6.1 Update push command implementation

  - Parse registry from image tag
  - Call auth_manager.get_credentials() for registry
  - Create RegistryConfig with credentials
  - Display error if credentials not found
  - Suggest running "derpy login [registry]"
  - _Requirements: 7.1, 7.2, 7.3_

- [ ] 6.2 Handle push authentication errors

  - Catch RegistryAuthenticationError during push
  - Display clear error message with registry URL
  - Include authentication details in error
  - Suggest checking credentials or re-running login
  - _Requirements: 7.4, 9.1, 9.3_

- [ ] 6.3 Write tests for push with authentication

  - Test push with valid credentials
  - Test push without credentials
  - Test push with invalid credentials
  - Test error messages and suggestions
  - _Requirements: All Requirement 7 criteria_

- [ ] 7. Add new exception classes

  - Add AuthenticationError base class to derpy/core/exceptions.py
  - Add CredentialStorageError for file I/O errors
  - Add TokenAuthenticationError for token request failures
  - Add InvalidCredentialsError for invalid username/password
  - Update exception hierarchy documentation
  - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [ ] 8. Update documentation

  - Update README.md with login/logout commands
  - Add authentication section to README
  - Document auth.json file format
  - Add examples for Docker Hub, private registries, AWS ECR
  - Update troubleshooting section with authentication errors
  - _Requirements: All requirements_

- [ ] 8.1 Update README with authentication commands

  - Add "Authentication" section after "Configuration"
  - Document "derpy login" command with examples
  - Document "derpy logout" command
  - Explain credential storage location
  - Add security notes about file permissions
  - _Requirements: 1.1, 1.2, 2.1, 3.1_

- [ ] 8.2 Add authentication examples

  - Add example for Docker Hub login
  - Add example for private registry login
  - Add example for AWS ECR login
  - Add example for building with private base image
  - Add example for pushing to authenticated registry
  - _Requirements: 1.1, 6.1, 7.1, 10.1, 10.2, 10.3_

- [ ] 8.3 Update troubleshooting section

  - Add "Authentication Failed" troubleshooting
  - Add "No Credentials Found" troubleshooting
  - Add "Token Request Failed" troubleshooting
  - Add "Rate Limit Exceeded" troubleshooting
  - Add "ECR Token Expired" troubleshooting
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 10.5_

- [ ] 9. Update steering documents

  - Update .kiro/steering/tech.md with authentication commands
  - Update .kiro/steering/structure.md with new auth.py module
  - Update .kiro/steering/product.md with authentication feature description
  - _Requirements: All requirements_

- [ ] 10. End-to-end testing
  - Test complete workflow: login -> build -> push -> logout
  - Test Docker Hub anonymous pulls
  - Test Docker Hub authenticated pulls
  - Test private registry authentication
  - Test AWS ECR authentication (if credentials available)
  - Test error scenarios and user feedback
  - _Requirements: All requirements_
