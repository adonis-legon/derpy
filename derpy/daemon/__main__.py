"""
Daemon entry point for derpyd.

This module provides the main entry point for the derpy daemon service.
The daemon runs with elevated privileges and handles build operations via
Unix domain socket communication.
"""

import sys
import argparse
import logging
import signal
import threading
from pathlib import Path

from derpy.daemon import __version__
from derpy.daemon.server import DaemonServer, DaemonError


def setup_logging(log_level: str) -> None:
    """Configure logging for the daemon.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Convert string to logging level
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Set specific logger levels
    logger = logging.getLogger('derpy.daemon')
    logger.setLevel(numeric_level)


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        prog='derpyd',
        description='Derpy daemon for privileged container operations',
        epilog='For more information, visit: https://github.com/adonis-legon/derpy'
    )
    
    # Version flag
    parser.add_argument(
        '--version',
        action='version',
        version=f'derpyd {__version__}'
    )
    
    # Socket path
    parser.add_argument(
        '--socket',
        type=Path,
        default=Path('/var/run/derpy.sock'),
        metavar='PATH',
        help='Path to Unix domain socket (default: /var/run/derpy.sock)'
    )
    
    # Group name
    parser.add_argument(
        '--group',
        type=str,
        default='derpy',
        metavar='NAME',
        help='System group name for access control (default: derpy)'
    )
    
    # Max workers
    parser.add_argument(
        '--max-workers',
        type=int,
        default=4,
        metavar='N',
        help='Maximum concurrent build operations (default: 4)'
    )
    
    # Log level
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Logging level (default: INFO)'
    )
    
    return parser.parse_args()


def main() -> int:
    """Main entry point for derpyd daemon.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Parse command-line arguments
        args = parse_arguments()
        
        # Setup logging
        setup_logging(args.log_level)
        logger = logging.getLogger('derpy.daemon')
        
        logger.info(f"Starting derpyd version {__version__}")
        logger.info(f"Socket path: {args.socket}")
        logger.info(f"Group name: {args.group}")
        logger.info(f"Max workers: {args.max_workers}")
        logger.info(f"Log level: {args.log_level}")
        
        # Create and start daemon server
        server = DaemonServer(
            socket_path=args.socket,
            group_name=args.group,
            max_workers=args.max_workers
        )
        
        # Start the server (this blocks until shutdown)
        server.start()
        
        # Keep the main thread alive
        # The server runs in background threads, so we need to wait
        try:
            # Wait for shutdown signal
            shutdown_event = threading.Event()
            
            def signal_handler(signum, frame):
                logger.info(f"Received signal {signum}, shutting down")
                shutdown_event.set()
            
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
            
            # Wait for shutdown
            shutdown_event.wait()
            
            # Stop the server
            server.stop()
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down")
            server.stop()
        
        logger.info("Daemon stopped successfully")
        return 0
        
    except DaemonError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        logging.exception("Unexpected error in daemon")
        return 1


if __name__ == "__main__":
    sys.exit(main())
