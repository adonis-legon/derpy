# Performance Testing Quick Start

Quick reference for running performance tests and interpreting results.

## Prerequisites

- Linux system
- Daemon running: `sudo systemctl start derpyd`
- Python 3.10+ with pytest

## Run Tests

### Quick Test

```bash
# Run all performance tests
pytest tests/test_daemon_performance.py -v -m slow
```

### Comprehensive Test with Report

```bash
# Run full test suite with detailed report
./scripts/performance-test.sh

# View report
cat performance-reports/performance_*.txt
```

### Individual Tests

```bash
# Test daemon overhead (fastest)
pytest tests/test_daemon_performance.py::TestDaemonPerformance::test_daemon_overhead_vs_direct_execution -v

# Test concurrent clients
pytest tests/test_daemon_performance.py::TestDaemonPerformance::test_concurrent_client_stress -v

# Test large contexts
pytest tests/test_daemon_performance.py::TestDaemonPerformance::test_large_build_context_performance -v

# Test many layers
pytest tests/test_daemon_performance.py::TestDaemonPerformance::test_many_layers_performance -v

# Test concurrent builds
pytest tests/test_daemon_performance.py::TestDaemonPerformance::test_concurrent_builds_performance -v

# Test memory usage
pytest tests/test_daemon_performance.py::TestDaemonResourceUsage::test_daemon_memory_usage -v
```

## Profile Code

```bash
# Profile all components
python scripts/profile-daemon.py

# Profile specific component
python scripts/profile-daemon.py --component serialization

# Generate optimization report
python scripts/profile-daemon.py --output optimization-report.txt
```

## Expected Results

### Daemon Overhead

- ✅ Mean latency: < 10ms
- ✅ Std deviation: < 5ms
- ❌ If > 10ms: Check system load

### Concurrent Clients (50 clients)

- ✅ P95 latency: < 100ms
- ✅ Error rate: < 1%
- ✅ Throughput: > 200 req/s
- ❌ If P95 > 100ms: Increase max_workers

### Large Context (1,000 files)

- ✅ Build time: < 60s
- ❌ If > 60s: Use .dockerignore, optimize Dockerfile

### Many Layers (20 layers)

- ✅ Build time: < 120s
- ❌ If > 120s: Combine RUN commands

### Concurrent Builds (5 builds)

- ✅ Max build time: < 30s
- ✅ No errors
- ❌ If errors: Check resource limits

### Memory Usage

- ✅ Base: 20-30 MB
- ✅ Under load: < 100 MB
- ✅ Increase: < 20 MB
- ❌ If > 100 MB: Restart daemon, check for leaks

## Quick Troubleshooting

### High Latency

```bash
# Check system load
uptime

# Check daemon status
systemctl status derpyd

# Restart daemon
sudo systemctl restart derpyd
```

### Build Slowness

```bash
# Check disk I/O
iostat -x 1 5

# Check context size
du -sh /path/to/context

# Optimize Dockerfile
# - Combine RUN commands
# - Use .dockerignore
# - Order from least to most changing
```

### Memory Issues

```bash
# Check daemon memory
ps aux | grep derpyd

# Restart daemon
sudo systemctl restart derpyd

# Reduce max workers
derpyd --max-workers 2
```

## Performance Tuning

### Increase Concurrency (8+ cores)

```bash
derpyd --max-workers 8
```

### Reduce Memory Usage (< 4GB RAM)

```bash
derpyd --max-workers 2
```

### Default (4 cores, 8GB RAM)

```bash
derpyd --max-workers 4  # default
```

## Monitoring

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

## Documentation

- **Full guide:** [docs/performance-testing.md](performance-testing.md)
- **Performance characteristics:** [docs/performance.md](performance.md)
- **Summary:** [docs/PERFORMANCE-TESTING-SUMMARY.md](PERFORMANCE-TESTING-SUMMARY.md)

## Common Issues

| Issue             | Symptom              | Solution                               |
| ----------------- | -------------------- | -------------------------------------- |
| High latency      | Requests > 100ms     | Increase max_workers or reduce load    |
| Build slowness    | Builds > 2x baseline | Optimize Dockerfile, use SSD           |
| Memory growth     | Daemon > 200MB       | Restart daemon, check for leaks        |
| Errors under load | Error rate > 1%      | Increase file descriptors, reduce load |

## Success Criteria

All tests should pass with:

- ✅ No test failures
- ✅ All metrics within expected ranges
- ✅ No errors in daemon logs
- ✅ Memory usage stable

If any test fails, see [docs/performance-testing.md](performance-testing.md) for detailed troubleshooting.
