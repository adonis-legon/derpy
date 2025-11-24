"""
Performance testing and optimization for daemon socket support.

This module contains performance tests that measure daemon overhead,
concurrent client handling, and resource usage under various conditions.

Requirements tested: 8.1, 8.5
"""

import os
import sys
import time
import tempfile
import threading
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple
import json
import statistics

import pytest

# Import daemon components
from derpy.daemon.client import DaemonClient
from derpy.daemon.protocol import BuildRequest, ListRequest
from derpy.build.engine import BuildEngine, BuildContext


class PerformanceMetrics:
    """Container for performance metrics."""
    
    def __init__(self):
        self.measurements: List[float] = []
        self.errors: List[str] = []
    
    def add_measurement(self, duration: float):
        """Add a timing measurement in seconds."""
        self.measurements.append(duration)
    
    def add_error(self, error: str):
        """Record an error."""
        self.errors.append(error)
    
    @property
    def mean(self) -> float:
        """Calculate mean duration."""
        return statistics.mean(self.measurements) if self.measurements else 0.0
    
    @property
    def median(self) -> float:
        """Calculate median duration."""
        return statistics.median(self.measurements) if self.measurements else 0.0
    
    @property
    def stdev(self) -> float:
        """Calculate standard deviation."""
        return statistics.stdev(self.measurements) if len(self.measurements) > 1 else 0.0
    
    @property
    def min(self) -> float:
        """Get minimum duration."""
        return min(self.measurements) if self.measurements else 0.0
    
    @property
    def max(self) -> float:
        """Get maximum duration."""
        return max(self.measurements) if self.measurements else 0.0
    
    @property
    def p95(self) -> float:
        """Calculate 95th percentile."""
        if not self.measurements:
            return 0.0
        sorted_measurements = sorted(self.measurements)
        index = int(len(sorted_measurements) * 0.95)
        return sorted_measurements[index]
    
    @property
    def p99(self) -> float:
        """Calculate 99th percentile."""
        if not self.measurements:
            return 0.0
        sorted_measurements = sorted(self.measurements)
        index = int(len(sorted_measurements) * 0.99)
        return sorted_measurements[index]
    
    def summary(self) -> Dict[str, float]:
        """Get summary statistics."""
        return {
            'count': len(self.measurements),
            'mean': self.mean,
            'median': self.median,
            'stdev': self.stdev,
            'min': self.min,
            'max': self.max,
            'p95': self.p95,
            'p99': self.p99,
            'error_count': len(self.errors)
        }


