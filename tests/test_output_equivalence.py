"""Tests for output equivalence between daemon and direct execution.

Property 3: Output equivalence for successful builds
Property 4: Error message equivalence for failed builds
Feature: daemon-socket-support, Property 3: Output equivalence for successful builds
Feature: daemon-socket-support, Property 4: Error message equivalence for failed builds
Validates: Requirements 1.4, 1.5
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings, assume
from click.testing import CliRunner

from derpy.cli.main import cli
from derpy.daemon.client import DaemonClient
from derpy.daemon.protocol import BuildResponse
from derpy.build.engine import BuildEngine, BuildContext
from derpy.storage.manager import ImageManager
from derpy.oci.models import Image, ImageConfig, Manifest, Layer


class TestOutputEquivalence:
    """Tests for Property 3 and Property 4: Output equivalence.
    
    Property 3: Output equivalence for successful builds
    For any successful build operation, the output displayed by the daemon-based
    CLI should match the output from the current sudo-based implementation.
    
    Property 4: Error message equivalence for failed builds
    For any failed build operation, the error messages displayed by the daemon-based
    CLI should contain the same detail as the current sudo-based implementation.
    
    Validates: Requirements 1.4, 1.5
    """
    
    def test_successful_build_output_contains_key_elements(self):
        """Test that successful build output contains expected elements."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            context_path = Path(tmpdir)
            dockerfile_path = context_path / "Dockerfile"
            
            # Create a minimal Dockerfile
            dockerfile_path.write_text("FROM scratch\nCMD [\"echo\", \"test\"]\n")
            
            # Mock daemon as unavailable to test direct execution
            with patch('derpy.cli.main.DaemonClient') as mock_daemon_class:
                mock_client = Mock()
                mock_client.is_available.return_value = False
                mock_daemon_class.return_value = mock_client
                
                # Mock the build components for direct execution
                with patch('derpy.cli.main.BuildEngine') as mock_engine_class, \
                     patch('derpy.cli.main.ImageManager') as mock_manager_class:
                    
                    # Setup mock image
                    mock_image = Mock(spec=Image)
                    mock_image.layers = [Mock(spec=Layer)]
                    
                    # Setup mock engine
                    mock_engine = Mock()
                    mock_engine.build_image.return_value = mock_image
                    mock_engine_class.return_value = mock_engine
                    
                    # Setup mock storage
                    mock_storage = Mock()
                    mock_manager_class.return_value = mock_storage
                    
                    # Run build command
                    result = runner.invoke(cli, [
                        'build',
                        str(context_path),
                        '-f', str(dockerfile_path),
                        '-t', 'test:success'
                    ])
                    
                    # Verify output contains key elements
                    assert "Building image 'test:success'" in result.output
                    assert "Context:" in result.output
                    assert "Dockerfile:" in result.output
                    assert "Successfully built" in result.output or "✓" in result.output
                    
                    # Verify build was executed
                    mock_engine.build_image.assert_called_once()
                    mock_storage.store_image.assert_called_once()
    
    def test_failed_build_output_contains_error_details(self):
        """Test that failed build output contains error details."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            context_path = Path(tmpdir)
            dockerfile_path = context_path / "Dockerfile"
            
            # Create an invalid Dockerfile
            dockerfile_path.write_text("INVALID INSTRUCTION\n")
            
            # Mock daemon as unavailable to test direct execution
            with patch('derpy.cli.main.DaemonClient') as mock_daemon_class:
                mock_client = Mock()
                mock_client.is_available.return_value = False
                mock_daemon_class.return_value = mock_client
                
                # Mock the build components to raise an error
                with patch('derpy.cli.main.BuildEngine') as mock_engine_class:
                    from derpy.build import BuildError
                    
                    mock_engine = Mock()
                    mock_engine.build_image.side_effect = BuildError("Unknown instruction: INVALID")
                    mock_engine_class.return_value = mock_engine
                    
                    # Run build command
                    result = runner.invoke(cli, [
                        'build',
                        str(context_path),
                        '-f', str(dockerfile_path),
                        '-t', 'test:failure'
                    ])
                    
                    # Verify error output contains details
                    assert result.exit_code != 0
                    assert "error" in result.output.lower() or "Error" in result.output
                    assert "INVALID" in result.output or "Unknown instruction" in result.output
    
    def test_daemon_and_direct_execution_show_similar_success_messages(self):
        """Test that daemon and direct execution show similar success messages."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            context_path = Path(tmpdir)
            dockerfile_path = context_path / "Dockerfile"
            
            # Create a minimal Dockerfile
            dockerfile_path.write_text("FROM scratch\nCMD [\"echo\", \"test\"]\n")
            
            # Test with daemon
            with patch('derpy.cli.main.DaemonClient') as mock_daemon_class:
                mock_client = Mock()
                mock_client.is_available.return_value = True
                mock_daemon_class.return_value = mock_client
                
                # Mock successful daemon response
                mock_response = BuildResponse(
                    success=True,
                    exit_code=0,
                    image_digest="sha256:abc123"
                )
                mock_client.send_build_request.return_value = mock_response
                
                # Run build with daemon
                daemon_result = runner.invoke(cli, [
                    'build',
                    str(context_path),
                    '-f', str(dockerfile_path),
                    '-t', 'test:daemon'
                ])
                
                # Verify daemon success output
                assert daemon_result.exit_code == 0
                assert "Successfully built" in daemon_result.output or "✓" in daemon_result.output
                assert "test:daemon" in daemon_result.output
            
            # Test with direct execution
            with patch('derpy.cli.main.DaemonClient') as mock_daemon_class:
                mock_client = Mock()
                mock_client.is_available.return_value = False
                mock_daemon_class.return_value = mock_client
                
                # Mock the build components for direct execution
                with patch('derpy.cli.main.BuildEngine') as mock_engine_class, \
                     patch('derpy.cli.main.ImageManager') as mock_manager_class:
                    
                    # Setup mock image
                    mock_image = Mock(spec=Image)
                    mock_image.layers = [Mock(spec=Layer)]
                    
                    # Setup mock engine
                    mock_engine = Mock()
                    mock_engine.build_image.return_value = mock_image
                    mock_engine_class.return_value = mock_engine
                    
                    # Setup mock storage
                    mock_storage = Mock()
                    mock_manager_class.return_value = mock_storage
                    
                    # Run build with direct execution
                    direct_result = runner.invoke(cli, [
                        'build',
                        str(context_path),
                        '-f', str(dockerfile_path),
                        '-t', 'test:direct'
                    ])
                    
                    # Verify direct execution success output
                    assert direct_result.exit_code == 0
                    assert "Successfully built" in direct_result.output or "✓" in direct_result.output
                    assert "test:direct" in direct_result.output
            
            # Both should have similar success indicators
            assert ("Successfully built" in daemon_result.output) == ("Successfully built" in direct_result.output)
    
    def test_daemon_and_direct_execution_show_similar_error_messages(self):
        """Test that daemon and direct execution show similar error messages."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            context_path = Path(tmpdir)
            dockerfile_path = context_path / "Dockerfile"
            
            # Create an invalid Dockerfile
            dockerfile_path.write_text("INVALID INSTRUCTION\n")
            
            error_message = "Unknown instruction: INVALID"
            
            # Test with daemon
            with patch('derpy.cli.main.DaemonClient') as mock_daemon_class:
                mock_client = Mock()
                mock_client.is_available.return_value = True
                mock_daemon_class.return_value = mock_client
                
                # Mock failed daemon response
                mock_response = BuildResponse(
                    success=False,
                    exit_code=1,
                    error_message=error_message
                )
                mock_client.send_build_request.return_value = mock_response
                
                # Run build with daemon
                daemon_result = runner.invoke(cli, [
                    'build',
                    str(context_path),
                    '-f', str(dockerfile_path),
                    '-t', 'test:daemon_fail'
                ])
                
                # Verify daemon error output
                assert daemon_result.exit_code != 0
                assert error_message in daemon_result.output
            
            # Test with direct execution
            with patch('derpy.cli.main.DaemonClient') as mock_daemon_class:
                mock_client = Mock()
                mock_client.is_available.return_value = False
                mock_daemon_class.return_value = mock_client
                
                # Mock the build components to raise an error
                with patch('derpy.cli.main.BuildEngine') as mock_engine_class:
                    from derpy.build import BuildError
                    
                    mock_engine = Mock()
                    mock_engine.build_image.side_effect = BuildError(error_message)
                    mock_engine_class.return_value = mock_engine
                    
                    # Run build with direct execution
                    direct_result = runner.invoke(cli, [
                        'build',
                        str(context_path),
                        '-f', str(dockerfile_path),
                        '-t', 'test:direct_fail'
                    ])
                    
                    # Verify direct execution error output
                    assert direct_result.exit_code != 0
                    assert error_message in direct_result.output
            
            # Both should contain the same error message
            assert error_message in daemon_result.output
            assert error_message in direct_result.output


class TestOutputEquivalencePropertyBased:
    """Property-based tests for output equivalence.
    
    Feature: daemon-socket-support, Property 3: Output equivalence for successful builds
    Feature: daemon-socket-support, Property 4: Error message equivalence for failed builds
    Validates: Requirements 1.4, 1.5
    """
    
    @given(
        name=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_."),
            min_size=1,
            max_size=15
        ),
        version=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_."),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=20, deadline=60000)
    def test_property_successful_build_output_equivalence(self, name, version):
        """
        Property 3: Output equivalence for successful builds
        
        For any successful build operation, the output displayed by the daemon-based
        CLI should match the output from the current sudo-based implementation.
        
        Validates: Requirements 1.4
        """
        # Skip invalid names/versions
        assume(name.strip() != "")
        assume(version.strip() != "")
        assume(not name.startswith("-") and not name.endswith("-"))
        assume(not version.startswith("-") and not version.endswith("-"))
        
        # Construct valid tag
        tag = f"{name}:{version}"
        
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            context_path = Path(tmpdir)
            dockerfile_path = context_path / "Dockerfile"
            
            # Create a minimal Dockerfile
            dockerfile_path.write_text("FROM scratch\nCMD [\"echo\", \"test\"]\n")
            
            # Collect outputs from both methods
            daemon_output = None
            direct_output = None
            
            # Test with daemon
            with patch('derpy.cli.main.DaemonClient') as mock_daemon_class:
                mock_client = Mock()
                mock_client.is_available.return_value = True
                mock_daemon_class.return_value = mock_client
                
                # Mock successful daemon response
                mock_response = BuildResponse(
                    success=True,
                    exit_code=0,
                    image_digest="sha256:abc123def456"
                )
                mock_client.send_build_request.return_value = mock_response
                
                # Run build with daemon
                daemon_result = runner.invoke(cli, [
                    'build',
                    str(context_path),
                    '-f', str(dockerfile_path),
                    '-t', tag
                ])
                
                daemon_output = daemon_result.output
            
            # Test with direct execution
            with patch('derpy.cli.main.DaemonClient') as mock_daemon_class:
                mock_client = Mock()
                mock_client.is_available.return_value = False
                mock_daemon_class.return_value = mock_client
                
                # Mock the build components for direct execution
                with patch('derpy.cli.main.BuildEngine') as mock_engine_class, \
                     patch('derpy.cli.main.ImageManager') as mock_manager_class:
                    
                    # Setup mock image
                    mock_image = Mock(spec=Image)
                    mock_image.layers = [Mock(spec=Layer)]
                    
                    # Setup mock engine
                    mock_engine = Mock()
                    mock_engine.build_image.return_value = mock_image
                    mock_engine_class.return_value = mock_engine
                    
                    # Setup mock storage
                    mock_storage = Mock()
                    mock_manager_class.return_value = mock_storage
                    
                    # Run build with direct execution
                    direct_result = runner.invoke(cli, [
                        'build',
                        str(context_path),
                        '-f', str(dockerfile_path),
                        '-t', tag
                    ])
                    
                    direct_output = direct_result.output
            
            # Verify both outputs contain key success elements
            assert daemon_output is not None
            assert direct_output is not None
            
            # Both should indicate success
            assert daemon_result.exit_code == 0
            assert direct_result.exit_code == 0
            
            # Both should mention the tag
            assert tag in daemon_output
            assert tag in direct_output
            
            # Both should have success indicators
            success_indicators = ["Successfully built", "✓"]
            daemon_has_success = any(indicator in daemon_output for indicator in success_indicators)
            direct_has_success = any(indicator in direct_output for indicator in success_indicators)
            
            assert daemon_has_success, f"Daemon output missing success indicator: {daemon_output}"
            assert direct_has_success, f"Direct output missing success indicator: {direct_output}"
            
            # Both should mention building
            assert "Building" in daemon_output or "build" in daemon_output.lower()
            assert "Building" in direct_output or "build" in direct_output.lower()
    
    @given(
        error_type=st.sampled_from([
            "Unknown instruction",
            "Invalid syntax",
            "Missing required field",
            "File not found"
        ]),
        error_detail=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters=" "),
            min_size=5,
            max_size=30
        )
    )
    @settings(max_examples=20, deadline=60000)
    def test_property_failed_build_error_message_equivalence(self, error_type, error_detail):
        """
        Property 4: Error message equivalence for failed builds
        
        For any failed build operation, the error messages displayed by the daemon-based
        CLI should contain the same detail as the current sudo-based implementation.
        
        Validates: Requirements 1.5
        """
        # Skip invalid error details
        assume(error_detail.strip() != "")
        assume(not any(c in error_detail for c in ["\n", "\r", "\t"]))
        
        runner = CliRunner()
        
        # Construct error message
        error_message = f"{error_type}: {error_detail}"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            context_path = Path(tmpdir)
            dockerfile_path = context_path / "Dockerfile"
            
            # Create an invalid Dockerfile
            dockerfile_path.write_text("INVALID INSTRUCTION\n")
            
            # Collect outputs from both methods
            daemon_output = None
            direct_output = None
            
            # Test with daemon
            with patch('derpy.cli.main.DaemonClient') as mock_daemon_class:
                mock_client = Mock()
                mock_client.is_available.return_value = True
                mock_daemon_class.return_value = mock_client
                
                # Mock failed daemon response
                mock_response = BuildResponse(
                    success=False,
                    exit_code=1,
                    error_message=error_message
                )
                mock_client.send_build_request.return_value = mock_response
                
                # Run build with daemon
                daemon_result = runner.invoke(cli, [
                    'build',
                    str(context_path),
                    '-f', str(dockerfile_path),
                    '-t', 'test:fail'
                ])
                
                daemon_output = daemon_result.output
            
            # Test with direct execution
            with patch('derpy.cli.main.DaemonClient') as mock_daemon_class:
                mock_client = Mock()
                mock_client.is_available.return_value = False
                mock_daemon_class.return_value = mock_client
                
                # Mock the build components to raise an error
                with patch('derpy.cli.main.BuildEngine') as mock_engine_class:
                    from derpy.build import BuildError
                    
                    mock_engine = Mock()
                    mock_engine.build_image.side_effect = BuildError(error_message)
                    mock_engine_class.return_value = mock_engine
                    
                    # Run build with direct execution
                    direct_result = runner.invoke(cli, [
                        'build',
                        str(context_path),
                        '-f', str(dockerfile_path),
                        '-t', 'test:fail'
                    ])
                    
                    direct_output = direct_result.output
            
            # Verify both outputs contain the error message
            assert daemon_output is not None
            assert direct_output is not None
            
            # Both should indicate failure
            assert daemon_result.exit_code != 0
            assert direct_result.exit_code != 0
            
            # Both should contain the error message
            assert error_message in daemon_output, f"Daemon output missing error: {daemon_output}"
            assert error_message in direct_output, f"Direct output missing error: {direct_output}"
            
            # Both should have error indicators
            error_indicators = ["error", "Error", "failed", "Failed"]
            daemon_has_error = any(indicator in daemon_output for indicator in error_indicators)
            direct_has_error = any(indicator in direct_output for indicator in error_indicators)
            
            assert daemon_has_error, f"Daemon output missing error indicator: {daemon_output}"
            assert direct_has_error, f"Direct output missing error indicator: {direct_output}"
