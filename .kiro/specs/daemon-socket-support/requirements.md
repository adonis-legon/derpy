# Requirements Document

## Introduction

This document specifies the requirements for Derpy version 0.2.0, which introduces a daemon-based architecture to eliminate the need for root privileges when running privileged operations like building container images. The daemon (derpyd) runs as a privileged service and communicates with the unprivileged CLI client via a Unix domain socket at /var/run/derpy.sock. Users gain access by being added to the 'derpy' system group, providing a secure and convenient alternative to using sudo for every build command.

## Glossary

- **Derpy CLI**: The command-line client application that users interact with directly
- **Derpyd**: The privileged daemon service that executes operations requiring elevated permissions
- **Unix Domain Socket**: An inter-process communication mechanism using filesystem paths (e.g., /var/run/derpy.sock)
- **Derpy Group**: A system user group ('derpy') that grants socket access permissions
- **Build Isolation**: The chroot-based execution environment for running container build commands
- **Client-Server Protocol**: The message format and communication pattern between CLI and daemon
- **Service Manager**: System service management tools (systemd on Linux, launchd on macOS)
- **Socket Permissions**: File system permissions controlling access to the Unix socket (typically 0660)
- **Request Message**: A structured message sent from CLI to daemon containing operation details
- **Response Message**: A structured message sent from daemon to CLI containing operation results

## Requirements

### Requirement 1

**User Story:** As a developer, I want to run derpy build commands without sudo, so that I can build container images conveniently without entering my password repeatedly.

#### Acceptance Criteria

1. WHEN a user in the derpy group runs a build command THEN the Derpy CLI SHALL communicate with Derpyd via the Unix socket without requiring sudo
2. WHEN a user not in the derpy group runs a build command THEN the Derpy CLI SHALL return a clear error message indicating they need to be added to the derpy group
3. WHEN the daemon is not running THEN the Derpy CLI SHALL return a clear error message indicating the daemon needs to be started
4. WHEN a build operation completes successfully THEN the Derpy CLI SHALL display the same output as the current sudo-based implementation
5. WHEN a build operation fails THEN the Derpy CLI SHALL display error messages with the same detail as the current implementation

### Requirement 2

**User Story:** As a system administrator, I want to install and configure the derpy daemon, so that users on my system can build containers without sudo.

#### Acceptance Criteria

1. WHEN the administrator installs derpy THEN the system SHALL create the derpy group if it does not exist
2. WHEN the administrator starts derpyd THEN the daemon SHALL create the Unix socket at /var/run/derpy.sock with 0660 permissions
3. WHEN the Unix socket is created THEN the Derpyd SHALL set the socket group ownership to the derpy group
4. WHEN the administrator adds a user to the derpy group THEN that user SHALL gain access to the socket after their next login
5. WHEN the system boots THEN the Derpyd SHALL start automatically if configured as a system service

### Requirement 3

**User Story:** As a developer, I want the daemon to handle build operations securely, so that unprivileged users cannot perform unauthorized operations.

#### Acceptance Criteria

1. WHEN the daemon receives a request THEN the Derpyd SHALL validate the request format before processing
2. WHEN the daemon validates socket connections THEN the Derpyd SHALL verify the connecting user is in the derpy group using socket credentials
3. WHEN the daemon executes build operations THEN the Derpyd SHALL use the same build isolation mechanisms as the current sudo-based implementation
4. WHEN the daemon encounters invalid requests THEN the Derpyd SHALL reject them and return descriptive error messages
5. WHEN the daemon processes concurrent requests THEN the Derpyd SHALL handle them safely without race conditions

### Requirement 4

**User Story:** As a developer, I want the CLI to communicate efficiently with the daemon, so that build operations complete without unnecessary delays.

#### Acceptance Criteria

1. WHEN the CLI sends a build request THEN the Derpy CLI SHALL serialize the request as JSON over the Unix socket
2. WHEN the daemon processes a request THEN the Derpyd SHALL stream build output back to the CLI in real-time
3. WHEN the CLI receives output THEN the Derpy CLI SHALL display it to the user immediately without buffering
4. WHEN a build operation completes THEN the Derpyd SHALL send a final response with the exit status
5. WHEN network errors occur THEN the Derpy CLI SHALL detect socket disconnections and report them clearly

### Requirement 5

