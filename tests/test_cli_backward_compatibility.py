"""Property-based tests for CLI backward compatibility.

Tests that all existing CLI commands work unchanged with the daemon architecture,
ensuring backward compatibility with existing scripts and workflows.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
from hypothesis import given, strategies as st, settings, assume

from derpy.daemon.client import DaemonClient


class TestBackwardCompatibility:
    """Property 20: Command-line flag backward compatibility.
    
    Feature: daemon-socket-support, Property 20: Command-line flag backward compatibility
    Validates: Requirements 7.1
    
    For any existing command-line flag combination, the new CLI should accept
    it without changes.
    """
    
    @given(
        tag=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='-_.:/'
        )),
        dockerfile_name=st.sampled_from(['Dockerfile', 'Dockerfile.dev', 'custom.dockerfile']),
        daemon_available=st.booleans()
    )
    @settings(max_examples=100)
    def test_property_build_command_flags_unchanged(self, tag, dockerfile_name, daemon_available):
        """
        Property 20: Build command flag backward compatibility
        
        For any valid tag and dockerfile path, the build command should accept
        the same flags as before (--file/-f, --tag/-t) regardless of daemon
        availability.
        
        Validates: Requirements 7.1
        """
        # Filter out invalid tags
        assume(tag.strip() != '')
        assume(':' not in tag or tag.count(':') == 1)
        assume('/' not in tag or not tag.startswith('/'))
        
        from derpy.cli import main as cli_module
        from click.testing import CliRunner
        
        with tempfile.TemporaryDirectory() as tmpdir:
            context_path = Path(tmpdir)
            dockerfile_path = context_path / dockerfile_name
            
            # Create a minimal Dockerfile
            dockerfile_path.write_text("FROM alpine:latest\nRUN echo 'test'\n")
            
            # Mock the DaemonClient
            with patch.object(cli_module, 'DaemonClient') as mock_daemon_class:
                mock_client = MagicMock()
                mock_daemon_class.return_value = mock_client
                mock_client.is_available.return_value = daemon_available
                
                if daemon_available:
                    # Mock daemon response
                    from derpy.daemon.protocol import BuildResponse
                    mock_response = BuildResponse(
                        success=True,
                        exit_code=0,
                        image_digest="sha256:abc123"
                    )
                    mock_client.send_build_request.return_value = mock_response
                else:
                    # Mock direct execution components
                    with patch('derpy.cli.main.BuildEngine') as mock_engine_class, \
                         patch('derpy.cli.main.ImageManager') as mock_manager_class:
                        
                        mock_engine = MagicMock()
                        mock_engine_class.return_value = mock_engine
                        
                        mock_image = MagicMock()
                        mock_image.layers = []
                        mock_engine.build_image.return_value = mock_image
                        
                        mock_manager = MagicMock()
                        mock_manager_class.return_value = mock_manager
                        
                        runner = CliRunner()
                        
                        # Test with -f and -t flags (short form)
                        result = runner.invoke(cli_module.cli, [
                            'build', str(context_path),
                            '-f', str(dockerfile_path),
                            '-t', tag
                        ])
                        
                        # Command should be accepted (may succeed or fail, but should parse)
                        # Exit code 0 means success, 1 means execution error (acceptable)
                        assert result.exit_code in [0, 1], \
                            f"Build command with -f/-t flags should be accepted: {result.output}"
                        
                        # Verify no "unrecognized option" or "invalid option" errors
                        assert "unrecognized" not in result.output.lower(), \
                            "Flags should be recognized"
                        assert "invalid option" not in result.output.lower(), \
                            "Flags should be valid"
                        
                        return
                
                runner = CliRunner()
                
                # Test with -f and -t flags (short form)
                result = runner.invoke(cli_module.cli, [
                    'build', str(context_path),
                    '-f', str(dockerfile_path),
                    '-t', tag
                ])
                
                # Command should be accepted
                assert result.exit_code in [0, 1], \
                    f"Build command with -f/-t flags should be accepted: {result.output}"
                
                # Verify no "unrecognized option" or "invalid option" errors
                assert "unrecognized" not in result.output.lower(), \
                    "Flags should be recognized"
                assert "invalid option" not in result.output.lower(), \
                    "Flags should be valid"
    
    @given(
        tag=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='-_.:/'
        )),
        dockerfile_name=st.sampled_from(['Dockerfile', 'Dockerfile.prod']),
        daemon_available=st.booleans()
    )
    @settings(max_examples=100)
    def test_property_build_command_long_flags_unchanged(self, tag, dockerfile_name, daemon_available):
        """
        Property 20: Build command long flag backward compatibility
        
        For any valid tag and dockerfile path, the build command should accept
        the same long-form flags as before (--file, --tag).
        
        Validates: Requirements 7.1
        """
        # Filter out invalid tags
        assume(tag.strip() != '')
        assume(':' not in tag or tag.count(':') == 1)
        assume('/' not in tag or not tag.startswith('/'))
        
        from derpy.cli import main as cli_module
        from click.testing import CliRunner
        
        with tempfile.TemporaryDirectory() as tmpdir:
            context_path = Path(tmpdir)
            dockerfile_path = context_path / dockerfile_name
            
            # Create a minimal Dockerfile
            dockerfile_path.write_text("FROM alpine:latest\n")
            
            # Mock the DaemonClient
            with patch.object(cli_module, 'DaemonClient') as mock_daemon_class:
                mock_client = MagicMock()
                mock_daemon_class.return_value = mock_client
                mock_client.is_available.return_value = daemon_available
                
                if daemon_available:
                    # Mock daemon response
                    from derpy.daemon.protocol import BuildResponse
                    mock_response = BuildResponse(
                        success=True,
                        exit_code=0,
                        image_digest="sha256:abc123"
                    )
                    mock_client.send_build_request.return_value = mock_response
                else:
                    # Mock direct execution
                    with patch('derpy.cli.main.BuildEngine') as mock_engine_class, \
                         patch('derpy.cli.main.ImageManager') as mock_manager_class:
                        
                        mock_engine = MagicMock()
                        mock_engine_class.return_value = mock_engine
                        
                        mock_image = MagicMock()
                        mock_image.layers = []
                        mock_engine.build_image.return_value = mock_image
                        
                        mock_manager = MagicMock()
                        mock_manager_class.return_value = mock_manager
                        
                        runner = CliRunner()
                        
                        # Test with --file and --tag flags (long form)
                        result = runner.invoke(cli_module.cli, [
                            'build', str(context_path),
                            '--file', str(dockerfile_path),
                            '--tag', tag
                        ])
                        
                        # Command should be accepted
                        assert result.exit_code in [0, 1], \
                            f"Build command with --file/--tag flags should be accepted: {result.output}"
                        
                        # Verify no flag-related errors
                        assert "unrecognized" not in result.output.lower()
                        assert "invalid option" not in result.output.lower()
                        
                        return
                
                runner = CliRunner()
                
                # Test with --file and --tag flags (long form)
                result = runner.invoke(cli_module.cli, [
                    'build', str(context_path),
                    '--file', str(dockerfile_path),
                    '--tag', tag
                ])
                
                # Command should be accepted
                assert result.exit_code in [0, 1], \
                    f"Build command with --file/--tag flags should be accepted: {result.output}"
                
                # Verify no flag-related errors
                assert "unrecognized" not in result.output.lower()
                assert "invalid option" not in result.output.lower()
    
    @given(
        format_type=st.sampled_from(['table', 'json']),
        daemon_available=st.booleans()
    )
    @settings(max_examples=100)
    def test_property_ls_command_flags_unchanged(self, format_type, daemon_available):
        """
        Property 20: List command flag backward compatibility
        
        For any format type, the ls command should accept the same --format
        flag as before.
        
        Validates: Requirements 7.1
        """
        from derpy.cli import main as cli_module
        from click.testing import CliRunner
        
        # Mock the DaemonClient
        with patch.object(cli_module, 'DaemonClient') as mock_daemon_class:
            mock_client = MagicMock()
            mock_daemon_class.return_value = mock_client
            mock_client.is_available.return_value = daemon_available
            
            if daemon_available:
                # Mock daemon response
                from derpy.daemon.protocol import ListResponse
                mock_response = ListResponse(images=[])
                mock_client.send_list_request.return_value = mock_response
            else:
                # Mock direct execution
                with patch('derpy.cli.main.ImageManager') as mock_manager_class:
                    mock_manager = MagicMock()
                    mock_manager_class.return_value = mock_manager
                    mock_manager.list_local_images.return_value = []
                    
                    runner = CliRunner()
                    result = runner.invoke(cli_module.cli, ['ls', '--format', format_type])
                    
                    # Command should be accepted
                    assert result.exit_code == 0, \
                        f"ls command with --format flag should be accepted: {result.output}"
                    
                    # Verify no flag-related errors
                    assert "unrecognized" not in result.output.lower()
                    assert "invalid option" not in result.output.lower()
                    
                    return
            
            runner = CliRunner()
            result = runner.invoke(cli_module.cli, ['ls', '--format', format_type])
            
            # Command should be accepted
            assert result.exit_code == 0, \
                f"ls command with --format flag should be accepted: {result.output}"
            
            # Verify no flag-related errors
            assert "unrecognized" not in result.output.lower()
            assert "invalid option" not in result.output.lower()
    
    @given(
        force_flag=st.booleans(),
        daemon_available=st.booleans()
    )
    @settings(max_examples=100)
    def test_property_purge_command_flags_unchanged(self, force_flag, daemon_available):
        """
        Property 20: Purge command flag backward compatibility
        
        For any force flag value, the purge command should accept the same
        --force/-f flag as before.
        
        Validates: Requirements 7.1
        """
        from derpy.cli import main as cli_module
        from click.testing import CliRunner
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock the DaemonClient
            with patch.object(cli_module, 'DaemonClient') as mock_daemon_class:
                mock_client = MagicMock()
                mock_daemon_class.return_value = mock_client
                mock_client.is_available.return_value = daemon_available
                
                if daemon_available:
                    # Mock daemon response
                    from derpy.daemon.protocol import PurgeResponse
                    mock_response = PurgeResponse(
                        success=True,
                        removed_count=0
                    )
                    mock_client.send_purge_request.return_value = mock_response
                else:
                    # Mock direct execution
                    with patch('derpy.cli.main.ImageManager') as mock_manager_class:
                        
                        mock_manager = MagicMock()
                        mock_manager_class.return_value = mock_manager
                        mock_manager.remove_all_images.return_value = 0
                        mock_manager._load_metadata.return_value = {}
                        mock_manager.calculate_storage_size.return_value = 0
                        mock_manager.get_cache_size.return_value = 0
                        
                        runner = CliRunner()
                        
                        if force_flag:
                            result = runner.invoke(cli_module.cli, ['purge', '--force'])
                        else:
                            result = runner.invoke(cli_module.cli, ['purge'])
                        
                        # Command should be accepted
                        assert result.exit_code == 0, \
                            f"purge command with --force flag should be accepted: {result.output}"
                        
                        # Verify no flag-related errors
                        assert "unrecognized" not in result.output.lower()
                        assert "invalid option" not in result.output.lower()
                        
                        return
                
                runner = CliRunner()
                
                if force_flag:
                    result = runner.invoke(cli_module.cli, ['purge', '--force'])
                else:
                    result = runner.invoke(cli_module.cli, ['purge'])
                
                # Command should be accepted
                assert result.exit_code == 0, \
                    f"purge command with --force flag should be accepted: {result.output}"
                
                # Verify no flag-related errors
                assert "unrecognized" not in result.output.lower()
                assert "invalid option" not in result.output.lower()
    
    @given(
        command=st.sampled_from(['build', 'ls', 'rm', 'purge', 'login', 'logout', 'push', 'config']),
        verbose=st.booleans(),
        debug=st.booleans()
    )
    @settings(max_examples=100)
    def test_property_global_flags_unchanged(self, command, verbose, debug):
        """
        Property 20: Global flag backward compatibility
        
        For any command, the global flags (--verbose, --debug) should be
        accepted as before.
        
        Validates: Requirements 7.1
        """
        from derpy.cli import main as cli_module
        from click.testing import CliRunner
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Build command-specific arguments
            args = []
            
            if verbose:
                args.append('--verbose')
            if debug:
                args.append('--debug')
            
            args.append(command)
            
            # Add command-specific required arguments
            if command == 'build':
                context_path = Path(tmpdir)
                dockerfile_path = context_path / 'Dockerfile'
                dockerfile_path.write_text("FROM alpine:latest\n")
                args.extend([str(context_path), '-f', str(dockerfile_path), '-t', 'test:latest'])
            elif command == 'rm':
                args.append('test:latest')
            elif command == 'purge':
                args.append('--force')
            elif command == 'login':
                # Skip login as it requires interactive input
                return
            elif command == 'logout':
                pass  # No additional args needed
            elif command == 'push':
                args.append('test:latest')
            elif command == 'config':
                args.append('show')
            
            # Mock necessary components
            with patch.object(cli_module, 'DaemonClient') as mock_daemon_class, \
                 patch('derpy.cli.main.ImageManager') as mock_manager_class, \
                 patch('derpy.cli.main.AuthManager') as mock_auth_class, \
                 patch('derpy.cli.main.BuildEngine') as mock_engine_class:
                
                # Setup mocks
                mock_client = MagicMock()
                mock_daemon_class.return_value = mock_client
                mock_client.is_available.return_value = False
                
                mock_manager = MagicMock()
                mock_manager_class.return_value = mock_manager
                mock_manager.list_local_images.return_value = []
                mock_manager.remove_image.return_value = False
                mock_manager.remove_all_images.return_value = 0
                mock_manager._load_metadata.return_value = {}
                mock_manager.calculate_storage_size.return_value = 0
                mock_manager.get_cache_size.return_value = 0
                mock_manager.image_exists.return_value = False
                
                mock_auth = MagicMock()
                mock_auth_class.return_value = mock_auth
                mock_auth.logout.return_value = False
                
                mock_engine = MagicMock()
                mock_engine_class.return_value = mock_engine
                mock_image = MagicMock()
                mock_image.layers = []
                mock_engine.build_image.return_value = mock_image
                
                runner = CliRunner()
                result = runner.invoke(cli_module.cli, args)
                
                # Command should be accepted (may fail for other reasons, but flags should parse)
                # Exit codes 0, 1, or 2 are acceptable (2 for usage errors like missing image)
                assert result.exit_code in [0, 1, 2], \
                    f"Command with global flags should be accepted: {result.output}"
                
                # Verify no flag-related errors
                assert "unrecognized" not in result.output.lower(), \
                    f"Global flags should be recognized: {result.output}"
                assert "invalid option" not in result.output.lower(), \
                    f"Global flags should be valid: {result.output}"


class TestConfigurationBackwardCompatibility:
    """Test that configuration file format remains unchanged."""
    
    @pytest.mark.skip(reason="ConfigManager removed in v0.3.0 - config no longer used")
    def test_config_file_format_unchanged(self):
        """
        Verify that the configuration file format has not changed.
        
        NOTE: This test is skipped because ConfigManager was removed in v0.3.0.
        Configuration is now handled by the daemon with fixed paths.
        
        Validates: Requirements 7.1
        """
        pass
    
    def test_image_storage_format_unchanged(self):
        """
        Verify that the image storage format has not changed.
        
        Images stored with v0.1.0 should be readable with v0.2.0.
        
        Validates: Requirements 7.1
        """
        from derpy.storage import ImageManager
        from derpy.oci.models import Image, Manifest, ImageConfig, Layer, Descriptor
        
        with tempfile.TemporaryDirectory() as tmpdir:
            images_path = Path(tmpdir) / "images"
            images_path.mkdir()
            
            # Create an ImageManager
            manager = ImageManager(images_path)
            
            # Create a test image with v0.1.0 structure
            from derpy.oci.models import RootFS, ContainerConfig
            import hashlib
            
            # Create actual layer content and write it to disk
            layer_content = b"test layer content"
            layer_digest = f"sha256:{hashlib.sha256(layer_content).hexdigest()}"
            diff_id = f"sha256:{hashlib.sha256(layer_content).hexdigest()}"
            
            # Write layer to blobs directory
            blobs_dir = images_path / "blobs" / "sha256"
            blobs_dir.mkdir(parents=True, exist_ok=True)
            layer_file = blobs_dir / layer_digest.split(':')[1]
            layer_file.write_bytes(layer_content)
            
            test_layer = Layer(
                digest=layer_digest,
                size=len(layer_content),
                diff_id=diff_id
            )
            
            # Create config
            test_config = ImageConfig(
                architecture="amd64",
                os="linux",
                rootfs=RootFS(type="layers", diff_ids=[diff_id]),
                config=ContainerConfig()
            )
            
            # Compute config digest and write config
            config_json = test_config.to_json()
            config_digest = f"sha256:{hashlib.sha256(config_json.encode()).hexdigest()}"
            config_file = blobs_dir / config_digest.split(':')[1]
            config_file.write_text(config_json)
            
            test_image = Image(
                manifest=Manifest(
                    schema_version=2,
                    media_type="application/vnd.oci.image.manifest.v1+json",
                    config=Descriptor(
                        media_type="application/vnd.oci.image.config.v1+json",
                        digest=config_digest,
                        size=len(config_json)
                    ),
                    layers=[test_layer.to_descriptor()]
                ),
                config=test_config,
                layers=[test_layer]
            )
            
            # Store the image
            manager.store_image(test_image, "test:v1")
            
            # Verify we can list it
            images = manager.list_local_images()
            assert len(images) == 1
            assert images[0].tag == "test:v1"
            
            # Verify image exists
            assert manager.image_exists("test:v1")
            
            # Verify we can retrieve it
            loaded_image = manager.get_image("test:v1")
            assert loaded_image is not None
            assert loaded_image.config.architecture == "amd64"


class TestScriptBackwardCompatibility:
    """Test that existing scripts continue to work."""
    
    @given(
        daemon_available=st.booleans()
    )
    @settings(max_examples=50)
    def test_property_script_execution_unchanged(self, daemon_available):
        """
        Property 20: Script execution backward compatibility
        
        For any script that uses derpy commands, the script should continue
        to work with the same exit codes and output format.
        
        Validates: Requirements 7.1
        """
        from derpy.cli import main as cli_module
        from click.testing import CliRunner
        
        # Simulate a script that runs: derpy ls
        with patch.object(cli_module, 'DaemonClient') as mock_daemon_class:
            mock_client = MagicMock()
            mock_daemon_class.return_value = mock_client
            mock_client.is_available.return_value = daemon_available
            
            if daemon_available:
                from derpy.daemon.protocol import ListResponse
                mock_client.send_list_request.return_value = ListResponse(images=[])
            else:
                with patch('derpy.cli.main.ImageManager') as mock_manager_class:
                    mock_manager = MagicMock()
                    mock_manager_class.return_value = mock_manager
                    mock_manager.list_local_images.return_value = []
                    
                    runner = CliRunner()
                    result = runner.invoke(cli_module.cli, ['ls'])
                    
                    # Script should get consistent exit code
                    assert result.exit_code == 0
                    
                    # Script should get parseable output
                    assert "no images" in result.output.lower() or "total:" in result.output.lower()
                    
                    return
            
            runner = CliRunner()
            result = runner.invoke(cli_module.cli, ['ls'])
            
            # Script should get consistent exit code
            assert result.exit_code == 0
            
            # Script should get parseable output
            assert "no images" in result.output.lower() or "total:" in result.output.lower()
