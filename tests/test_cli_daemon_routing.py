"""Property-based tests for CLI daemon routing.

Tests that CLI commands properly route to daemon when available and fall back
to direct execution when daemon is unavailable, especially for non-privileged
commands.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
from hypothesis import given, strategies as st, settings

from derpy.daemon.client import DaemonClient


class TestNonPrivilegedCommandRouting:
    """Property 23: Non-privileged command direct execution.
    
    Feature: daemon-socket-support, Property 23: Non-privileged command direct execution
    Validates: Requirements 7.4
    
    For any non-privileged command (ls, rm without isolation, etc.), the CLI
    should execute it directly without daemon communication.
    """
    
    @given(
        command=st.sampled_from(['ls', 'rm', 'purge']),
        daemon_available=st.booleans()
    )
    @settings(max_examples=100)
    def test_property_non_privileged_command_routing(self, command, daemon_available):
        """
        Property 23: Non-privileged command direct execution
        
        For any non-privileged command, when the daemon is available, the command
        should use the daemon. When the daemon is unavailable, the command should
        execute directly without requiring elevated privileges.
        
        Validates: Requirements 7.4
        """
        # Import CLI module
        from derpy.cli import main as cli_module
        from click.testing import CliRunner
        
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            
            # Mock the DaemonClient to control availability
            with patch.object(cli_module, 'DaemonClient') as mock_daemon_class:
                mock_client = MagicMock()
                mock_daemon_class.return_value = mock_client
                mock_client.is_available.return_value = daemon_available
                
                # Mock ImageManager for direct execution
                with patch('derpy.cli.main.ImageManager') as mock_image_manager:
                    mock_manager = MagicMock()
                    mock_image_manager.return_value = mock_manager
                    
                    # Set up mock responses based on command
                    if command == 'ls':
                        if daemon_available:
                            # Mock daemon response
                            from derpy.daemon.protocol import ListResponse, ImageInfo
                            mock_response = ListResponse(images=[])
                            mock_client.send_list_request.return_value = mock_response
                        else:
                            # Mock direct execution
                            mock_manager.list_local_images.return_value = []
                    
                    elif command == 'rm':
                        if daemon_available:
                            # Mock daemon response
                            from derpy.daemon.protocol import RemoveResponse
                            mock_response = RemoveResponse(
                                success=False,
                                error_message="Image 'test:latest' not found"
                            )
                            mock_client.send_remove_request.return_value = mock_response
                        else:
                            # Mock direct execution
                            mock_manager.remove_image.return_value = False
                    
                    elif command == 'purge':
                        if daemon_available:
                            # Mock daemon response
                            from derpy.daemon.protocol import PurgeResponse
                            mock_response = PurgeResponse(
                                success=True,
                                removed_count=0
                            )
                            mock_client.send_purge_request.return_value = mock_response
                        else:
                            # Mock direct execution - need at least one image to avoid early return
                            mock_manager.remove_all_images.return_value = 1
                            mock_manager._load_metadata.return_value = {'test:latest': {}}
                            mock_manager.calculate_storage_size.return_value = 1024
                            mock_manager.get_cache_size.return_value = 0
                    
                    # Mock ConfigManager for purge command
                    with patch('derpy.cli.main.ConfigManager') as mock_config_manager:
                        mock_config = MagicMock()
                        mock_config.build_settings.base_image_cache_dir = tmpdir
                        mock_config_manager.return_value.get_config.return_value = mock_config
                        
                        # Run the CLI command
                        runner = CliRunner()
                        
                        if command == 'ls':
                            result = runner.invoke(cli_module.cli, ['ls'])
                        elif command == 'rm':
                            result = runner.invoke(cli_module.cli, ['rm', 'test:latest'])
                        elif command == 'purge':
                            result = runner.invoke(cli_module.cli, ['purge', '--force'])
                        
                        # Verify the command executed (may succeed or fail, but should not crash)
                        # Exit code 0 or 1 is acceptable (1 for "not found" errors)
                        assert result.exit_code in [0, 1], \
                            f"Command should execute without crashing: {result.output}"
                        
                        # Verify routing behavior
                        if daemon_available:
                            # Should have checked daemon availability
                            mock_client.is_available.assert_called()
                            
                            # Should have used daemon
                            if command == 'ls':
                                mock_client.send_list_request.assert_called_once()
                            elif command == 'rm':
                                mock_client.send_remove_request.assert_called_once()
                            elif command == 'purge':
                                mock_client.send_purge_request.assert_called_once()
                        else:
                            # Should have checked daemon availability
                            mock_client.is_available.assert_called()
                            
                            # Should have fallen back to direct execution
                            if command == 'ls':
                                mock_manager.list_local_images.assert_called()
                            elif command == 'rm':
                                mock_manager.remove_image.assert_called()
                            elif command == 'purge':
                                mock_manager.remove_all_images.assert_called()
    
    @given(
        command=st.sampled_from(['ls', 'rm', 'purge'])
    )
    @settings(max_examples=50)
    def test_property_fallback_without_sudo_requirement(self, command):
        """
        Property 23 (fallback case): Direct execution without sudo
        
        For any non-privileged command, when the daemon is unavailable,
        the command should execute directly without requiring sudo or
        elevated privileges.
        
        Validates: Requirements 7.4
        """
        # Import CLI module
        from derpy.cli import main as cli_module
        from click.testing import CliRunner
        
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock the DaemonClient to simulate unavailable daemon
            with patch.object(cli_module, 'DaemonClient') as mock_daemon_class:
                mock_client = MagicMock()
                mock_daemon_class.return_value = mock_client
                mock_client.is_available.return_value = False
                
                # Mock ImageManager for direct execution
                with patch('derpy.cli.main.ImageManager') as mock_image_manager:
                    mock_manager = MagicMock()
                    mock_image_manager.return_value = mock_manager
                    
                    # Set up mock responses
                    mock_manager.list_local_images.return_value = []
                    mock_manager.remove_image.return_value = False
                    mock_manager.remove_all_images.return_value = 1
                    mock_manager._load_metadata.return_value = {'test:latest': {}}
                    mock_manager.calculate_storage_size.return_value = 1024
                    mock_manager.get_cache_size.return_value = 0
                    
                    # Mock ConfigManager
                    with patch('derpy.cli.main.ConfigManager') as mock_config_manager:
                        mock_config = MagicMock()
                        mock_config.build_settings.base_image_cache_dir = tmpdir
                        mock_config_manager.return_value.get_config.return_value = mock_config
                        
                        # Run the CLI command
                        runner = CliRunner()
                        
                        if command == 'ls':
                            result = runner.invoke(cli_module.cli, ['ls'])
                        elif command == 'rm':
                            result = runner.invoke(cli_module.cli, ['rm', 'test:latest'])
                        elif command == 'purge':
                            result = runner.invoke(cli_module.cli, ['purge', '--force'])
                        
                        # Verify the command executed without requiring sudo
                        # The command should complete (exit code 0 or 1 for "not found")
                        assert result.exit_code in [0, 1], \
                            f"Command should execute without sudo: {result.output}"
                        
                        # Verify no sudo-related errors in output
                        assert "sudo" not in result.output.lower(), \
                            "Command should not require sudo for non-privileged operations"
                        
                        # Verify direct execution was used
                        if command == 'ls':
                            mock_manager.list_local_images.assert_called()
                        elif command == 'rm':
                            mock_manager.remove_image.assert_called()
                        elif command == 'purge':
                            mock_manager.remove_all_images.assert_called()
    
    @given(
        daemon_available=st.booleans()
    )
    @settings(max_examples=50)
    def test_property_daemon_preference_for_all_commands(self, daemon_available):
        """
        Property 23 (daemon preference): Daemon preference when available
        
        For any command (privileged or non-privileged), when the daemon is
        available, it should be preferred over direct execution.
        
        Validates: Requirements 7.4
        """
        # Import CLI module
        from derpy.cli import main as cli_module
        from click.testing import CliRunner
        
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock the DaemonClient
            with patch.object(cli_module, 'DaemonClient') as mock_daemon_class:
                mock_client = MagicMock()
                mock_daemon_class.return_value = mock_client
                mock_client.is_available.return_value = daemon_available
                
                # Mock daemon responses
                from derpy.daemon.protocol import ListResponse
                mock_client.send_list_request.return_value = ListResponse(images=[])
                
                # Mock ImageManager for direct execution
                with patch('derpy.cli.main.ImageManager') as mock_image_manager:
                    mock_manager = MagicMock()
                    mock_image_manager.return_value = mock_manager
                    mock_manager.list_local_images.return_value = []
                    
                    # Run ls command
                    runner = CliRunner()
                    result = runner.invoke(cli_module.cli, ['ls'])
                    
                    # Verify command executed
                    assert result.exit_code == 0, \
                        f"Command should execute successfully: {result.output}"
                    
                    # Verify routing
                    if daemon_available:
                        # Should use daemon
                        mock_client.send_list_request.assert_called_once()
                        # Should NOT use direct execution
                        mock_manager.list_local_images.assert_not_called()
                    else:
                        # Should use direct execution
                        mock_manager.list_local_images.assert_called()
                        # Should NOT use daemon
                        mock_client.send_list_request.assert_not_called()
    
    @given(dummy=st.just(None))
    @settings(max_examples=50)
    def test_property_consistent_output_format(self, dummy):
        """
        Property 23 (output consistency): Consistent output format
        
        For any command, the output format should be consistent whether
        using daemon or direct execution.
        
        Validates: Requirements 7.4
        """
        # Import CLI module
        from derpy.cli import main as cli_module
        from click.testing import CliRunner
        
        # Test with daemon available
        with patch.object(cli_module, 'DaemonClient') as mock_daemon_class:
            mock_client = MagicMock()
            mock_daemon_class.return_value = mock_client
            mock_client.is_available.return_value = True
            
            from derpy.daemon.protocol import ListResponse
            mock_client.send_list_request.return_value = ListResponse(images=[])
            
            runner = CliRunner()
            result_daemon = runner.invoke(cli_module.cli, ['ls'])
        
        # Test with daemon unavailable
        with patch.object(cli_module, 'DaemonClient') as mock_daemon_class:
            mock_client = MagicMock()
            mock_daemon_class.return_value = mock_client
            mock_client.is_available.return_value = False
            
            with patch('derpy.cli.main.ImageManager') as mock_image_manager:
                mock_manager = MagicMock()
                mock_image_manager.return_value = mock_manager
                mock_manager.list_local_images.return_value = []
                
                runner = CliRunner()
                result_direct = runner.invoke(cli_module.cli, ['ls'])
        
        # Both should succeed
        assert result_daemon.exit_code == 0
        assert result_direct.exit_code == 0
        
        # Both should have similar output structure (both mention "No images found")
        assert "no images" in result_daemon.output.lower()
        assert "no images" in result_direct.output.lower()


class TestDaemonRoutingIntegration:
    """Integration tests for daemon routing behavior."""
    
    def test_ls_command_uses_daemon_when_available(self):
        """Test that ls command uses daemon when available."""
        from derpy.cli import main as cli_module
        from click.testing import CliRunner
        
        with patch.object(cli_module, 'DaemonClient') as mock_daemon_class:
            mock_client = MagicMock()
            mock_daemon_class.return_value = mock_client
            mock_client.is_available.return_value = True
            
            from derpy.daemon.protocol import ListResponse
            mock_client.send_list_request.return_value = ListResponse(images=[])
            
            runner = CliRunner()
            result = runner.invoke(cli_module.cli, ['ls'])
            
            assert result.exit_code == 0
            mock_client.send_list_request.assert_called_once()
    
    def test_rm_command_uses_daemon_when_available(self):
        """Test that rm command uses daemon when available."""
        from derpy.cli import main as cli_module
        from click.testing import CliRunner
        
        with patch.object(cli_module, 'DaemonClient') as mock_daemon_class:
            mock_client = MagicMock()
            mock_daemon_class.return_value = mock_client
            mock_client.is_available.return_value = True
            
            from derpy.daemon.protocol import RemoveResponse
            mock_client.send_remove_request.return_value = RemoveResponse(
                success=True
            )
            
            runner = CliRunner()
            result = runner.invoke(cli_module.cli, ['rm', 'test:latest'])
            
            assert result.exit_code == 0
            mock_client.send_remove_request.assert_called_once_with('test:latest')
    
    def test_purge_command_uses_daemon_when_available(self):
        """Test that purge command uses daemon when available."""
        from derpy.cli import main as cli_module
        from click.testing import CliRunner
        
        with patch.object(cli_module, 'DaemonClient') as mock_daemon_class:
            mock_client = MagicMock()
            mock_daemon_class.return_value = mock_client
            mock_client.is_available.return_value = True
            
            from derpy.daemon.protocol import PurgeResponse
            mock_client.send_purge_request.return_value = PurgeResponse(
                success=True,
                removed_count=0
            )
            
            runner = CliRunner()
            result = runner.invoke(cli_module.cli, ['purge', '--force'])
            
            assert result.exit_code == 0
            mock_client.send_purge_request.assert_called_once()
    
    def test_commands_fallback_to_direct_when_daemon_unavailable(self):
        """Test that commands fall back to direct execution when daemon unavailable."""
        from derpy.cli import main as cli_module
        from click.testing import CliRunner
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(cli_module, 'DaemonClient') as mock_daemon_class:
                mock_client = MagicMock()
                mock_daemon_class.return_value = mock_client
                mock_client.is_available.return_value = False
                
                with patch('derpy.cli.main.ImageManager') as mock_image_manager:
                    mock_manager = MagicMock()
                    mock_image_manager.return_value = mock_manager
                    mock_manager.list_local_images.return_value = []
                    
                    runner = CliRunner()
                    result = runner.invoke(cli_module.cli, ['ls'])
                    
                    assert result.exit_code == 0
                    mock_manager.list_local_images.assert_called()
                    mock_client.send_list_request.assert_not_called()
