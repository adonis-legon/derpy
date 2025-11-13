"""Logging configuration for derpy.

This module provides centralized logging configuration with support for
different log levels, formats, and output destinations.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from derpy.core.platform import get_config_dir, ensure_directory


# Default log format
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
SIMPLE_FORMAT = "%(levelname)s: %(message)s"
DETAILED_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"


class DerpyLogger:
    """Centralized logger for derpy application."""
    
    _instance: Optional['DerpyLogger'] = None
    _initialized: bool = False
    
    def __new__(cls):
        """Singleton pattern to ensure only one logger instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the logger."""
        if not self._initialized:
            self.logger = logging.getLogger('derpy')
            self.logger.setLevel(logging.INFO)
            self._initialized = True
    
    def setup(
        self,
        level: int = logging.INFO,
        log_file: Optional[Path] = None,
        console: bool = True,
        format_string: str = SIMPLE_FORMAT
    ) -> None:
        """Setup logging configuration.
        
        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional path to log file
            console: Whether to log to console
            format_string: Log message format
        """
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Set level
        self.logger.setLevel(level)
        
        # Create formatter
        formatter = logging.Formatter(format_string)
        
        # Add console handler if requested
        if console:
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # Add file handler if requested
        if log_file:
            try:
                # Ensure log directory exists
                ensure_directory(log_file.parent)
                
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(level)
                file_handler.setFormatter(logging.Formatter(DETAILED_FORMAT))
                self.logger.addHandler(file_handler)
            except Exception as e:
                self.logger.warning(f"Failed to setup file logging: {e}")
    
    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """Get a logger instance.
        
        Args:
            name: Optional logger name (will be prefixed with 'derpy.')
        
        Returns:
            Logger instance
        """
        if name:
            return logging.getLogger(f'derpy.{name}')
        return self.logger
    
    def set_level(self, level: int) -> None:
        """Set logging level.
        
        Args:
            level: Logging level
        """
        self.logger.setLevel(level)
        for handler in self.logger.handlers:
            handler.setLevel(level)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Optional logger name
    
    Returns:
        Logger instance
    """
    derpy_logger = DerpyLogger()
    return derpy_logger.get_logger(name)


def setup_logging(
    verbose: bool = False,
    debug: bool = False,
    log_file: Optional[Path] = None,
    quiet: bool = False
) -> None:
    """Setup logging based on command-line flags.
    
    Args:
        verbose: Enable verbose output (INFO level)
        debug: Enable debug output (DEBUG level)
        log_file: Optional log file path
        quiet: Suppress console output
    """
    derpy_logger = DerpyLogger()
    
    # Determine log level
    if debug:
        level = logging.DEBUG
        format_string = DETAILED_FORMAT
    elif verbose:
        level = logging.INFO
        format_string = DEFAULT_FORMAT
    else:
        level = logging.WARNING
        format_string = SIMPLE_FORMAT
    
    # Setup logging
    derpy_logger.setup(
        level=level,
        log_file=log_file,
        console=not quiet,
        format_string=format_string
    )


def get_default_log_file() -> Path:
    """Get default log file path.
    
    Returns:
        Path to default log file
    """
    config_dir = get_config_dir()
    log_dir = config_dir / "logs"
    timestamp = datetime.now().strftime("%Y%m%d")
    return log_dir / f"derpy_{timestamp}.log"
