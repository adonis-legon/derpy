# Distribution Testing Guide

This document provides a comprehensive testing procedure for verifying Derpy daemon installation and functionality across multiple Linux distributions.

## Overview

The Derpy daemon (derpyd) must be tested on multiple Linux distributions to ensure compatibility and identify any distribution-specific issues. This guide covers testing procedures for:

- Ubuntu 22.04 LTS
- Debian 12 (Bookworm)
- Fedora 39
- Arch Linux (rolling release)

## Testing Environment Setup

### Option 1: Virtual Machines

Use VirtualBox, VMware, or similar virtualization software:

```bash
# Download ISO images
# Ubuntu: https://ubuntu.com/download/server
# Debian: https://www.debian.org/distrib/
# Fedora: https://fedoraproject.org/server/download/
# Arch: https://archlinux.org/download/

# Create VMs with:
# - 2GB RAM minimum
# - 20GB disk space
# - Network access enabled
```

### Option 2: Docker Containers (Limited Testing)

For basic installation testing only (systemd functionality limited):

```bash
# Ubuntu
docker run -it --privileged ubuntu:22.04 /bin/bash

# Debian
docker run -it --privileged debian:12 /bin/bash

# Fedora
docker run -it --privileged fedora:39 /bin/bash

# Arch
docker run -it --privileged archlinux:latest /bin/bash
```

**Note**: Full systemd testing requires VMs or physical machines.

### Option 3: Cloud Instances

Use cloud providers for testing:

- AWS EC2 (t2.micro for testing)
- DigitalOcean Droplets
- Linode instances
- Google Cloud Compute Engine

## Pre-Installation Checklist

For each distribution, verify:

- [ ] Python version available (3.10+)
- [ ] systemd is installed and running
- [ ] pip is available
- [ ] Root/sudo access available
- [ ] Internet connectivity working

## Test Procedure

### Phase 1: System Preparation

#### Ubuntu 22.04

```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Install prerequisites
sudo apt install -y python3 python3-pip python3-venv git

# Verify Python version
python3 --version  # Should be 3.10+

# Verify systemd
systemctl --version
```

#### Debian 12

```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Install prerequisites
sudo apt install -y python3 python3-pip python3-venv git

# Verify Python version
python3 --version  # Should be 3.11+

# Verify systemd
systemctl --version
```

#### Fedora 39

```bash
# Update system
sudo dnf update -y

# Install prerequisites
sudo dnf install -y python3 python3-pip git

# Verify Python version
python3 --version  # Should be 3.11+

# Verify systemd
systemctl --version
```

#### Arch Linux

```bash
# Update system
sudo pacman -Syu --noconfirm

# Install prerequisites
sudo pacman -S --noconfirm python python-pip git

# Verify Python version
python --version  # Should be 3.11+

# Verify systemd
systemctl --version
```

### Phase 2: Derpy Installation

For each distribution:

```bash
# Clone repository
git clone https://github.com/yourusername/derpy.git
cd derpy

# Install derpy
sudo pip install -e .

# Verify installation
derpy --version
derpyd --version

# Record versions
echo "Derpy version: $(derpy --version)" >> ~/test-results.txt
echo "Python version: $(python3 --version)" >> ~/test-results.txt
echo "Distribution: $(cat /etc/os-release | grep PRETTY_NAME)" >> ~/test-results.txt
```

### Phase 3: Daemon Installation

```bash
# Run installation script
sudo bash scripts/install-daemon.sh

# Verify script output
# Expected: Success message with socket path

# Check service status
sudo systemctl status derpyd

# Verify socket creation
ls -l /var/run/derpy.sock

# Expected output:
# srw-rw---- 1 root derpy 0 <date> /var/run/derpy.sock

# Verify group creation
getent group derpy

# Record results
echo "Socket permissions: $(ls -l /var/run/derpy.sock)" >> ~/test-results.txt
echo "Service status: $(systemctl is-active derpyd)" >> ~/test-results.txt
```

### Phase 4: User Management

```bash
# Add current user to derpy group
sudo bash scripts/add-user-to-derpy.sh $USER

# Verify group membership (before logout)
groups | grep derpy  # May not show yet

# Verify group file
grep derpy /etc/group

# Log out and back in (or use newgrp)
newgrp derpy

# Verify group membership (after)
groups | grep derpy  # Should show derpy

# Record results
echo "User groups: $(groups)" >> ~/test-results.txt
```

### Phase 5: Basic Functionality Testing

