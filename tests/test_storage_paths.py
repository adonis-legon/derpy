"""Tests for storage path configuration.

This module tests that the storage manager and daemon use the correct
fixed paths for image storage without relying on configuration files.
"""

import pytest
from pathlib import Path
from derpy.storage.manager import ImageManager
from derpy.daemon.handlers import RequestHandler


class TestStoragePaths:
    """Test storage path configuration."""
    
    def test_image_manager_default_path_direct_execution(self):
        """Test ImageManager uses ~/.derpy/images by default for direct execution."""
        manager = ImageManager()
        
        expected_path = Path.home() / '.derpy' / 'images'
        assert manager.repository_path == expected_path
    
    def test_image_manager_custom_path(self):
        """Test ImageManager accepts custom repository path."""
        custom_path = Path("/tmp/custom/images")
        manager = ImageManager(repository_path=custom_path)
        
        assert manager.repository_path == custom_path
    
    def test_request_handler_default_path_daemon_mode(self):
        """Test RequestHandler uses /var/lib/derpy/images by default for daemon."""
        handler = RequestHandler()
        
        expected_path = Path("/var/lib/derpy/images")
        assert handler.repository_path == expected_path
    
    def test_request_handler_custom_path(self):
        """Test RequestHandler accepts custom repository path."""
        custom_path = Path("/tmp/custom/images")
        handler = RequestHandler(repository_path=custom_path)
        
        assert handler.repository_path == custom_path
