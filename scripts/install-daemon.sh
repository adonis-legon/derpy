#!/bin/bash
# Derpy Daemon Installation Script
# This script installs the derpyd daemon service on Linux systems with systemd

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
    echo "Please run: sudo $0"
    exit 1
fi

print_success "Running as root"

# Check if systemd is available
if ! command -v systemctl &> /dev/null; then
    print_error "systemd is not available on this system"
    echo "This installation script requires systemd for service management."
    exit 1
fi

print_success "systemd detected"

# Determine the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo ""
echo "=========================================="
echo "  Derpy Daemon Installation"
echo "=========================================="
echo ""

# Create derpy group if it doesn't exist
if getent group derpy > /dev/null 2>&1; then
    print_info "derpy group already exists"
else
    print_info "Creating derpy group..."
    groupadd -r derpy
    print_success "derpy group created"
fi

# Install derpy package with pip
print_info "Installing derpy package..."
cd "$PROJECT_ROOT"

# Check if we're in a virtual environment
if [ -n "$VIRTUAL_ENV" ]; then
    print_error "Cannot install in a virtual environment"
    echo "Please deactivate the virtual environment and run again."
    exit 1
fi

# Install the package
if pip install -e . > /dev/null 2>&1; then
    print_success "derpy package installed"
else
    print_error "Failed to install derpy package"
    exit 1
fi

# Verify derpyd binary is available
if ! command -v derpyd &> /dev/null; then
    print_error "derpyd binary not found after installation"
    echo "Expected location: /usr/local/bin/derpyd"
    exit 1
fi

print_success "derpyd binary found at $(which derpyd)"

# Copy systemd service file
print_info "Installing systemd service file..."
SERVICE_FILE="$SCRIPT_DIR/systemd/derpyd.service"

if [ ! -f "$SERVICE_FILE" ]; then
    print_error "Service file not found: $SERVICE_FILE"
    exit 1
fi

cp "$SERVICE_FILE" /etc/systemd/system/derpyd.service
print_success "Service file copied to /etc/systemd/system/derpyd.service"

# Reload systemd daemon
print_info "Reloading systemd daemon..."
systemctl daemon-reload
print_success "systemd daemon reloaded"

# Enable derpyd service
print_info "Enabling derpyd service..."
systemctl enable derpyd
print_success "derpyd service enabled (will start on boot)"

# Start derpyd service
print_info "Starting derpyd service..."
systemctl start derpyd
print_success "derpyd service started"

# Wait for socket to be created (up to 5 seconds)
print_info "Waiting for socket to be created..."
SOCKET_PATH="/var/run/derpy.sock"
WAIT_COUNT=0
MAX_WAIT=10

while [ ! -S "$SOCKET_PATH" ] && [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    sleep 0.5
    WAIT_COUNT=$((WAIT_COUNT + 1))
done

# Verify socket exists and has correct permissions
if [ -S "$SOCKET_PATH" ]; then
    print_success "Daemon socket created at $SOCKET_PATH"
    
    # Check socket permissions
    SOCKET_PERMS=$(stat -c "%a" "$SOCKET_PATH" 2>/dev/null || stat -f "%Lp" "$SOCKET_PATH" 2>/dev/null)
    SOCKET_GROUP=$(stat -c "%G" "$SOCKET_PATH" 2>/dev/null || stat -f "%Sg" "$SOCKET_PATH" 2>/dev/null)
    
    echo ""
    echo "Socket details:"
    ls -l "$SOCKET_PATH"
    echo ""
    
    # Verify permissions are 0660
    if [ "$SOCKET_PERMS" = "660" ]; then
        print_success "Socket permissions are correct (0660)"
    else
        print_error "Socket permissions are $SOCKET_PERMS (expected 0660)"
        echo "The daemon may not have set permissions correctly."
    fi
    
    # Verify group is derpy
    if [ "$SOCKET_GROUP" = "derpy" ]; then
        print_success "Socket group ownership is correct (derpy)"
    else
        print_error "Socket group is $SOCKET_GROUP (expected derpy)"
        echo "The daemon may not have set group ownership correctly."
    fi
else
    print_error "Failed to create daemon socket at $SOCKET_PATH"
    echo ""
    echo "Checking daemon status:"
    systemctl status derpyd --no-pager
    echo ""
    echo "Checking daemon logs:"
    journalctl -u derpyd -n 20 --no-pager
    exit 1
fi

# Check daemon status
DAEMON_STATUS=$(systemctl is-active derpyd)
if [ "$DAEMON_STATUS" = "active" ]; then
    print_success "derpyd service is running"
else
    print_error "derpyd service is not active (status: $DAEMON_STATUS)"
    exit 1
fi

echo ""
echo "=========================================="
echo "  Installation Complete!"
echo "=========================================="
echo ""
print_success "Derpy daemon has been successfully installed and started"
echo ""
echo "Next steps:"
echo ""
echo "1. Add users to the derpy group to grant them access:"
echo "   ${GREEN}sudo usermod -aG derpy <username>${NC}"
echo ""
echo "2. Users must log out and back in for group changes to take effect"
echo ""
echo "3. Verify access by running (as the user):"
echo "   ${GREEN}derpy build . -f Dockerfile -t myapp:latest${NC}"
echo ""
echo "Service management commands:"
echo "  - Check status:  ${GREEN}sudo systemctl status derpyd${NC}"
echo "  - View logs:     ${GREEN}sudo journalctl -u derpyd -f${NC}"
echo "  - Restart:       ${GREEN}sudo systemctl restart derpyd${NC}"
echo "  - Stop:          ${GREEN}sudo systemctl stop derpyd${NC}"
echo ""
echo "For troubleshooting, see: docs/troubleshooting.md"
echo ""