```bash
# Create test directory
mkdir -p ~/derpy-test
cd ~/derpy-test

# Create simple Dockerfile
cat > Dockerfile << 'EOF'
FROM alpine:latest
RUN echo "Hello from Derpy on $(cat /etc/os-release | grep PRETTY_NAME)"
CMD ["/bin/sh"]
EOF

# Test build without sudo (should use daemon)
derpy build . -f Dockerfile -t test-alpine:latest

# Verify success
echo "Build exit code: $?" >> ~/test-results.txt

# Test list command
derpy ls

# Test with Ubuntu base image
cat > Dockerfile.ubuntu << 'EOF'
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y curl
RUN curl --version
CMD ["/bin/bash"]
EOF

derpy build . -f Dockerfile.ubuntu -t test-ubuntu:latest

# Record results
echo "Ubuntu build exit code: $?" >> ~/test-results.txt
```

### Phase 6: Systemd Integration Testing

```bash
# Test service start/stop
sudo systemctl stop derpyd
sleep 2
sudo systemctl status derpyd  # Should be inactive

sudo systemctl start derpyd
sleep 2
sudo systemctl status derpyd  # Should be active

# Test restart
sudo systemctl restart derpyd
sleep 2
sudo systemctl status derpyd  # Should be active

# Test enable/disable
sudo systemctl disable derpyd
systemctl is-enabled derpyd  # Should be disabled

sudo systemctl enable derpyd
systemctl is-enabled derpyd  # Should be enabled

# Test logs
sudo journalctl -u derpyd -n 20

# Record results
echo "Systemd integration: PASS" >> ~/test-results.txt
```

### Phase 7: Concurrent Build Testing

```bash
# Create test script for concurrent builds
cat > concurrent-test.sh << 'EOF'
#!/bin/bash
for i in {1..3}; do
  (
    mkdir -p /tmp/derpy-test-$i
    cd /tmp/derpy-test-$i
    cat > Dockerfile << 'DOCKERFILE'
FROM alpine:latest
RUN echo "Build $i"
RUN sleep 2
CMD ["/bin/sh"]
DOCKERFILE
    derpy build . -f Dockerfile -t test-concurrent-$i:latest
    echo "Build $i completed with exit code: $?"
  ) &
done
wait
EOF

chmod +x concurrent-test.sh
./concurrent-test.sh

# Verify all builds succeeded
derpy ls | grep test-concurrent

# Record results
echo "Concurrent builds: PASS" >> ~/test-results.txt
```

### Phase 8: Error Handling Testing

```bash
# Test with daemon stopped
sudo systemctl stop derpyd
derpy build . -f Dockerfile -t test-error:latest 2>&1 | tee error-output.txt

# Should show clear error message about daemon not running
grep -i "daemon not running" error-output.txt
echo "Error message test: $?" >> ~/test-results.txt

# Restart daemon
sudo systemctl start derpyd

# Test with invalid user (not in group)
sudo useradd -m testuser
sudo -u testuser derpy build . -f Dockerfile -t test-error:latest 2>&1 | tee error-output2.txt

# Should show clear error about group membership
grep -i "derpy group" error-output2.txt
echo "Permission error test: $?" >> ~/test-results.txt

# Cleanup
sudo userdel -r testuser
```

### Phase 9: Reboot Testing

```bash
# Verify daemon starts on boot
sudo reboot

# After reboot, log back in and check
sudo systemctl status derpyd  # Should be active

# Verify socket exists
ls -l /var/run/derpy.sock

# Test build after reboot
cd ~/derpy-test
derpy build . -f Dockerfile -t test-reboot:latest

# Record results
echo "Reboot test: PASS" >> ~/test-results.txt
```

### Phase 10: Cleanup and Uninstallation

```bash
# Stop service
sudo systemctl stop derpyd
sudo systemctl disable derpyd

# Remove service file
sudo rm /etc/systemd/system/derpyd.service
sudo systemctl daemon-reload

# Remove socket
sudo rm -f /var/run/derpy.sock

# Remove group
sudo groupdel derpy

# Uninstall package
sudo pip uninstall -y derpy

# Verify cleanup
systemctl status derpyd  # Should not exist
ls /var/run/derpy.sock  # Should not exist
getent group derpy  # Should not exist

# Record results
echo "Cleanup: PASS" >> ~/test-results.txt
```

## Results Documentation

### Test Results Template

Create a file `test-results-<distribution>.md` for each distribution:

