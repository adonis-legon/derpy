"""Tests for daemon entry point."""

import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from derpy.daemon.__main__ import parse_arguments, setup_logging, main
from derpy.daemon import __version__


class TestParseArguments:
    """Tests for command-line argument parsing."""
    
    def test_parse_arguments_defaults(self):
        """Test parsing with default arguments."""
        with patch('sys.argv', ['derpyd']):
            args = parse_arguments()
            
            assert args.socket == Path('/var/run/derpy.sock')
            assert args.group == 'derpy'
            assert args.max_workers == 4
            assert args.log_level == 'INFO'
    
    def test_parse_arguments_custom_socket(self):
        """Test parsing with custom socket path."""
        with patch('sys.argv', ['derpyd', '--socket', '/tmp/test.sock']):
            args = parse_arguments()
            
            assert args.socket == Path('/tmp/test.sock')
    
    def test_parse_arguments_custom_group(self):
        """Test parsing with custom group name."""
        with patch('sys.argv', ['derpyd', '--group', 'testgroup']):
            args = parse_arguments()
            
            assert args.group == 'testgroup'
    
    def test_parse_arguments_custom_max_workers(self):
        """Test parsing with custom max workers."""
        with patch('sys.argv', ['derpyd', '--max-workers', '8']):
            args = parse_arguments()
            
            assert args.max_workers == 8
    
    def test_parse_arguments_custom_log_level(self):
        """Test parsing with custom log level."""
        with patch('sys.argv', ['derpyd', '--log-level', 'DEBUG']):
            args = parse_arguments()
            
            assert args.log_level == 'DEBUG'
    
    def test_parse_arguments_version(self):
        """Test --version flag."""
        with patch('sys.argv', ['derpyd', '--version']):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            
            # argparse exits with 0 for --version
            assert exc_info.value.code == 0
    
    def test_parse_arguments_help(self):
        """Test --help flag."""
        with patch('sys.argv', ['derpyd', '--help']):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            
            # argparse exits with 0 for --help
            assert exc_info.value.code == 0


class TestSetupLogging:
    """Tests for logging setup."""
    
    def test_setup_logging_info(self):
        """Test setting up INFO logging."""
        setup_logging('INFO')
        
        import logging
        logger = logging.getLogger('derpy.daemon')
        assert logger.level == logging.INFO
    
    def test_setup_logging_debug(self):
        """Test setting up DEBUG logging."""
        setup_logging('DEBUG')
        
        import logging
        logger = logging.getLogger('derpy.daemon')
        assert logger.level == logging.DEBUG
    
    def test_setup_logging_invalid(self):
        """Test setting up with invalid log level."""
        with pytest.raises(ValueError):
            setup_logging('INVALID')


class TestMain:
    """Tests for main entry point."""
    
    @patch('derpy.daemon.__main__.DaemonServer')
    @patch('derpy.daemon.__main__.parse_arguments')
    def test_main_success(self, mock_parse_args, mock_server_class):
        """Test successful daemon startup."""
        # Mock arguments
        mock_args = MagicMock()
        mock_args.socket = Path('/tmp/test.sock')
        mock_args.group = 'derpy'
        mock_args.max_workers = 4
        mock_args.log_level = 'INFO'
        mock_parse_args.return_value = mock_args
        
        # Mock server
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        
        # Mock the wait loop to exit immediately
        with patch('derpy.daemon.__main__.threading.Event') as mock_event_class:
            mock_event = MagicMock()
            mock_event.wait.side_effect = KeyboardInterrupt()
            mock_event_class.return_value = mock_event
            
            # Run main
            result = main()
            
            # Verify server was created and started
            mock_server_class.assert_called_once_with(
                socket_path=mock_args.socket,
                group_name=mock_args.group,
                max_workers=mock_args.max_workers
            )
            mock_server.start.assert_called_once()
            mock_server.stop.assert_called_once()
            
            # Should return 0 for success
            assert result == 0
    
    @patch('derpy.daemon.__main__.DaemonServer')
    @patch('derpy.daemon.__main__.parse_arguments')
    def test_main_daemon_error(self, mock_parse_args, mock_server_class):
        """Test daemon startup error."""
        from derpy.daemon.server import DaemonError
        
        # Mock arguments
        mock_args = MagicMock()
        mock_args.socket = Path('/tmp/test.sock')
        mock_args.group = 'derpy'
        mock_args.max_workers = 4
        mock_args.log_level = 'INFO'
        mock_parse_args.return_value = mock_args
        
        # Mock server to raise error
        mock_server = MagicMock()
        mock_server.start.side_effect = DaemonError("Test error")
        mock_server_class.return_value = mock_server
        
        # Run main
        result = main()
        
        # Should return 1 for error
        assert result == 1
    
    @patch('derpy.daemon.__main__.DaemonServer')
    @patch('derpy.daemon.__main__.parse_arguments')
    def test_main_unexpected_error(self, mock_parse_args, mock_server_class):
        """Test unexpected error during startup."""
        # Mock arguments
        mock_args = MagicMock()
        mock_args.socket = Path('/tmp/test.sock')
        mock_args.group = 'derpy'
        mock_args.max_workers = 4
        mock_args.log_level = 'INFO'
        mock_parse_args.return_value = mock_args
        
        # Mock server to raise unexpected error
        mock_server = MagicMock()
        mock_server.start.side_effect = RuntimeError("Unexpected error")
        mock_server_class.return_value = mock_server
        
        # Run main
        result = main()
        
        # Should return 1 for error
        assert result == 1
