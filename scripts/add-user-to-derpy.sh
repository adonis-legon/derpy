#!/bin/bash
# Derpy User Management Script
# This script adds a user to the derpy group to grant daemon access
#
# NOTE: This script is designed for Linux systems only.
# It requires usermod, getent, and other Linux-specific commands.
# The derpy daemon is not supported on macOS or Windows.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_error() {
    echo -e "${RED}✗ $1${NC}" >&2
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run as root"
    echo "Please run: sudo $0 <username>"
    exit 1
fi

# Check if username argument is provided
if [ $# -eq 0 ]; then
    print_error "No username provided"
    echo ""
    echo "Usage: sudo $0 <username>"
    echo ""
    echo "Example:"
    echo "  sudo $0 john"
    echo ""
    exit 1
fi

USERNAME="$1"

echo ""
echo "=========================================="
echo "  Add User to Derpy Group"
echo "=========================================="
echo ""

# Check if user exists
if ! id "$USERNAME" &>/dev/null; then
    print_error "User '$USERNAME' does not exist"
    echo ""
    echo "Please create the user first or check the username spelling."
    exit 1
fi

print_success "User '$USERNAME' exists"

# Check if derpy group exists
if ! getent group derpy > /dev/null 2>&1; then
    print_error "derpy group does not exist"
    echo ""
    echo "The derpy daemon may not be installed. Please run:"
    echo "  sudo scripts/install-daemon.sh"
    echo ""
    exit 1
fi

print_success "derpy group exists"

# Check if user is already in the derpy group
if id -nG "$USERNAME" | grep -qw "derpy"; then
    print_info "User '$USERNAME' is already in the derpy group"
    echo ""
    echo "No changes needed. The user already has access to the derpy daemon."
    exit 0
fi

# Add user to derpy group
print_info "Adding user '$USERNAME' to derpy group..."
if usermod -aG derpy "$USERNAME"; then
    print_success "User '$USERNAME' added to derpy group"
else
    print_error "Failed to add user '$USERNAME' to derpy group"
    exit 1
fi

# Verify user was added successfully
if id -nG "$USERNAME" | grep -qw "derpy"; then
    print_success "Verified: User '$USERNAME' is now in the derpy group"
else
    print_error "Verification failed: User '$USERNAME' is not in the derpy group"
    echo "The usermod command succeeded but verification failed."
    echo "This may indicate a system issue."
    exit 1
fi

echo ""
echo "=========================================="
echo "  Success!"
echo "=========================================="
echo ""
print_success "User '$USERNAME' has been granted access to the derpy daemon"
echo ""
echo "⚠️  IMPORTANT: The user must log out and log back in for the"
echo "   group membership change to take effect."
echo ""
echo "After logging back in, the user can verify access with:"
echo "  ${GREEN}groups${NC}  (should show 'derpy' in the list)"
echo "  ${GREEN}derpy build . -f Dockerfile -t myapp:latest${NC}"
echo ""
echo "If the user is currently logged in, they should:"
echo "  1. Save any work"
echo "  2. Log out completely"
echo "  3. Log back in"
echo ""
echo "Alternatively, for SSH sessions, the user can run:"
echo "  ${GREEN}newgrp derpy${NC}  (starts a new shell with updated groups)"
echo ""

</content>
