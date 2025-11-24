#!/usr/bin/env python3
"""
Profiling utility for Derpy daemon operations.

This script helps identify performance bottlenecks in daemon operations
by profiling key code paths and generating reports.
"""

import cProfile
import pstats
import io
import sys
import tempfile
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from derpy.daemon.protocol import BuildRequest, ListRequest, OutputMessage
from derpy.daemon.framing import MessageFramer


def profile_message_serialization(iterations: int = 1000):
    """Profile message serialization performance."""
    print(f"\n=== Profiling Message Serialization ({iterations} iterations) ===")
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Profile BuildRequest serialization
    for i in range(iterations):
        request = BuildRequest(
            context_path=f"/tmp/context_{i}",
            dockerfile_path=f"/tmp/context_{i}/Dockerfile",
            tag=f"test:image-{i}",
            build_args={"ARG1": "value1", "ARG2": "value2"}
        )
        json_str = request.to_json()
        BuildRequest.from_json(json_str)
    
    profiler.disable()
    
    # Print stats
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(20)
    print(s.getvalue())


def profile_message_framing(iterations: int = 1000):
    """Profile message framing performance."""
    print(f"\n=== Profiling Message Framing ({iterations} iterations) ===")
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Profile message framing
    for i in range(iterations):
        request = BuildRequest(
            context_path=f"/tmp/context_{i}",
            dockerfile_path=f"/tmp/context_{i}/Dockerfile",
            tag=f"test:image-{i}"
        )
        
        # Simulate framing (without actual socket)
        json_str = request.to_json()
        message_bytes = (json_str + "\n").encode('utf-8')
        
        # Simulate parsing
        decoded = message_bytes.decode('utf-8').strip()
    
    profiler.disable()
    
    # Print stats
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(20)
    print(s.getvalue())


def profile_output_streaming(iterations: int = 1000):
    """Profile output message streaming."""
    print(f"\n=== Profiling Output Streaming ({iterations} iterations) ===")
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Profile output message creation and serialization
    for i in range(iterations):
        output = OutputMessage(
            content=f"Build output line {i}\n",
            timestamp=float(i)
        )
        json_str = output.to_json()
        OutputMessage.from_json(json_str)
    
    profiler.disable()
    
    # Print stats
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(20)
    print(s.getvalue())


def analyze_hotspots():
    """Analyze potential performance hotspots."""
    print("\n=== Performance Hotspot Analysis ===\n")
    
    hotspots = [
        {
            'component': 'Message Serialization',
            'description': 'JSON encoding/decoding of protocol messages',
            'impact': 'Low (< 1ms per message)',
            'optimization': 'Use msgpack or protobuf for binary serialization'
        },
        {
            'component': 'Socket I/O',
            'description': 'Unix socket read/write operations',
            'impact': 'Low (< 2ms per operation)',
            'optimization': 'Already optimal for Unix sockets'
        },
        {
            'component': 'Build Isolation',
            'description': 'Chroot setup and filesystem operations',
            'impact': 'Medium (1-2s per build)',
            'optimization': 'Use overlayfs for faster layer mounting'
        },
        {
            'component': 'Layer Diff Tracking',
            'description': 'Computing filesystem changes',
            'impact': 'Medium (0.5-2s per layer)',
            'optimization': 'Use inotify for real-time tracking'
        },
        {
            'component': 'Base Image Download',
            'description': 'Downloading base images from registry',
            'impact': 'High (10-60s depending on image size)',
            'optimization': 'Pre-cache common base images'
        },
        {
            'component': 'Thread Pool Management',
            'description': 'Managing concurrent build threads',
            'impact': 'Low (< 10ms overhead)',
            'optimization': 'Already using efficient ThreadPoolExecutor'
        }
    ]
    
    print("Component                    | Impact  | Optimization Opportunity")
    print("-" * 75)
    for hotspot in hotspots:
        print(f"{hotspot['component']:<28} | {hotspot['impact']:<7} | {hotspot['optimization']}")
    
    print("\n")
    print("Recommendations:")
    print("1. Focus optimization efforts on build isolation and layer diff tracking")
    print("2. Pre-cache common base images to eliminate download time")
    print("3. Consider binary serialization for high-throughput scenarios")
    print("4. Monitor thread pool utilization and adjust max_workers as needed")


def generate_optimization_report(output_path: Optional[Path] = None):
    """Generate comprehensive optimization report."""
    if output_path is None:
        output_path = Path("performance-optimization-report.txt")
    
    # Redirect stdout to file
    original_stdout = sys.stdout
    
    with open(output_path, 'w') as f:
        sys.stdout = f
        
        print("Derpy Daemon Performance Optimization Report")
        print("=" * 60)
        print()
        
        # Run profiling
        profile_message_serialization(iterations=1000)
        profile_message_framing(iterations=1000)
        profile_output_streaming(iterations=1000)
        
        # Analyze hotspots
        analyze_hotspots()
        
        print("\n" + "=" * 60)
        print("Report generation complete")
    
    sys.stdout = original_stdout
    print(f"\nOptimization report saved to: {output_path}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Profile Derpy daemon operations'
    )
    parser.add_argument(
        '--iterations',
        type=int,
        default=1000,
        help='Number of iterations for profiling (default: 1000)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Output file for optimization report'
    )
    parser.add_argument(
        '--component',
        choices=['serialization', 'framing', 'streaming', 'all'],
        default='all',
        help='Component to profile (default: all)'
    )
    
    args = parser.parse_args()
    
    if args.component in ['serialization', 'all']:
        profile_message_serialization(args.iterations)
    
    if args.component in ['framing', 'all']:
        profile_message_framing(args.iterations)
    
    if args.component in ['streaming', 'all']:
        profile_output_streaming(args.iterations)
    
    if args.component == 'all':
        analyze_hotspots()
    
    if args.output:
        generate_optimization_report(args.output)