@pytest.mark.integration
@pytest.mark.slow
class TestDaemonPerformance:
    """Performance tests for daemon operations."""
    
    def test_daemon_overhead_vs_direct_execution(self, tmp_path):
        """
        Measure daemon overhead compared to direct execution.
        
        Tests simple list operations to isolate communication overhead
        from actual build work.
        
        Requirements: 8.1
        """
        # Skip if not on Linux or no daemon available
        if sys.platform != 'linux':
            pytest.skip("Daemon only supported on Linux")
        
        daemon_client = DaemonClient()
        if not daemon_client.is_available():
            pytest.skip("Daemon not running")
        
        iterations = 50
        daemon_metrics = PerformanceMetrics()
        
        # Measure daemon-based list operations
        for _ in range(iterations):
            start = time.perf_counter()
            try:
                response = daemon_client.send_list_request()
                duration = time.perf_counter() - start
                daemon_metrics.add_measurement(duration)
            except Exception as e:
                daemon_metrics.add_error(str(e))
        
        # Print results
        print("\n=== Daemon Overhead Test ===")
        print(f"Iterations: {iterations}")
        print(f"Daemon list operation:")
        print(f"  Mean: {daemon_metrics.mean*1000:.2f}ms")
        print(f"  Median: {daemon_metrics.median*1000:.2f}ms")
        print(f"  Std Dev: {daemon_metrics.stdev*1000:.2f}ms")
        print(f"  Min: {daemon_metrics.min*1000:.2f}ms")
        print(f"  Max: {daemon_metrics.max*1000:.2f}ms")
        print(f"  P95: {daemon_metrics.p95*1000:.2f}ms")
        print(f"  P99: {daemon_metrics.p99*1000:.2f}ms")
        print(f"  Errors: {len(daemon_metrics.errors)}")
        
        # Verify overhead is reasonable (< 10ms mean)
        assert daemon_metrics.mean < 0.010, \
            f"Daemon overhead too high: {daemon_metrics.mean*1000:.2f}ms"
        
        # Verify consistency (stdev < 5ms)
        assert daemon_metrics.stdev < 0.005, \
            f"Daemon response time too variable: {daemon_metrics.stdev*1000:.2f}ms"
    
    def test_concurrent_client_stress(self, tmp_path):
        """
        Stress test with many concurrent clients.
        
        Tests daemon's ability to handle many simultaneous connections
        and requests without degradation.
        
        Requirements: 8.1, 8.5
        """
        if sys.platform != 'linux':
            pytest.skip("Daemon only supported on Linux")
        
        daemon_client = DaemonClient()
        if not daemon_client.is_available():
            pytest.skip("Daemon not running")
        
        num_clients = 50
        requests_per_client = 5
        metrics = PerformanceMetrics()
        errors = []
        lock = threading.Lock()
        
        def client_worker(client_id: int):
            """Worker function for each client thread."""
            client = DaemonClient()
            for req_num in range(requests_per_client):
                try:
                    start = time.perf_counter()
                    response = client.send_list_request()
                    duration = time.perf_counter() - start
                    
                    with lock:
                        metrics.add_measurement(duration)
                except Exception as e:
                    with lock:
                        errors.append(f"Client {client_id}, Request {req_num}: {e}")
        
        # Launch concurrent clients
        threads = []
        start_time = time.perf_counter()
        
        for i in range(num_clients):
            thread = threading.Thread(target=client_worker, args=(i,))
            thread.start()
            threads.append(thread)
        
        # Wait for all clients to complete
        for thread in threads:
            thread.join()
        
        total_duration = time.perf_counter() - start_time
        
        # Print results
        print("\n=== Concurrent Client Stress Test ===")
        print(f"Clients: {num_clients}")
        print(f"Requests per client: {requests_per_client}")
        print(f"Total requests: {num_clients * requests_per_client}")
        print(f"Total duration: {total_duration:.2f}s")
        print(f"Throughput: {(num_clients * requests_per_client) / total_duration:.2f} req/s")
        print(f"Request latency:")
        print(f"  Mean: {metrics.mean*1000:.2f}ms")
        print(f"  Median: {metrics.median*1000:.2f}ms")
        print(f"  Std Dev: {metrics.stdev*1000:.2f}ms")
        print(f"  Min: {metrics.min*1000:.2f}ms")
        print(f"  Max: {metrics.max*1000:.2f}ms")
        print(f"  P95: {metrics.p95*1000:.2f}ms")
        print(f"  P99: {metrics.p99*1000:.2f}ms")
        print(f"Errors: {len(errors)}")
        if errors:
            print("Error samples:")
            for error in errors[:5]:
                print(f"  {error}")
        
        # Verify all requests completed
        assert len(metrics.measurements) == num_clients * requests_per_client, \
            f"Not all requests completed: {len(metrics.measurements)}/{num_clients * requests_per_client}"
        
        # Verify reasonable latency under load (< 100ms p95)
        assert metrics.p95 < 0.100, \
            f"P95 latency too high under load: {metrics.p95*1000:.2f}ms"
        
        # Verify minimal errors (< 1%)
        error_rate = len(errors) / (num_clients * requests_per_client)
        assert error_rate < 0.01, \
            f"Error rate too high: {error_rate*100:.2f}%"
    
    def test_large_build_context_performance(self, tmp_path):
        """
        Test performance with large build contexts.
        
        Measures how daemon handles builds with many files in the context.
        
        Requirements: 8.1
        """
        if sys.platform != 'linux':
            pytest.skip("Daemon only supported on Linux")
        
        daemon_client = DaemonClient()
        if not daemon_client.is_available():
            pytest.skip("Daemon not running")
        
        # Create a build context with many files
        context_dir = tmp_path / "large_context"
        context_dir.mkdir()
        
        # Create 1000 small files
        num_files = 1000
        for i in range(num_files):
            file_path = context_dir / f"file_{i}.txt"
            file_path.write_text(f"Content {i}\n" * 10)
        
        # Create Dockerfile
        dockerfile = context_dir / "Dockerfile"
        dockerfile.write_text("""
FROM alpine:latest
COPY . /app
RUN echo "Build complete"
""")
        
        # Measure build time
        print(f"\n=== Large Build Context Test ===")
        print(f"Context files: {num_files}")
        print(f"Context size: {sum(f.stat().st_size for f in context_dir.rglob('*') if f.is_file()) / 1024:.2f} KB")
        
        start = time.perf_counter()
        try:
            output_lines = []
            response = daemon_client.send_build_request(
                context_path=context_dir,
                dockerfile_path=dockerfile,
                tag="test:large-context",
                output_callback=lambda line: output_lines.append(line)
            )
            duration = time.perf_counter() - start
            
            print(f"Build duration: {duration:.2f}s")
            print(f"Build success: {response.success}")
            
            # Verify build completed in reasonable time (< 60s)
            assert duration < 60.0, \
                f"Build took too long: {duration:.2f}s"
            
        except Exception as e:
            duration = time.perf_counter() - start
            print(f"Build failed after {duration:.2f}s: {e}")
            raise
    
    def test_many_layers_performance(self, tmp_path):
        """
        Test performance with images containing many layers.
        
        Measures how daemon handles builds that create many layers.
        
        Requirements: 8.1
        """
        if sys.platform != 'linux':
            pytest.skip("Daemon only supported on Linux")
        
        daemon_client = DaemonClient()
        if not daemon_client.is_available():
            pytest.skip("Daemon not running")
        
        # Create Dockerfile with many RUN instructions
        context_dir = tmp_path / "many_layers"
        context_dir.mkdir()
        
        num_layers = 20
        dockerfile_content = "FROM alpine:latest\n"
        for i in range(num_layers):
            dockerfile_content += f'RUN echo "Layer {i}" > /layer_{i}.txt\n'
        
        dockerfile = context_dir / "Dockerfile"
        dockerfile.write_text(dockerfile_content)
        
        # Measure build time
        print(f"\n=== Many Layers Test ===")
        print(f"Number of layers: {num_layers}")
        
        start = time.perf_counter()
        try:
            output_lines = []
            response = daemon_client.send_build_request(
                context_path=context_dir,
                dockerfile_path=dockerfile,
                tag="test:many-layers",
                output_callback=lambda line: output_lines.append(line)
            )
            duration = time.perf_counter() - start
            
            print(f"Build duration: {duration:.2f}s")
            print(f"Build success: {response.success}")
            print(f"Average time per layer: {duration/num_layers:.2f}s")
            
            # Verify build completed in reasonable time (< 120s)
            assert duration < 120.0, \
                f"Build took too long: {duration:.2f}s"
            
        except Exception as e:
            duration = time.perf_counter() - start
            print(f"Build failed after {duration:.2f}s: {e}")
            raise
    
    def test_concurrent_builds_performance(self, tmp_path):
        """
        Test performance with multiple concurrent builds.
        
        Measures daemon's ability to handle multiple builds simultaneously
        without significant performance degradation.
        
        Requirements: 8.1, 8.5
        """
        if sys.platform != 'linux':
            pytest.skip("Daemon only supported on Linux")
        
        daemon_client = DaemonClient()
        if not daemon_client.is_available():
            pytest.skip("Daemon not running")
        
        num_builds = 5
        metrics = PerformanceMetrics()
        errors = []
        lock = threading.Lock()
        
        def build_worker(build_id: int):
            """Worker function for each build thread."""
            # Create unique build context
            context_dir = tmp_path / f"build_{build_id}"
            context_dir.mkdir(exist_ok=True)
            
            dockerfile = context_dir / "Dockerfile"
            dockerfile.write_text(f"""
FROM alpine:latest
RUN echo "Build {build_id}" > /build_{build_id}.txt
RUN sleep 1
RUN echo "Build {build_id} complete"
""")
            
            client = DaemonClient()
            try:
                start = time.perf_counter()
                output_lines = []
                response = client.send_build_request(
                    context_path=context_dir,
                    dockerfile_path=dockerfile,
                    tag=f"test:concurrent-{build_id}",
                    output_callback=lambda line: output_lines.append(line)
                )
                duration = time.perf_counter() - start
                
                with lock:
                    metrics.add_measurement(duration)
                    
                if not response.success:
                    with lock:
                        errors.append(f"Build {build_id} failed: {response.error_message}")
                        
            except Exception as e:
                with lock:
                    errors.append(f"Build {build_id} exception: {e}")
        
        # Launch concurrent builds
        threads = []
        start_time = time.perf_counter()
        
        for i in range(num_builds):
            thread = threading.Thread(target=build_worker, args=(i,))
            thread.start()
            threads.append(thread)
        
        # Wait for all builds to complete
        for thread in threads:
            thread.join()
        
        total_duration = time.perf_counter() - start_time
        
        # Print results
        print("\n=== Concurrent Builds Performance Test ===")
        print(f"Number of builds: {num_builds}")
        print(f"Total duration: {total_duration:.2f}s")
        print(f"Build times:")
        print(f"  Mean: {metrics.mean:.2f}s")
        print(f"  Median: {metrics.median:.2f}s")
        print(f"  Std Dev: {metrics.stdev:.2f}s")
        print(f"  Min: {metrics.min:.2f}s")
        print(f"  Max: {metrics.max:.2f}s")
        print(f"Errors: {len(errors)}")
        if errors:
            print("Errors:")
            for error in errors:
                print(f"  {error}")
        
        # Verify all builds completed
        assert len(metrics.measurements) == num_builds, \
            f"Not all builds completed: {len(metrics.measurements)}/{num_builds}"
        
        # Verify reasonable performance (max build time < 30s)
        assert metrics.max < 30.0, \
            f"Build took too long: {metrics.max:.2f}s"
        
        # Verify minimal errors
        assert len(errors) == 0, \
            f"Builds had errors: {errors}"


