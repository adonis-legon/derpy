"""Property-based tests for CLI daemon integration.

Tests the integration of daemon client into CLI build command,
including daemon preference and fallback behavior.
"""

import os
import socket
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import pytest
from hypothesis import given, strategies as st, settings, assume
from click.testing import CliRunner

from derpy.cli.main import cli
from derpy.daemon.client import DaemonClient
from derpy.daemon.protocol import BuildResponse, OutputMessage
from derpy.daemon.framing import MessageFramer


class TestDaemonPreference:
    """Property 21: Daemon preference with sudo.
    
    Feature: daemon-socket-support, Property 21: Daemon preference with sudo
    Validates: Requirements 7.2
    
    For any invocation of derpy build with sudo, if the daemon is available,
    it should be used instead of direct execution.
    """
    
    @given(
        tag=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='-_.:/'
        )).filter(lambda x: ':' in x or '/' not in x)
    )
    @settings(max_examples=100)
    def test_property_daemon_preference_with_sudo(self, tag):
        """
        Property 21: Daemon preference with sudo
        
        For any invocation of derpy build with sudo, if the daemon is available,
        it should be used instead of direct execution.
        
        Validates: Requirements 7.2
        """
        # Ensure tag is valid (contains at least one alphanumeric)
        assume(any(c.isalnum() for c in tag))
        assume(len(tag.strip()) > 0)
        
        # Create a temporary directory for test context
        with tempfile.TemporaryDirectory() as tmpdir:
            context_path = Path(tmpdir)
            dockerfile_path = context_path / "Dockerfile"
            
            # Create a minimal Dockerfile
            dockerfile_path.write_text("FROM alpine:latest\nRUN echo 'test'\n")
            
            # Mock daemon client to simulate available daemon
            with patch('derpy.cli.main.DaemonClient') as MockDaemonClient:
                mock_client = Mock()
                MockDaemonClient.return_value = mock_client
                
                # Simulate daemon is available
                mock_client.is_available.return_value = True
                
                # Mock successful build response
                mock_response = BuildResponse(
                    success=True,
                    exit_code=0,
                    image_digest="sha256:abc123"
                )
                mock_client.send_build_request.return_value = mock_response
                
                # Run build command
                runner = CliRunner()
                result = runner.invoke(cli, [
                    'build',
                    str(context_path),
                    '-t', tag
                ])
                
                # Verify daemon was checked for availability
                mock_client.is_available.assert_called_once()
                
                # Verify daemon was used (send_build_request was called)
                mock_client.send_build_request.assert_called_once()
                
                # Verify the call included correct parameters
                call_args = mock_client.send_build_request.call_args
                # Use resolve() to handle path differences (e.g., /private prefix on macOS)
                assert call_args[1]['context_path'].resolve() == context_path.resolve()
                assert call_args[1]['dockerfile_path'].resolve() == dockerfile_path.resolve()
                assert call_args[1]['tag'] == tag
                
                # Verify output indicates daemon was used
                assert "Using daemon for build" in result.output
                
                # Verify no fallback warning
                assert "falling back to direct execution" not in result.output.lower()


