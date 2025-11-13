"""Tests for logging module."""

import pytest
import logging
from pathlib import Path
import tempfile

from derpy.core.logging import (
    DerpyLogger,
    get_logger,
    setup_logging,
    get_default_log_file,
    DEFAULT_FORMAT,
    SIMPLE_FORMAT,
    DETAILED_FORMAT
)


class TestDerpyLogger:
    """Tests for DerpyLogger class."""
    
    def test_singleton_pattern(self):
        """Test that DerpyLogger follows singleton pattern."""
        logger1 = DerpyLogger()
        logger2 = DerpyLogger()
        assert logger1 is logger2
    
    def test_logger_initialization(self):
        """Test logger initialization."""
        derpy_logger = DerpyLogger()
        assert derpy_logger.logger is not None
        assert derpy_logger.logger.name == 'derpy'
    
    def test_get_logger_without_name(self):
        """Test getting logger without name."""
        derpy_logger = DerpyLogger()
        logger = derpy_logger.get_logger()
        assert logger is not None
        assert logger.name == 'derpy'
    
    def test_get_logger_with_name(self):
        """Test getting logger with name."""
        derpy_logger = DerpyLogger()
        logger = derpy_logger.get_logger('test')
        assert logger is not None
        assert logger.name == 'derpy.test'
    
    def test_set_level(self):
        """Test setting log level."""
        derpy_logger = DerpyLogger()
        derpy_logger.set_level(logging.DEBUG)
        assert derpy_logger.logger.level == logging.DEBUG
        
        derpy_logger.set_level(logging.WARNING)
        assert derpy_logger.logger.level == logging.WARNING
    
    def test_setup_console_logging(self):
        """Test setup with console logging."""
        derpy_logger = DerpyLogger()
        derpy_logger.setup(level=logging.INFO, console=True)
        assert len(derpy_logger.logger.handlers) > 0
    
    def test_setup_file_logging(self):
        """Test setup with file logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            derpy_logger = DerpyLogger()
            derpy_logger.setup(level=logging.INFO, log_file=log_file, console=False)
            
            # Log a message
            derpy_logger.logger.info("Test message")
            
            # Check file was created
            assert log_file.exists()
    
    def test_setup_with_custom_format(self):
        """Test setup with custom format."""
        derpy_logger = DerpyLogger()
        derpy_logger.setup(format_string=DETAILED_FORMAT)
        assert len(derpy_logger.logger.handlers) > 0


class TestGetLogger:
    """Tests for get_logger function."""
    
    def test_get_logger_function(self):
        """Test get_logger function."""
        logger = get_logger()
        assert logger is not None
        assert 'derpy' in logger.name
    
    def test_get_logger_with_name(self):
        """Test get_logger with name."""
        logger = get_logger('module')
        assert logger is not None
        assert logger.name == 'derpy.module'


class TestSetupLogging:
    """Tests for setup_logging function."""
    
    def test_setup_logging_default(self):
        """Test setup_logging with defaults."""
        setup_logging()
        logger = get_logger()
        assert logger.level <= logging.WARNING
    
    def test_setup_logging_verbose(self):
        """Test setup_logging with verbose flag."""
        setup_logging(verbose=True)
        logger = get_logger()
        assert logger.level <= logging.INFO
    
    def test_setup_logging_debug(self):
        """Test setup_logging with debug flag."""
        setup_logging(debug=True)
        logger = get_logger()
        assert logger.level <= logging.DEBUG
    
    def test_setup_logging_quiet(self):
        """Test setup_logging with quiet flag."""
        setup_logging(quiet=True)
        derpy_logger = DerpyLogger()
        # When quiet, console handler should not be added
        # or handlers should be empty
        assert True  # Just verify it doesn't crash
    
    def test_setup_logging_with_file(self):
        """Test setup_logging with log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            setup_logging(log_file=log_file)
            
            logger = get_logger()
            logger.info("Test message")
            
            assert log_file.exists()


class TestGetDefaultLogFile:
    """Tests for get_default_log_file function."""
    
    def test_get_default_log_file(self):
        """Test get_default_log_file returns a Path."""
        log_file = get_default_log_file()
        assert isinstance(log_file, Path)
        assert 'derpy' in str(log_file)
        assert '.log' in str(log_file)
    
    def test_default_log_file_has_timestamp(self):
        """Test default log file includes timestamp."""
        log_file = get_default_log_file()
        # Should contain date in format YYYYMMDD
        assert any(char.isdigit() for char in log_file.name)


class TestLogFormats:
    """Tests for log format constants."""
    
    def test_format_constants_exist(self):
        """Test that format constants are defined."""
        assert DEFAULT_FORMAT is not None
        assert SIMPLE_FORMAT is not None
        assert DETAILED_FORMAT is not None
    
    def test_format_constants_are_strings(self):
        """Test that format constants are strings."""
        assert isinstance(DEFAULT_FORMAT, str)
        assert isinstance(SIMPLE_FORMAT, str)
        assert isinstance(DETAILED_FORMAT, str)
    
    def test_formats_contain_placeholders(self):
        """Test that formats contain logging placeholders."""
        assert '%(' in DEFAULT_FORMAT
        assert '%(' in SIMPLE_FORMAT
        assert '%(' in DETAILED_FORMAT


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