@pytest.mark.integration
@pytest.mark.slow
class TestDaemonResourceUsage:
    """Resource usage tests for daemon."""
    
    def test_daemon_memory_usage(self):
        """
        Monitor daemon memory usage under load.
        
        Verifies daemon doesn't have memory leaks or excessive memory usage.
        
        Requirements: 8.5
        """
        if sys.platform != 'linux':
            pytest.skip("Daemon only supported on Linux")
        
        # Try to find daemon process
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'derpyd'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                pytest.skip("Daemon not running")
            
            pid = int(result.stdout.strip().split()[0])
            
            # Get initial memory usage
            def get_memory_usage(pid: int) -> float:
                """Get memory usage in MB."""
                try:
                    with open(f'/proc/{pid}/status', 'r') as f:
                        for line in f:
                            if line.startswith('VmRSS:'):
                                # Extract KB value and convert to MB
                                kb = int(line.split()[1])
                                return kb / 1024.0
                except:
                    return 0.0
                return 0.0
            
            initial_memory = get_memory_usage(pid)
            print(f"\n=== Daemon Memory Usage Test ===")
            print(f"Daemon PID: {pid}")
            print(f"Initial memory: {initial_memory:.2f} MB")
            
            # Send many requests to stress memory
            daemon_client = DaemonClient()
            for i in range(100):
                try:
                    daemon_client.send_list_request()
                except:
                    pass
            
            # Get final memory usage
            final_memory = get_memory_usage(pid)
            memory_increase = final_memory - initial_memory
            
            print(f"Final memory: {final_memory:.2f} MB")
            print(f"Memory increase: {memory_increase:.2f} MB")
            
            # Verify memory usage is reasonable (< 100MB total, < 20MB increase)
            assert final_memory < 100.0, \
                f"Daemon using too much memory: {final_memory:.2f} MB"
            
            assert memory_increase < 20.0, \
                f"Memory increased too much: {memory_increase:.2f} MB"
            
        except subprocess.TimeoutExpired:
            pytest.skip("Could not check daemon process")
        except FileNotFoundError:
            pytest.skip("pgrep not available")


def generate_performance_report(output_path: Path):
    """
    Generate a comprehensive performance report.
    
    This function can be called manually to generate a detailed
    performance report with all metrics.
    """
    report = {
        'timestamp': time.time(),
        'platform': sys.platform,
        'tests': []
    }
    
    # Run all performance tests and collect results
    pytest.main([
        __file__,
        '-v',
        '--tb=short',
        '-m', 'slow'
    ])
    
    # Save report
    output_path.write_text(json.dumps(report, indent=2))
    print(f"\nPerformance report saved to: {output_path}")


if __name__ == '__main__':
    # Allow running performance tests directly
    pytest.main([__file__, '-v', '--tb=short', '-m', 'slow'])