class TestFallbackBehavior:
    """Property 22: Fallback to direct execution.
    
    Feature: daemon-socket-support, Property 22: Fallback to direct execution
    Validates: Requirements 7.3, 7.5
    
    For any build command when the daemon is unavailable and the user has sudo
    privileges, the CLI should fall back to direct execution with a warning.
    """
    
    @given(
        tag=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='-_.:/'
        )).filter(lambda x: ':' in x or '/' not in x)
    )
    @settings(max_examples=100)
    def test_property_fallback_to_direct_execution(self, tag):
        """
        Property 22: Fallback to direct execution
        
        For any build command when the daemon is unavailable, the CLI should
        fall back to direct execution with a warning.
        
        Validates: Requirements 7.3, 7.5
        """
        # Ensure tag is valid (contains at least one alphanumeric)
        assume(any(c.isalnum() for c in tag))
        assume(len(tag.strip()) > 0)
        
        # Create a temporary directory for test context
        with tempfile.TemporaryDirectory() as tmpdir:
            context_path = Path(tmpdir)
            dockerfile_path = context_path / "Dockerfile"
            
            # Create a minimal Dockerfile
            dockerfile_path.write_text("FROM alpine:latest\nRUN echo 'test'\n")
            
            # Mock daemon client to simulate unavailable daemon
            with patch('derpy.cli.main.DaemonClient') as MockDaemonClient:
                mock_client = Mock()
                MockDaemonClient.return_value = mock_client
                
                # Simulate daemon is NOT available
                mock_client.is_available.return_value = False
                
                # Mock the direct execution components
                with patch('derpy.cli.main.BuildEngine') as MockBuildEngine, \
                     patch('derpy.cli.main.ImageManager') as MockImageManager:
                    
                    # Setup mocks for direct execution
                    mock_image = Mock()
                    mock_image.layers = [Mock(), Mock()]
                    mock_engine = Mock()
                    mock_engine.build_image.return_value = mock_image
                    MockBuildEngine.return_value = mock_engine
                    
                    mock_storage = Mock()
                    MockImageManager.return_value = mock_storage
                    
                    # Run build command
                    runner = CliRunner()
                    result = runner.invoke(cli, [
                        'build',
                        str(context_path),
                        '-t', tag
                    ])
                    
                    # Verify daemon was checked for availability
                    mock_client.is_available.assert_called_once()
                    
                    # Verify daemon was NOT used (send_build_request was NOT called)
                    mock_client.send_build_request.assert_not_called()
                    
                    # Verify fallback warning was displayed
                    assert "Warning: Daemon not available" in result.output
                    assert "falling back to direct execution" in result.output
                    
                    # Verify direct execution was used
                    mock_engine.build_image.assert_called_once()
                    mock_storage.store_image.assert_called_once()
    
    @given(
        tag=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='-_.:/'
        )).filter(lambda x: ':' in x or '/' not in x)
    )
    @settings(max_examples=100)
    def test_property_fallback_maintains_functionality(self, tag):
        """
        Property 22 (extended): Fallback maintains functionality
        
        For any build command when falling back to direct execution,
        the build should complete successfully with the same functionality.
        
        Validates: Requirements 7.5
        """
        # Ensure tag is valid (contains at least one alphanumeric)
        assume(any(c.isalnum() for c in tag))
        assume(len(tag.strip()) > 0)
        
        # Create a temporary directory for test context
        with tempfile.TemporaryDirectory() as tmpdir:
            context_path = Path(tmpdir)
            dockerfile_path = context_path / "Dockerfile"
            
            # Create a minimal Dockerfile
            dockerfile_path.write_text("FROM alpine:latest\nRUN echo 'test'\n")
            
            # Mock daemon client to simulate unavailable daemon
            with patch('derpy.cli.main.DaemonClient') as MockDaemonClient:
                mock_client = Mock()
                MockDaemonClient.return_value = mock_client
                
                # Simulate daemon is NOT available
                mock_client.is_available.return_value = False
                
                # Mock the direct execution components
                with patch('derpy.cli.main.BuildEngine') as MockBuildEngine, \
                     patch('derpy.cli.main.ImageManager') as MockImageManager:
                    
                    # Setup mocks for direct execution
                    mock_image = Mock()
                    mock_image.layers = [Mock(), Mock()]
                    mock_engine = Mock()
                    mock_engine.build_image.return_value = mock_image
                    MockBuildEngine.return_value = mock_engine
                    
                    mock_storage = Mock()
                    MockImageManager.return_value = mock_storage
                    
                    # Run build command
                    runner = CliRunner()
                    result = runner.invoke(cli, [
                        'build',
                        str(context_path),
                        '-t', tag
                    ])
                    
                    # Verify build completed successfully
                    assert result.exit_code == 0
                    
                    # Verify success message was displayed
                    assert "Successfully built" in result.output
                    
                    # Verify image was stored
                    mock_storage.store_image.assert_called_once_with(mock_image, tag)
