#!/bin/bash
#
# Performance testing script for Derpy daemon
#
# This script runs comprehensive performance tests and generates a report.
# It should be run on a Linux system with the daemon installed and running.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPORT_DIR="performance-reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="${REPORT_DIR}/performance_${TIMESTAMP}.txt"

echo -e "${BLUE}=== Derpy Daemon Performance Testing ===${NC}"
echo ""

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo -e "${RED}Error: Performance tests require Linux${NC}"
    exit 1
fi

# Check if daemon is running
if ! pgrep -f derpyd > /dev/null; then
    echo -e "${RED}Error: Daemon is not running${NC}"
    echo "Start the daemon with: sudo systemctl start derpyd"
    exit 1
fi

echo -e "${GREEN}✓ Daemon is running${NC}"
echo ""

# Create report directory
mkdir -p "$REPORT_DIR"

# Start report
{
    echo "Derpy Daemon Performance Report"
    echo "================================"
    echo ""
    echo "Date: $(date)"
    echo "Hostname: $(hostname)"
    echo "Kernel: $(uname -r)"
    echo "CPU: $(lscpu | grep 'Model name' | cut -d: -f2 | xargs)"
    echo "CPU Cores: $(nproc)"
    echo "Memory: $(free -h | grep Mem | awk '{print $2}')"
    echo ""
    echo "Daemon Status:"
    systemctl status derpyd --no-pager | head -n 10
    echo ""
    echo "================================"
    echo ""
} > "$REPORT_FILE"

# Function to run test and capture output
run_test() {
    local test_name=$1
    local test_path=$2
    
    echo -e "${YELLOW}Running: $test_name${NC}"
    
    {
        echo "Test: $test_name"
        echo "---"
        echo ""
    } >> "$REPORT_FILE"
    
    if pytest "$test_path" -v --tb=short 2>&1 | tee -a "$REPORT_FILE"; then
        echo -e "${GREEN}✓ $test_name passed${NC}"
    else
        echo -e "${RED}✗ $test_name failed${NC}"
    fi
    
    {
        echo ""
        echo "---"
        echo ""
    } >> "$REPORT_FILE"
    
    echo ""
}

# Run performance tests
echo -e "${BLUE}Running performance tests...${NC}"
echo ""

run_test "Daemon Overhead Test" \
    "tests/test_daemon_performance.py::TestDaemonPerformance::test_daemon_overhead_vs_direct_execution"

run_test "Concurrent Client Stress Test" \
    "tests/test_daemon_performance.py::TestDaemonPerformance::test_concurrent_client_stress"

run_test "Large Build Context Test" \
    "tests/test_daemon_performance.py::TestDaemonPerformance::test_large_build_context_performance"

run_test "Many Layers Test" \
    "tests/test_daemon_performance.py::TestDaemonPerformance::test_many_layers_performance"

run_test "Concurrent Builds Test" \
    "tests/test_daemon_performance.py::TestDaemonPerformance::test_concurrent_builds_performance"

run_test "Memory Usage Test" \
    "tests/test_daemon_performance.py::TestDaemonResourceUsage::test_daemon_memory_usage"

# Collect daemon statistics
echo -e "${BLUE}Collecting daemon statistics...${NC}"

{
    echo "Daemon Statistics"
    echo "================="
    echo ""
    
    # Get daemon PID
    DAEMON_PID=$(pgrep -f derpyd | head -n 1)
    
    if [ -n "$DAEMON_PID" ]; then
        echo "Daemon PID: $DAEMON_PID"
        echo ""
        
        # Memory usage
        echo "Memory Usage:"
        ps -p "$DAEMON_PID" -o pid,vsz,rss,pmem,comm --no-headers
        echo ""
        
        # CPU usage
        echo "CPU Usage:"
        ps -p "$DAEMON_PID" -o pid,pcpu,time,comm --no-headers
        echo ""
        
        # File descriptors
        echo "Open File Descriptors:"
        ls -1 /proc/"$DAEMON_PID"/fd 2>/dev/null | wc -l
        echo ""
        
        # Socket connections
        echo "Socket Connections:"
        ss -x | grep derpy.sock | wc -l
        echo ""
    else
        echo "Could not find daemon process"
        echo ""
    fi
    
    # Recent logs
    echo "Recent Daemon Logs (last 50 lines):"
    echo "---"
    journalctl -u derpyd -n 50 --no-pager
    echo ""
    
} >> "$REPORT_FILE"

echo -e "${GREEN}✓ Statistics collected${NC}"
echo ""

# Generate summary
echo -e "${BLUE}Generating summary...${NC}"

{
    echo "Summary"
    echo "======="
    echo ""
    echo "All performance tests completed."
    echo "See detailed results above."
    echo ""
    echo "Key Findings:"
    echo "- Daemon overhead: Check 'Daemon Overhead Test' section"
    echo "- Concurrent performance: Check 'Concurrent Client Stress Test' section"
    echo "- Resource usage: Check 'Memory Usage Test' and 'Daemon Statistics' sections"
    echo ""
    echo "For performance tuning recommendations, see docs/performance.md"
    echo ""
} >> "$REPORT_FILE"

# Display report location
echo -e "${GREEN}=== Performance Testing Complete ===${NC}"
echo ""
echo "Report saved to: $REPORT_FILE"
echo ""
echo "View report with: cat $REPORT_FILE"
echo "Or: less $REPORT_FILE"
echo ""

# Optionally display summary
if command -v tail &> /dev/null; then
    echo -e "${BLUE}Report Summary:${NC}"
    echo ""
    tail -n 20 "$REPORT_FILE"
fi