```markdown
# Derpy Daemon Test Results: <Distribution Name>

## System Information

- Distribution: <name and version>
- Kernel: <uname -r>
- Python: <python3 --version>
- systemd: <systemctl --version>
- Test Date: <date>
- Tester: <name>

## Test Results

### Phase 1: System Preparation

- [ ] Python 3.10+ available
- [ ] systemd installed and running
- [ ] pip available
- [ ] Prerequisites installed successfully

**Notes**: <any issues or observations>

### Phase 2: Derpy Installation

- [ ] Package installed successfully
- [ ] derpy command available
- [ ] derpyd command available
- [ ] Version check passed

**Notes**: <any issues or observations>

### Phase 3: Daemon Installation

- [ ] Installation script completed successfully
- [ ] Socket created at /var/run/derpy.sock
- [ ] Socket has correct permissions (0660)
- [ ] Socket has correct ownership (root:derpy)
- [ ] derpy group created
- [ ] Service started successfully

**Notes**: <any issues or observations>

### Phase 4: User Management

- [ ] User added to derpy group successfully
- [ ] Group membership verified after re-login
- [ ] Helper script worked correctly

**Notes**: <any issues or observations>

### Phase 5: Basic Functionality

- [ ] Alpine build succeeded without sudo
- [ ] Ubuntu build succeeded without sudo
- [ ] List command worked
- [ ] Output streamed in real-time

**Notes**: <any issues or observations>

### Phase 6: Systemd Integration

- [ ] Service start/stop worked
- [ ] Service restart worked
- [ ] Service enable/disable worked
- [ ] Logs accessible via journalctl

**Notes**: <any issues or observations>

### Phase 7: Concurrent Builds

- [ ] Multiple builds ran simultaneously
- [ ] No race conditions observed
- [ ] All builds completed successfully
- [ ] Output properly isolated

**Notes**: <any issues or observations>

### Phase 8: Error Handling

- [ ] Clear error when daemon not running
- [ ] Clear error for unauthorized users
- [ ] Fallback behavior works correctly

**Notes**: <any issues or observations>

### Phase 9: Reboot Testing

- [ ] Daemon started automatically after reboot
- [ ] Socket recreated correctly
- [ ] Builds work after reboot

**Notes**: <any issues or observations>

### Phase 10: Cleanup

- [ ] Service stopped and disabled
- [ ] Service file removed
- [ ] Socket removed
- [ ] Group removed
- [ ] Package uninstalled

**Notes**: <any issues or observations>

## Distribution-Specific Issues

<Document any issues specific to this distribution>

## Recommendations

<Any recommendations for documentation updates or code changes>

## Overall Result

- [ ] PASS - All tests passed
- [ ] PASS WITH NOTES - Tests passed with minor issues
- [ ] FAIL - Critical issues found

**Summary**: <brief summary of test results>
```

## Known Distribution Differences

### Package Managers

- **Ubuntu/Debian**: apt (dpkg)
- **Fedora**: dnf (rpm)
- **Arch**: pacman

### Python Command

- **Ubuntu/Debian/Fedora**: `python3`
- **Arch**: `python` (python3 is default)

### pip Installation

- **Ubuntu/Debian**: May need `python3-pip` package
- **Fedora**: May need `python3-pip` package
- **Arch**: May need `python-pip` package

### systemd Paths

All distributions use standard systemd paths:

- Service files: `/etc/systemd/system/`
- Journal logs: `journalctl`

## Automation Script

For automated testing across distributions, use this script:

```bash
#!/bin/bash
# automated-distribution-test.sh

DISTRIBUTIONS=("ubuntu:22.04" "debian:12" "fedora:39" "archlinux:latest")

for distro in "${DISTRIBUTIONS[@]}"; do
  echo "Testing on $distro..."

  # Create container
  docker run -d --name derpy-test-$distro --privileged $distro sleep infinity

  # Copy test scripts
  docker cp . derpy-test-$distro:/root/derpy

  # Run tests
  docker exec derpy-test-$distro /root/derpy/scripts/run-distribution-tests.sh

  # Copy results
  docker cp derpy-test-$distro:/root/test-results.txt ./test-results-$distro.txt

  # Cleanup
  docker stop derpy-test-$distro
  docker rm derpy-test-$distro

  echo "Completed testing on $distro"
done

echo "All distribution tests completed"
```

## Reporting Issues

When reporting distribution-specific issues, include:

1. Distribution name and version
2. Kernel version (`uname -r`)
3. Python version
4. systemd version
5. Complete error messages
6. Relevant log output (`journalctl -u derpyd`)
7. Steps to reproduce

## Next Steps

After completing distribution testing:

1. Update `docs/installation.md` with any distribution-specific notes
2. Update `README.md` with tested distribution list
3. Create GitHub issues for any distribution-specific bugs
4. Update CI/CD pipeline to include distribution testing
5. Document workarounds for known issues

## Continuous Testing

Consider setting up automated testing:

- GitHub Actions with matrix builds for each distribution
- Weekly automated tests on latest distribution versions
- Notification system for test failures
- Automated issue creation for regressions