**User Story:** As a system administrator, I want to manage the daemon lifecycle, so that I can start, stop, and monitor the service.

#### Acceptance Criteria

1. WHEN the administrator runs the daemon start command THEN the system SHALL launch derpyd as a background service
2. WHEN the administrator stops the daemon THEN the Derpyd SHALL complete in-progress operations before shutting down gracefully
3. WHEN the daemon shuts down THEN the Derpyd SHALL remove the Unix socket file
4. WHEN the administrator checks daemon status THEN the system SHALL report whether derpyd is running
5. WHEN the daemon encounters errors THEN the Derpyd SHALL log them to the system log for administrator review

### Requirement 6

**User Story:** As a developer, I want comprehensive documentation for daemon setup, so that I can configure my system correctly.

#### Acceptance Criteria

1. WHEN a user reads the installation documentation THEN the documentation SHALL include instructions for creating the derpy group
2. WHEN a user reads the daemon documentation THEN the documentation SHALL include systemd service file examples for Linux
3. WHEN a user reads the daemon documentation THEN the documentation SHALL include instructions for adding users to the derpy group
4. WHEN a user reads the troubleshooting documentation THEN the documentation SHALL include common socket permission issues and solutions
5. WHEN a user reads the architecture documentation THEN the documentation SHALL explain the client-daemon communication protocol

### Requirement 7

**User Story:** As a developer, I want the CLI to maintain backward compatibility, so that existing scripts and workflows continue to work.

#### Acceptance Criteria

1. WHEN a user runs derpy build with existing command-line flags THEN the Derpy CLI SHALL accept all current flags without changes
2. WHEN a user runs derpy build with sudo THEN the Derpy CLI SHALL detect the daemon is available and use it instead of direct execution
3. WHEN the daemon is unavailable and the user has sudo privileges THEN the Derpy CLI SHALL fall back to direct execution with a warning
4. WHEN a user runs non-privileged commands THEN the Derpy CLI SHALL execute them directly without daemon communication
5. WHEN a user runs derpy on a system without the daemon installed THEN the Derpy CLI SHALL fall back to the current sudo-based behavior

### Requirement 8

**User Story:** As a developer, I want the daemon to handle multiple concurrent build requests, so that multiple users can build images simultaneously.

#### Acceptance Criteria

1. WHEN multiple clients connect simultaneously THEN the Derpyd SHALL accept all connections without blocking
2. WHEN multiple build operations run concurrently THEN the Derpyd SHALL isolate their filesystem operations to prevent conflicts
3. WHEN concurrent builds access the base image cache THEN the Derpyd SHALL coordinate access to prevent corruption
4. WHEN concurrent builds complete THEN the Derpyd SHALL ensure each client receives only its own build output
5. WHEN the daemon reaches resource limits THEN the Derpyd SHALL queue requests and process them as resources become available

### Requirement 9

**User Story:** As a system administrator, I want the daemon to operate securely, so that it does not introduce security vulnerabilities.

#### Acceptance Criteria

1. WHEN the daemon starts THEN the Derpyd SHALL run as root but drop privileges for non-critical operations
2. WHEN the daemon creates temporary directories THEN the Derpyd SHALL set restrictive permissions to prevent unauthorized access
3. WHEN the daemon executes user-provided commands THEN the Derpyd SHALL validate and sanitize inputs to prevent command injection
4. WHEN the daemon handles file paths THEN the Derpyd SHALL validate paths to prevent directory traversal attacks
5. WHEN the daemon logs operations THEN the Derpyd SHALL avoid logging sensitive information like registry credentials

### Requirement 10

**User Story:** As a developer, I want clear error messages when daemon communication fails, so that I can diagnose and fix issues quickly.

#### Acceptance Criteria

1. WHEN the socket file does not exist THEN the Derpy CLI SHALL display a message indicating the daemon is not running
2. WHEN the user lacks socket permissions THEN the Derpy CLI SHALL display a message indicating they need to be added to the derpy group
3. WHEN the daemon is unresponsive THEN the Derpy CLI SHALL timeout after a reasonable period and display a timeout error
4. WHEN the daemon returns an error THEN the Derpy CLI SHALL display the error message with context about the failed operation
5. WHEN socket communication is interrupted THEN the Derpy CLI SHALL detect the interruption and display a connection lost message
