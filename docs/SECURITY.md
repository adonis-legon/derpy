# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.0   | :white_check_mark: |
| 0.1.0   | :x:                |

## Security Features

Derpy version 0.2.0 includes comprehensive security features for the daemon socket support:

### 1. Access Control

- **Group-based authentication:** Only users in the `derpy` group can access the daemon
- **Socket credential validation:** Uses `SO_PEERCRED` to verify client credentials
- **Socket permissions:** Unix socket has 0660 permissions (owner + group only)

### 2. Input Validation

- **Tag validation:** Whitelist approach for image tags (alphanumeric + `._:/-`)
- **Path validation:** Directory traversal detection and prevention
- **Command validation:** Shell injection prevention with pattern detection
- **Build args validation:** Shell metacharacter detection

### 3. Privilege Management

- **Privilege dropping:** Daemon drops root privileges for non-critical operations
- **Correct order:** Group privileges dropped before user privileges
- **Capability detection:** Checks if running as root before attempting drops

### 4. File System Security

- **Restrictive permissions:** Temporary directories created with 0700 (owner-only)
- **Path boundary validation:** Ensures paths stay within allowed directories
- **Symlink resolution:** Resolves symbolic links to detect escapes

### 5. Credential Protection

- **Log sanitization:** Removes passwords, tokens, and API keys from logs
- **Bearer token redaction:** OAuth2 bearer tokens sanitized
- **Basic auth redaction:** Base64-encoded credentials sanitized
- **Recursive sanitization:** Handles nested data structures

## Security Audit

A comprehensive security audit was completed on November 22, 2025:

- **Property-Based Tests:** 1000+ randomized test cases
- **Attack Simulations:** 22 explicit attack scenarios
- **Code Coverage:** 95%+ for security modules
- **Result:** ✅ ALL TESTS PASSED

See [Security Audit Report](security-audit.md) for details.

## Reporting a Vulnerability

If you discover a security vulnerability in Derpy, please report it by:

1. **DO NOT** open a public GitHub issue
2. Email the maintainers directly (see CONTRIBUTING.md)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and work with you to address the issue.

## Security Best Practices

When using Derpy daemon mode:

### For System Administrators

1. **Limit group membership:** Only add trusted users to the `derpy` group
2. **Monitor logs:** Review daemon logs regularly for suspicious activity
3. **Keep updated:** Apply security updates promptly
4. **Audit access:** Periodically review group membership
5. **Secure socket:** Ensure `/var/run/derpy.sock` has correct permissions (0660)

### For Users

1. **Validate inputs:** Don't build untrusted Dockerfiles
2. **Review build contexts:** Ensure build contexts don't contain sensitive data
3. **Use specific tags:** Avoid using `latest` tag in production
4. **Check credentials:** Verify registry credentials are stored securely
5. **Monitor builds:** Review build output for unexpected behavior

## Known Limitations

The following limitations are documented and will be addressed in future releases:

1. **TOCTOU Race Conditions:** Time-of-check-time-of-use between path validation and use
2. **URL-Encoded Traversal:** URL-encoded directory traversal patterns not explicitly handled
3. **Rate Limiting:** No rate limiting on connection attempts
4. **Path Complexity:** No explicit limits on path depth or complexity

These limitations are considered **low severity** and do not pose immediate security risks.

## Security Testing

Derpy includes comprehensive security tests:

- **Property-Based Tests:** `tests/test_daemon_security.py`
- **Attack Simulations:** `tests/test_security_attack_simulation.py`
- **Integration Tests:** Various integration test files

Run security tests:

```bash
pytest tests/test_daemon_security.py -v
pytest tests/test_security_attack_simulation.py -v
```

## Security Hardening

Additional security hardening recommendations:

### Linux Security Modules

- Consider using AppArmor or SELinux profiles
- Restrict daemon capabilities with systemd settings
- Use seccomp filters to limit syscalls

### Network Security

- Daemon uses Unix sockets only (no network exposure)
- No remote access by design
- All communication is local

### Monitoring

- Enable audit logging for security events
- Monitor daemon logs: `journalctl -u derpyd`
- Set up alerts for authentication failures

## Compliance

Derpy's security implementation follows:

- **OWASP Top 10:** Protection against common web vulnerabilities
- **CWE-78:** OS Command Injection prevention
- **CWE-22:** Path Traversal prevention
- **CWE-532:** Information Exposure Through Log Files prevention
- **CWE-250:** Execution with Unnecessary Privileges prevention

## Security Updates

Security updates will be released as needed. Subscribe to:

- GitHub Security Advisories
- Release notifications
- Security mailing list (if available)

## Contact

For security concerns, contact the maintainers through the channels listed in CONTRIBUTING.md.

---

**Last Updated:** November 22, 2025  
**Security Audit Date:** November 22, 2025  
**Next Audit:** TBD
