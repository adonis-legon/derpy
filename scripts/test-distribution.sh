#!/bin/bash
# test-distribution.sh - Automated distribution testing script for Derpy daemon
#
# Usage: ./test-distribution.sh [distribution]
# Example: ./test-distribution.sh ubuntu:22.04
#
# This script automates the testing procedure for a specific Linux distribution.
# It can be run inside a VM or container of the target distribution.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results
RESULTS_FILE="$HOME/derpy-test-results.txt"
PASSED=0
FAILED=0

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

test_pass() {
    echo "[PASS] $1" | tee -a "$RESULTS_FILE"
    ((PASSED++))
}

test_fail() {
    echo "[FAIL] $1" | tee -a "$RESULTS_FILE"
    ((FAILED++))
}

# Initialize results file
init_results() {
    echo "=== Derpy Daemon Distribution Test Results ===" > "$RESULTS_FILE"
    echo "Date: $(date)" >> "$RESULTS_FILE"
    echo "Distribution: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)" >> "$RESULTS_FILE"
    echo "Kernel: $(uname -r)" >> "$RESULTS_FILE"
    echo "Python: $(python3 --version 2>&1 || python --version 2>&1)" >> "$RESULTS_FILE"
    echo "systemd: $(systemctl --version | head -n1)" >> "$RESULTS_FILE"
    echo "" >> "$RESULTS_FILE"
}

# Test Phase 1: Prerequisites
test_prerequisites() {
    log_info "Phase 1: Testing prerequisites..."
    
    # Check Python version
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        test_pass "Python 3 available: $PYTHON_VERSION"
    elif command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version | cut -d' ' -f2)
        test_pass "Python available: $PYTHON_VERSION"
    else
        test_fail "Python not found"
        return 1
    fi
    
    # Check systemd
    if command -v systemctl &> /dev/null; then
        test_pass "systemd available"
    else
        test_fail "systemd not found"
        return 1
    fi
    
    # Check pip
    if command -v pip3 &> /dev/null || command -v pip &> /dev/null; then
        test_pass "pip available"
    else
        test_fail "pip not found"
        return 1
    fi
    
    # Check git
    if command -v git &> /dev/null; then
        test_pass "git available"
    else
        test_fail "git not found"
        return 1
    fi
}

# Test Phase 2: Installation
test_installation() {
    log_info "Phase 2: Testing installation..."
    
    # Check if derpy is already installed
    if command -v derpy &> /dev/null; then
        test_pass "derpy command available"
    else
        test_fail "derpy command not found"
        return 1
    fi
    
    # Check derpyd
    if command -v derpyd &> /dev/null; then
        test_pass "derpyd command available"
    else
        test_fail "derpyd command not found"
        return 1
    fi
    
    # Check versions
    if derpy --version &> /dev/null; then
        test_pass "derpy version check: $(derpy --version)"
    else
        test_fail "derpy version check failed"
    fi
}

# Test Phase 3: Daemon Installation
test_daemon_installation() {
    log_info "Phase 3: Testing daemon installation..."
    
    # Check service file
    if [ -f /etc/systemd/system/derpyd.service ]; then
        test_pass "systemd service file exists"
    else
        test_fail "systemd service file not found"
        return 1
    fi
    
    # Check service status
    if systemctl is-active --quiet derpyd; then
        test_pass "derpyd service is active"
    else
        test_fail "derpyd service is not active"
        log_warn "Service status: $(systemctl status derpyd --no-pager)"
    fi
    
    # Check socket
    if [ -S /var/run/derpy.sock ]; then
        test_pass "Unix socket exists"
        
        # Check permissions
        PERMS=$(stat -c %a /var/run/derpy.sock 2>/dev/null || stat -f %A /var/run/derpy.sock 2>/dev/null)
        if [ "$PERMS" = "660" ]; then
            test_pass "Socket permissions correct (660)"
        else
            test_fail "Socket permissions incorrect: $PERMS (expected 660)"
        fi
        
        # Check ownership
        OWNER=$(stat -c %U /var/run/derpy.sock 2>/dev/null || stat -f %Su /var/run/derpy.sock 2>/dev/null)
        GROUP=$(stat -c %G /var/run/derpy.sock 2>/dev/null || stat -f %Sg /var/run/derpy.sock 2>/dev/null)
        
        if [ "$OWNER" = "root" ]; then
            test_pass "Socket owner correct (root)"
        else
            test_fail "Socket owner incorrect: $OWNER (expected root)"
        fi
        
        if [ "$GROUP" = "derpy" ]; then
            test_pass "Socket group correct (derpy)"
        else
            test_fail "Socket group incorrect: $GROUP (expected derpy)"
        fi
    else
        test_fail "Unix socket not found"
    fi
    
    # Check derpy group
    if getent group derpy &> /dev/null; then
        test_pass "derpy group exists"
    else
        test_fail "derpy group not found"
    fi
}

