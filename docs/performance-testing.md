# Performance Testing Guide

This guide explains how to run performance tests, interpret results, and optimize the Derpy daemon for your environment.

## Overview

The Derpy daemon performance testing suite includes:

1. **Automated Performance Tests** - Pytest-based tests that measure key metrics
2. **Performance Testing Script** - Comprehensive test runner with reporting
3. **Profiling Utility** - Code profiling to identify bottlenecks
4. **Performance Documentation** - Detailed performance characteristics

## Running Performance Tests

### Prerequisites

- Linux system (daemon only runs on Linux)
- Derpy daemon installed and running
- Python 3.10+ with pytest installed
- Root access (for daemon management)

### Quick Start

```bash
# Ensure daemon is running
sudo systemctl start derpyd
sudo systemctl status derpyd

# Run all performance tests
pytest tests/test_daemon_performance.py -v -m slow

# Run comprehensive performance test suite with report
./scripts/performance-test.sh
```

### Individual Tests

Run specific performance tests:

```bash
# Test daemon overhead
pytest tests/test_daemon_performance.py::TestDaemonPerformance::test_daemon_overhead_vs_direct_execution -v

# Test concurrent clients
pytest tests/test_daemon_performance.py::TestDaemonPerformance::test_concurrent_client_stress -v

# Test large build contexts
pytest tests/test_daemon_performance.py::TestDaemonPerformance::test_large_build_context_performance -v

# Test many layers
pytest tests/test_daemon_performance.py::TestDaemonPerformance::test_many_layers_performance -v

# Test concurrent builds
pytest tests/test_daemon_performance.py::TestDaemonPerformance::test_concurrent_builds_performance -v

# Test memory usage
pytest tests/test_daemon_performance.py::TestDaemonResourceUsage::test_daemon_memory_usage -v
```

## Test Descriptions

### 1. Daemon Overhead Test

**Purpose:** Measure communication overhead of daemon vs direct execution

**What it tests:**

- Socket connection latency
- Request serialization overhead
- Response deserialization overhead

**Expected results:**

- Mean latency: < 10ms
- Standard deviation: < 5ms
- Overhead: < 1% of total operation time

**Interpretation:**

- If mean > 10ms: Check system load, socket buffer sizes
- If stdev > 5ms: Check for competing processes, disk I/O issues

### 2. Concurrent Client Stress Test

**Purpose:** Test daemon's ability to handle many simultaneous clients

**What it tests:**

- Connection acceptance under load
- Request handling throughput
- Response latency under load
- Error rate under stress

**Expected results:**

- All requests complete successfully
- P95 latency: < 100ms
- Error rate: < 1%
- Throughput: > 200 req/s with 50 clients

**Interpretation:**

- If P95 > 100ms: Increase max_workers or reduce concurrent clients
- If error rate > 1%: Check system resources, increase file descriptor limits

### 3. Large Build Context Test

**Purpose:** Test performance with many files in build context

**What it tests:**

- Context processing time
- File copying performance
- Memory usage with large contexts

**Expected results:**

- 1,000 files: < 60 seconds
- No memory issues
- Build completes successfully

**Interpretation:**

- If time > 60s: Check disk I/O, use SSD, optimize Dockerfile
- If memory issues: Reduce context size, use .dockerignore

### 4. Many Layers Test

**Purpose:** Test performance with images containing many layers

**What it tests:**

- Layer creation overhead
- Diff tracking performance
- Cumulative layer overhead

**Expected results:**

- 20 layers: < 120 seconds
- Linear scaling with layer count
- ~1-2s overhead per layer

**Interpretation:**

- If time > 120s: Optimize Dockerfile, combine RUN commands
- If non-linear scaling: Check disk I/O, filesystem performance

### 5. Concurrent Builds Test

**Purpose:** Test multiple simultaneous builds

**What it tests:**

- Build isolation
- Resource coordination
- Output isolation
- Performance degradation under load

**Expected results:**

- All builds complete successfully
- Max build time: < 30s
- No output mixing
- No resource conflicts

**Interpretation:**

- If builds fail: Check resource limits, reduce max_workers
- If output mixed: Report as bug (should never happen)

### 6. Memory Usage Test

**Purpose:** Monitor daemon memory usage under load

**What it tests:**

- Base memory usage
- Memory growth under load
- Memory leak detection

**Expected results:**

- Base memory: 20-30 MB
- Under load: < 100 MB
- Memory increase: < 20 MB after 100 requests

**Interpretation:**

- If base > 50 MB: Investigate, may indicate issue
- If growth > 20 MB: Potential memory leak, restart daemon
- If total > 100 MB: Check for memory leaks, report as bug

## Profiling

### Running the Profiler

```bash
# Profile all components
python scripts/profile-daemon.py

# Profile specific component
python scripts/profile-daemon.py --component serialization
python scripts/profile-daemon.py --component framing
python scripts/profile-daemon.py --component streaming

# Generate optimization report
python scripts/profile-daemon.py --output optimization-report.txt

# Custom iteration count
python scripts/profile-daemon.py --iterations 10000
```

### Interpreting Profiling Results

The profiler shows:

- **cumulative time**: Total time spent in function and its callees
- **percall**: Average time per call
- **ncalls**: Number of times function was called

Focus on:

1. Functions with high cumulative time
2. Functions called many times with high percall
3. Unexpected function calls

### Common Bottlenecks

Based on profiling, common bottlenecks are:

1. **JSON serialization** (low impact, < 1ms)

   - Already optimized with Python's built-in json module
   - Consider msgpack for binary serialization if needed

2. **Socket I/O** (low impact, < 2ms)

   - Unix sockets are already optimal
   - No optimization needed

3. **Build isolation** (medium impact, 1-2s)

   - Chroot setup and teardown
   - Consider overlayfs for faster mounting

4. **Layer diff tracking** (medium impact, 0.5-2s)
   - Computing filesystem changes
   - Consider inotify for real-time tracking

## Performance Tuning

### Daemon Configuration

Adjust daemon settings based on your workload:

```bash
# For high-concurrency scenarios (8+ CPU cores)
derpyd --max-workers 8

# For memory-constrained systems (< 4GB RAM)
derpyd --max-workers 2

# For development (low load)
derpyd --max-workers 4  # default
```

### System Tuning

Optimize system settings for high-load scenarios:

```bash
# Increase file descriptor limits
sudo vim /etc/security/limits.conf
# Add:
# root soft nofile 4096
# root hard nofile 8192

# Increase socket buffer sizes (if needed)
sudo sysctl -w net.core.rmem_max=16777216
sudo sysctl -w net.core.wmem_max=16777216

# Make permanent
sudo vim /etc/sysctl.conf
# Add above settings
```

### Build Optimization

Optimize builds for better performance:

```dockerfile
# Combine RUN commands to reduce layers
RUN apt-get update && \
    apt-get install -y package1 package2 && \
    apt-get clean

# Order from least to most frequently changing
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

# Use .dockerignore to exclude unnecessary files
# .dockerignore:
# .git
# __pycache__
# *.pyc
# .pytest_cache
```

## Continuous Performance Monitoring

### Setting Up Monitoring

```bash
# Create cron job for daily performance tests
sudo crontab -e

# Add:
# 0 2 * * * /path/to/scripts/performance-test.sh >> /var/log/derpy-performance.log 2>&1
```

### Key Metrics to Track

Monitor these metrics over time:

1. **Request Latency**

   - Track P50, P95, P99
   - Alert if P95 > 100ms

2. **Build Duration**

   - Track average build time
   - Alert if > 2x baseline

3. **Memory Usage**

   - Track daemon RSS
   - Alert if > 200MB

4. **Error Rate**

   - Track failed requests
   - Alert if > 1%

5. **Throughput**
   - Track requests/second
   - Alert if < 100 req/s

### Monitoring Commands

```bash
# Check daemon memory
ps aux | grep derpyd | awk '{print $6/1024 " MB"}'

# Check socket connections
ss -x | grep derpy.sock | wc -l

# Check recent errors
journalctl -u derpyd --since "1 hour ago" | grep ERROR

# Check request rate
journalctl -u derpyd --since "1 hour ago" | grep "Request" | wc -l
```

## Troubleshooting Performance Issues

### Issue: High Latency

**Symptoms:**

- Requests taking > 100ms
- Slow response times

**Diagnosis:**

```bash
# Check system load
uptime
top

# Check daemon status
systemctl status derpyd

# Check for errors
journalctl -u derpyd -n 100
```

**Solutions:**

- Reduce max_workers if CPU saturated
- Increase max_workers if CPU idle
- Check for disk I/O bottlenecks
- Restart daemon if memory high

### Issue: Build Slowness

**Symptoms:**

- Builds taking longer than expected
- Builds slower than direct execution

**Diagnosis:**

```bash
# Profile a build
time derpy build . -f Dockerfile -t test:perf

# Check disk I/O
iostat -x 1 10

# Check for large contexts
du -sh /path/to/context
```

**Solutions:**

- Optimize Dockerfile (combine layers)
- Use .dockerignore
- Use SSD storage
- Pre-cache base images

### Issue: Memory Growth

**Symptoms:**

- Daemon memory increasing over time
- System running out of memory

**Diagnosis:**

```bash
# Monitor memory over time
watch -n 5 'ps aux | grep derpyd'

# Check for memory leaks
valgrind --leak-check=full derpyd
```

**Solutions:**

- Restart daemon periodically
- Report as bug if consistent growth
- Reduce max_workers
- Reduce concurrent builds

## Performance Regression Testing

### Setting Up Regression Tests

```bash
# Run baseline tests
./scripts/performance-test.sh
mv performance-reports/performance_*.txt baseline.txt

# After changes, run again
./scripts/performance-test.sh
mv performance-reports/performance_*.txt current.txt

# Compare results
diff baseline.txt current.txt
```

### Acceptable Regression Thresholds

- Latency: < 10% increase
- Throughput: < 10% decrease
- Memory: < 20% increase
- Build time: < 5% increase

## Best Practices

1. **Run tests on dedicated hardware** - Avoid running on shared systems
2. **Run multiple iterations** - Average results over 3-5 runs
3. **Control variables** - Keep system load consistent
4. **Document changes** - Track configuration changes
5. **Automate testing** - Run tests regularly in CI/CD
6. **Monitor production** - Track metrics in production environments
7. **Baseline early** - Establish baseline before optimization
8. **Optimize incrementally** - Make one change at a time

## References

- [Performance Documentation](performance.md) - Detailed performance characteristics
- [Daemon Documentation](daemon.md) - Daemon architecture and configuration
- [Troubleshooting Guide](troubleshooting.md) - Common issues and solutions

## Contributing Performance Improvements

If you identify performance improvements:

1. Run baseline tests
2. Make your changes
3. Run tests again
4. Document the improvement
5. Submit PR with before/after metrics

Include in your PR:

- Performance test results (before/after)
- Profiling data showing improvement
- Description of optimization
- Any trade-offs or limitations