# Test Phase 4: User Management
test_user_management() {
    log_info "Phase 4: Testing user management..."
    
    # Check if current user is in derpy group
    if groups | grep -q derpy; then
        test_pass "Current user in derpy group"
    else
        test_fail "Current user not in derpy group"
        log_warn "Run: sudo usermod -aG derpy $USER && newgrp derpy"
    fi
}

# Test Phase 5: Basic Functionality
test_basic_functionality() {
    log_info "Phase 5: Testing basic functionality..."
    
    # Create test directory
    TEST_DIR=$(mktemp -d)
    cd "$TEST_DIR"
    
    # Create simple Dockerfile
    cat > Dockerfile << 'EOF'
FROM alpine:latest
RUN echo "Test build from distribution testing"
CMD ["/bin/sh"]
EOF
    
    # Test build
    log_info "Running test build..."
    if derpy build . -f Dockerfile -t derpy-test:latest &> build-output.txt; then
        test_pass "Build command succeeded"
    else
        test_fail "Build command failed"
        log_error "Build output:"
        cat build-output.txt
    fi
    
    # Test list
    if derpy ls &> /dev/null; then
        test_pass "List command succeeded"
    else
        test_fail "List command failed"
    fi
    
    # Cleanup
    cd - > /dev/null
    rm -rf "$TEST_DIR"
}

# Test Phase 6: Systemd Integration
test_systemd_integration() {
    log_info "Phase 6: Testing systemd integration..."
    
    # Test stop
    if systemctl stop derpyd &> /dev/null; then
        test_pass "Service stop succeeded"
    else
        test_fail "Service stop failed"
    fi
    
    sleep 2
    
    # Verify stopped
    if ! systemctl is-active --quiet derpyd; then
        test_pass "Service stopped successfully"
    else
        test_fail "Service still active after stop"
    fi
    
    # Test start
    if systemctl start derpyd &> /dev/null; then
        test_pass "Service start succeeded"
    else
        test_fail "Service start failed"
    fi
    
    sleep 2
    
    # Verify started
    if systemctl is-active --quiet derpyd; then
        test_pass "Service started successfully"
    else
        test_fail "Service not active after start"
    fi
    
    # Test restart
    if systemctl restart derpyd &> /dev/null; then
        test_pass "Service restart succeeded"
    else
        test_fail "Service restart failed"
    fi
    
    sleep 2
    
    # Check enabled status
    if systemctl is-enabled --quiet derpyd; then
        test_pass "Service is enabled for boot"
    else
        test_fail "Service not enabled for boot"
    fi
    
    # Test logs
    if journalctl -u derpyd -n 10 &> /dev/null; then
        test_pass "Journal logs accessible"
    else
        test_fail "Journal logs not accessible"
    fi
}

# Test Phase 7: Error Handling
test_error_handling() {
    log_info "Phase 7: Testing error handling..."
    
    # Stop daemon
    systemctl stop derpyd
    sleep 2
    
    # Try to build (should show error)
    TEST_DIR=$(mktemp -d)
    cd "$TEST_DIR"
    cat > Dockerfile << 'EOF'
FROM alpine:latest
CMD ["/bin/sh"]
EOF
    
    if derpy build . -f Dockerfile -t error-test:latest 2>&1 | grep -qi "daemon"; then
        test_pass "Clear error message when daemon not running"
    else
        test_fail "Error message unclear when daemon not running"
    fi
    
    # Restart daemon
    systemctl start derpyd
    sleep 2
    
    # Cleanup
    cd - > /dev/null
    rm -rf "$TEST_DIR"
}

# Main test execution
main() {
    log_info "Starting Derpy daemon distribution tests..."
    log_info "This script assumes Derpy is already installed"
    
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
    
    # Initialize results
    init_results
    
    # Run test phases
    test_prerequisites || log_warn "Prerequisites test had failures"
    test_installation || log_warn "Installation test had failures"
    test_daemon_installation || log_warn "Daemon installation test had failures"
    test_user_management || log_warn "User management test had failures"
    test_basic_functionality || log_warn "Basic functionality test had failures"
    test_systemd_integration || log_warn "Systemd integration test had failures"
    test_error_handling || log_warn "Error handling test had failures"
    
    # Summary
    echo "" | tee -a "$RESULTS_FILE"
    echo "=== Test Summary ===" | tee -a "$RESULTS_FILE"
    echo "Passed: $PASSED" | tee -a "$RESULTS_FILE"
    echo "Failed: $FAILED" | tee -a "$RESULTS_FILE"
    
    if [ $FAILED -eq 0 ]; then
        log_info "All tests passed!"
        echo "OVERALL: PASS" | tee -a "$RESULTS_FILE"
        exit 0
    else
        log_error "Some tests failed"
        echo "OVERALL: FAIL" | tee -a "$RESULTS_FILE"
        exit 1
    fi
}

# Run main function
main "$@"
