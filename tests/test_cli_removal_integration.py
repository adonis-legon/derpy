"""Integration tests for CLI removal commands (rm and purge)."""

import pytest
from click.testing import CliRunner
from pathlib import Path
import tempfile
import hashlib
import shutil
from unittest.mock import patch, MagicMock

from derpy.cli.main import cli
from derpy.storage.manager import ImageManager
from derpy.core.config import Config, BuildSettings
from derpy.oci.models import (
    Image,
    ImageConfig,
    Manifest,
    Layer,
    Descriptor,
    RootFS,
    ContainerConfig,
    MEDIA_TYPE_IMAGE_CONFIG,
    MEDIA_TYPE_IMAGE_LAYER,
)


class TestRmCommandIntegration:
    """Integration tests for rm command."""
    
    def mock_config(self, tmpdir: str):
        """Create a mock config that uses the temporary directory."""
        repo_path = Path(tmpdir) / "images"
        cache_dir = Path(tmpdir) / "cache" / "base-images"
        
        config = Config(
            images_path=repo_path,
            registry_configs={},
            build_settings=BuildSettings(base_image_cache_dir=str(cache_dir))
        )
        return config
    
    def create_test_image(self, tag: str = "test:latest") -> Image:
        """Helper to create a test image with real content."""
        # Create a simple test layer with real digest
        layer_content = b"test layer content for " + tag.encode()
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.tar.gz') as f:
            f.write(layer_content)
            layer_path = Path(f.name)
        
        # Compute real digest
        layer_digest = f"sha256:{hashlib.sha256(layer_content).hexdigest()}"
        
        layer = Layer(
            digest=layer_digest,
            size=len(layer_content),
            diff_id="sha256:testdiff123",
            content_path=layer_path
        )
        
        config = ImageConfig(
            architecture="amd64",
            os="linux",
            rootfs=RootFS(diff_ids=["sha256:testdiff123"]),
            config=ContainerConfig(cmd=["/bin/sh"]),
            created="2024-01-15T10:00:00Z"
        )
        
        config_desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_CONFIG,
            digest="sha256:testconfig123",
            size=100
        )
        
        layer_desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_LAYER,
            digest=layer_digest,
            size=len(layer_content)
        )
        
        manifest = Manifest(
            config=config_desc,
            layers=[layer_desc]
        )
        
        return Image(
            manifest=manifest,
            config=config,
            layers=[layer]
        )
    
    def test_rm_removes_image_and_displays_success(self):
        """Test removing image via CLI displays success message."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            config = self.mock_config(tmpdir)
            
            # Store an image
            manager = ImageManager(repo_path)
            image = self.create_test_image("myapp:v1")
            manager.store_image(image, "myapp:v1")
            
            # Verify image exists
            assert manager.image_exists("myapp:v1")
            
            # Mock ConfigManager in both locations
            with patch('derpy.cli.main.ConfigManager') as mock_cli_config, \
                 patch('derpy.storage.manager.ConfigManager') as mock_storage_config:
                
                mock_cli_instance = MagicMock()
                mock_cli_instance.get_config.return_value = config
                mock_cli_instance.load_config.return_value = config
                mock_cli_config.return_value = mock_cli_instance
                
                mock_storage_instance = MagicMock()
                mock_storage_instance.load_config.return_value = config
                mock_storage_config.return_value = mock_storage_instance
                
                # Remove via CLI
                result = runner.invoke(cli, ['rm', 'myapp:v1'])
            
            # Check exit code
            assert result.exit_code == 0
            
            # Check output format
            assert "Removing image 'myapp:v1'" in result.output
            assert "Successfully removed image: myapp:v1" in result.output
            assert "Freed:" in result.output
            
            # Verify image is actually removed
            assert not manager.image_exists("myapp:v1")
    
    def test_rm_nonexistent_image_displays_error(self):
        """Test removing non-existent image displays error."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            config = self.mock_config(tmpdir)
            
            # Initialize empty repository
            manager = ImageManager(repo_path)
            
            # Mock ConfigManager in both locations
            with patch('derpy.cli.main.ConfigManager') as mock_cli_config, \
                 patch('derpy.storage.manager.ConfigManager') as mock_storage_config:
                
                mock_cli_instance = MagicMock()
                mock_cli_instance.get_config.return_value = config
                mock_cli_instance.load_config.return_value = config
                mock_cli_config.return_value = mock_cli_instance
                
                mock_storage_instance = MagicMock()
                mock_storage_instance.load_config.return_value = config
                mock_storage_config.return_value = mock_storage_instance
                
                # Try to remove non-existent image
                result = runner.invoke(cli, ['rm', 'nonexistent:v1'])
            
            # Check exit code
            assert result.exit_code == 1
            
            # Check error message
            assert "Error: Image 'nonexistent:v1' not found" in result.output
            assert "derpy ls" in result.output
    
    def test_rm_exit_codes(self):
        """Test exit codes (0 for success, 1 for error)."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            config = self.mock_config(tmpdir)
            
            # Store an image
            manager = ImageManager(repo_path)
            image = self.create_test_image("myapp:v1")
            manager.store_image(image, "myapp:v1")
            
            # Mock ConfigManager in both locations
            with patch('derpy.cli.main.ConfigManager') as mock_cli_config, \
                 patch('derpy.storage.manager.ConfigManager') as mock_storage_config:
                
                mock_cli_instance = MagicMock()
                mock_cli_instance.get_config.return_value = config
                mock_cli_instance.load_config.return_value = config
                mock_cli_config.return_value = mock_cli_instance
                
                mock_storage_instance = MagicMock()
                mock_storage_instance.load_config.return_value = config
                mock_storage_config.return_value = mock_storage_instance
                
                # Success case - exit code 0
                result = runner.invoke(cli, ['rm', 'myapp:v1'])
                assert result.exit_code == 0
                
                # Error case - exit code 1
                result = runner.invoke(cli, ['rm', 'nonexistent:v1'])
                assert result.exit_code == 1
    
    def test_rm_output_format_matches_design(self):
        """Test output format matches design."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            config = self.mock_config(tmpdir)
            
            # Store an image
            manager = ImageManager(repo_path)
            image = self.create_test_image("testapp:latest")
            manager.store_image(image, "testapp:latest")
            
            # Mock ConfigManager in both locations
            with patch('derpy.cli.main.ConfigManager') as mock_cli_config, \
                 patch('derpy.storage.manager.ConfigManager') as mock_storage_config:
                
                mock_cli_instance = MagicMock()
                mock_cli_instance.get_config.return_value = config
                mock_cli_instance.load_config.return_value = config
                mock_cli_config.return_value = mock_cli_instance
                
                mock_storage_instance = MagicMock()
                mock_storage_instance.load_config.return_value = config
                mock_storage_config.return_value = mock_storage_instance
                
                # Remove via CLI
                result = runner.invoke(cli, ['rm', 'testapp:latest'])
            
            # Verify output format matches design
            assert result.exit_code == 0
            assert "Removing image 'testapp:latest'" in result.output
            assert "✓ Successfully removed image: testapp:latest" in result.output
            
            # Should show freed space in human-readable format
            assert "Freed:" in result.output
            # Should have a size unit (B, KB, MB, GB, TB)
            assert any(unit in result.output for unit in ['B', 'KB', 'MB', 'GB', 'TB'])


class TestPurgeCommandIntegration:
    """Integration tests for purge command."""
    
    def mock_config(self, tmpdir: str):
        """Create a mock config that uses the temporary directory."""
        repo_path = Path(tmpdir) / "images"
        cache_dir = Path(tmpdir) / "cache" / "base-images"
        
        config = Config(
            images_path=repo_path,
            registry_configs={},
            build_settings=BuildSettings(base_image_cache_dir=str(cache_dir))
        )
        return config
    
    def create_test_image(self, tag: str = "test:latest") -> Image:
        """Helper to create a test image with real content."""
        # Create a simple test layer with real digest
        layer_content = b"test layer content for " + tag.encode()
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.tar.gz') as f:
            f.write(layer_content)
            layer_path = Path(f.name)
        
        # Compute real digest
        layer_digest = f"sha256:{hashlib.sha256(layer_content).hexdigest()}"
        
        layer = Layer(
            digest=layer_digest,
            size=len(layer_content),
            diff_id="sha256:testdiff123",
            content_path=layer_path
        )
        
        config = ImageConfig(
            architecture="amd64",
            os="linux",
            rootfs=RootFS(diff_ids=["sha256:testdiff123"]),
            config=ContainerConfig(cmd=["/bin/sh"]),
            created="2024-01-15T10:00:00Z"
        )
        
        config_desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_CONFIG,
            digest="sha256:testconfig123",
            size=100
        )
        
        layer_desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_LAYER,
            digest=layer_digest,
            size=len(layer_content)
        )
        
        manifest = Manifest(
            config=config_desc,
            layers=[layer_desc]
        )
        
        return Image(
            manifest=manifest,
            config=config,
            layers=[layer]
        )
    
    def test_purge_with_force_removes_all_images(self):
        """Test purge with --force flag removes all images."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            config = self.mock_config(tmpdir)
            
            # Store multiple images
            manager = ImageManager(repo_path)
            image1 = self.create_test_image("app1:v1")
            manager.store_image(image1, "app1:v1")
            
            image2 = self.create_test_image("app2:v2")
            manager.store_image(image2, "app2:v2")
            
            image3 = self.create_test_image("app3:v3")
            manager.store_image(image3, "app3:v3")
            
            # Verify images exist
            assert manager.image_exists("app1:v1")
            assert manager.image_exists("app2:v2")
            assert manager.image_exists("app3:v3")
            
            # Mock ConfigManager to use our test config
            with patch('derpy.cli.main.ConfigManager') as mock_cli_config, \
                 patch('derpy.storage.manager.ConfigManager') as mock_storage_config:
                
                mock_cli_instance = MagicMock()
                mock_cli_instance.get_config.return_value = config
                mock_cli_instance.load_config.return_value = config
                mock_cli_config.return_value = mock_cli_instance
                
                mock_storage_instance = MagicMock()
                mock_storage_instance.load_config.return_value = config
                mock_storage_config.return_value = mock_storage_instance
                
                # Purge with --force
                result = runner.invoke(cli, ['purge', '--force'])
            
            # Check exit code
            assert result.exit_code == 0
            
            # Check output
            assert "Removing all images" in result.output
            assert "Successfully purged all images" in result.output
            assert "Images removed: 3" in result.output
            assert "Space freed:" in result.output
            
            # Verify all images are removed
            assert not manager.image_exists("app1:v1")
            assert not manager.image_exists("app2:v2")
            assert not manager.image_exists("app3:v3")
    
    def test_purge_displays_confirmation_prompt_without_force(self):
        """Test purge displays confirmation prompt without --force."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            config = self.mock_config(tmpdir)
            
            # Store an image
            manager = ImageManager(repo_path)
            image = self.create_test_image("myapp:v1")
            manager.store_image(image, "myapp:v1")
            
            # Mock ConfigManager to use our test config
            with patch('derpy.cli.main.ConfigManager') as mock_cli_config, \
                 patch('derpy.storage.manager.ConfigManager') as mock_storage_config:
                
                mock_cli_instance = MagicMock()
                mock_cli_instance.get_config.return_value = config
                mock_cli_instance.load_config.return_value = config
                mock_cli_config.return_value = mock_cli_instance
                
                mock_storage_instance = MagicMock()
                mock_storage_instance.load_config.return_value = config
                mock_storage_config.return_value = mock_storage_instance
                
                # Purge without --force, answer 'y' to confirmation
                result = runner.invoke(cli, ['purge'], input='y\n')
            
            # Check output contains warning and confirmation prompt
            assert "WARNING: This will remove all images and cached data" in result.output
            assert "Images: 1" in result.output
            assert "Storage:" in result.output
            assert "Cache:" in result.output
            assert "Total:" in result.output
            assert "Are you sure you want to continue?" in result.output
            
            # Check exit code
            assert result.exit_code == 0
            
            # Verify image is removed
            assert not manager.image_exists("myapp:v1")
    
    def test_purge_with_no_images_displays_appropriate_message(self):
        """Test purge with no images displays appropriate message."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            config = self.mock_config(tmpdir)
            
            # Initialize empty repository
            manager = ImageManager(repo_path)
            
            # Mock ConfigManager to use our test config
            with patch('derpy.cli.main.ConfigManager') as mock_cli_config, \
                 patch('derpy.storage.manager.ConfigManager') as mock_storage_config:
                
                mock_cli_instance = MagicMock()
                mock_cli_instance.get_config.return_value = config
                mock_cli_instance.load_config.return_value = config
                mock_cli_config.return_value = mock_cli_instance
                
                mock_storage_instance = MagicMock()
                mock_storage_instance.load_config.return_value = config
                mock_storage_config.return_value = mock_storage_instance
                
                # Purge with no images
                result = runner.invoke(cli, ['purge', '--force'])
            
            # Check exit code
            assert result.exit_code == 0
            
            # Check message
            assert "No images found" in result.output
            assert "Nothing to purge" in result.output
    
    def test_purge_exit_codes(self):
        """Test exit codes."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            config = self.mock_config(tmpdir)
            
            # Store an image
            manager = ImageManager(repo_path)
            image = self.create_test_image("myapp:v1")
            manager.store_image(image, "myapp:v1")
            
            # Mock ConfigManager to use our test config
            with patch('derpy.cli.main.ConfigManager') as mock_cli_config, \
                 patch('derpy.storage.manager.ConfigManager') as mock_storage_config:
                
                mock_cli_instance = MagicMock()
                mock_cli_instance.get_config.return_value = config
                mock_cli_instance.load_config.return_value = config
                mock_cli_config.return_value = mock_cli_instance
                
                mock_storage_instance = MagicMock()
                mock_storage_instance.load_config.return_value = config
                mock_storage_config.return_value = mock_storage_instance
                
                # Success case with --force - exit code 0
                result = runner.invoke(cli, ['purge', '--force'])
                assert result.exit_code == 0
            
            # Re-add image for cancellation test (outside the mock context)
            manager.store_image(image, "myapp:v1")
            
            # Mock ConfigManager again for cancellation test
            with patch('derpy.cli.main.ConfigManager') as mock_cli_config, \
                 patch('derpy.storage.manager.ConfigManager') as mock_storage_config:
                
                mock_cli_instance = MagicMock()
                mock_cli_instance.get_config.return_value = config
                mock_cli_instance.load_config.return_value = config
                mock_cli_config.return_value = mock_cli_instance
                
                mock_storage_instance = MagicMock()
                mock_storage_instance.load_config.return_value = config
                mock_storage_config.return_value = mock_storage_instance
                
                # User cancellation - exit code 0 (not an error)
                result = runner.invoke(cli, ['purge'], input='n\n')
                assert result.exit_code == 0
                assert "Operation cancelled" in result.output
    
    def test_purge_output_format_and_summary(self):
        """Test output format and summary."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            cache_dir = Path(tmpdir) / "cache" / "base-images"
            config = self.mock_config(tmpdir)
            
            # Create cache directory so the message appears
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Store multiple images
            manager = ImageManager(repo_path)
            image1 = self.create_test_image("app1:v1")
            manager.store_image(image1, "app1:v1")
            
            image2 = self.create_test_image("app2:v2")
            manager.store_image(image2, "app2:v2")
            
            # Mock ConfigManager to use our test config
            with patch('derpy.cli.main.ConfigManager') as mock_cli_config, \
                 patch('derpy.storage.manager.ConfigManager') as mock_storage_config:
                
                mock_cli_instance = MagicMock()
                mock_cli_instance.get_config.return_value = config
                mock_cli_instance.load_config.return_value = config
                mock_cli_config.return_value = mock_cli_instance
                
                mock_storage_instance = MagicMock()
                mock_storage_instance.load_config.return_value = config
                mock_storage_config.return_value = mock_storage_instance
                
                # Purge with --force
                result = runner.invoke(cli, ['purge', '--force'])
            
            # Verify output format
            assert result.exit_code == 0
            assert "Removing all images..." in result.output
            assert "Clearing base image cache..." in result.output
            assert "✓ Successfully purged all images" in result.output
            assert "Images removed: 2" in result.output
            assert "Space freed:" in result.output
            
            # Should show size in human-readable format
            assert any(unit in result.output for unit in ['B', 'KB', 'MB', 'GB', 'TB'])


class TestEndToEndWorkflows:
    """End-to-end workflow tests."""
    
    def mock_config(self, tmpdir: str):
        """Create a mock config that uses the temporary directory."""
        repo_path = Path(tmpdir) / "images"
        cache_dir = Path(tmpdir) / "cache" / "base-images"
        
        config = Config(
            images_path=repo_path,
            registry_configs={},
            build_settings=BuildSettings(base_image_cache_dir=str(cache_dir))
        )
        return config
    
    def create_test_image(self, tag: str = "test:latest") -> Image:
        """Helper to create a test image with real content."""
        # Create a simple test layer with real digest
        layer_content = b"test layer content for " + tag.encode()
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.tar.gz') as f:
            f.write(layer_content)
            layer_path = Path(f.name)
        
        # Compute real digest
        layer_digest = f"sha256:{hashlib.sha256(layer_content).hexdigest()}"
        
        layer = Layer(
            digest=layer_digest,
            size=len(layer_content),
            diff_id="sha256:testdiff123",
            content_path=layer_path
        )
        
        config = ImageConfig(
            architecture="amd64",
            os="linux",
            rootfs=RootFS(diff_ids=["sha256:testdiff123"]),
            config=ContainerConfig(cmd=["/bin/sh"]),
            created="2024-01-15T10:00:00Z"
        )
        
        config_desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_CONFIG,
            digest="sha256:testconfig123",
            size=100
        )
        
        layer_desc = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_LAYER,
            digest=layer_digest,
            size=len(layer_content)
        )
        
        manifest = Manifest(
            config=config_desc,
            layers=[layer_desc]
        )
        
        return Image(
            manifest=manifest,
            config=config,
            layers=[layer]
        )
    
    def test_build_remove_verify_workflow(self):
        """Test: Build image, remove with rm, verify removal."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            config = self.mock_config(tmpdir)
            
            # Simulate building an image (store it)
            manager = ImageManager(repo_path)
            image = self.create_test_image("webapp:v1")
            manager.store_image(image, "webapp:v1")
            
            # Verify image exists
            assert manager.image_exists("webapp:v1")
            
            # Mock ConfigManager to use our test config
            with patch('derpy.cli.main.ConfigManager') as mock_cli_config, \
                 patch('derpy.storage.manager.ConfigManager') as mock_storage_config:
                
                mock_cli_instance = MagicMock()
                mock_cli_instance.get_config.return_value = config
                mock_cli_instance.load_config.return_value = config
                mock_cli_config.return_value = mock_cli_instance
                
                mock_storage_instance = MagicMock()
                mock_storage_instance.load_config.return_value = config
                mock_storage_config.return_value = mock_storage_instance
                
                # List images
                result = runner.invoke(cli, ['ls'])
                assert result.exit_code == 0
                assert "webapp:v1" in result.output
                
                # Remove image
                result = runner.invoke(cli, ['rm', 'webapp:v1'])
                assert result.exit_code == 0
                assert "Successfully removed image: webapp:v1" in result.output
            
            # Verify removal
            assert not manager.image_exists("webapp:v1")
            
            # Mock ConfigManager again for second ls command
            with patch('derpy.cli.main.ConfigManager') as mock_cli_config, \
                 patch('derpy.storage.manager.ConfigManager') as mock_storage_config:
                
                mock_cli_instance = MagicMock()
                mock_cli_instance.get_config.return_value = config
                mock_cli_instance.load_config.return_value = config
                mock_cli_config.return_value = mock_cli_instance
                
                mock_storage_instance = MagicMock()
                mock_storage_instance.load_config.return_value = config
                mock_storage_config.return_value = mock_storage_instance
                
                # List images again - should be empty
                result = runner.invoke(cli, ['ls'])
                assert result.exit_code == 0
                assert "No images found" in result.output
    
    def test_build_multiple_purge_verify_workflow(self):
        """Test: Build multiple images, purge, verify all removed."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            config = self.mock_config(tmpdir)
            
            # Simulate building multiple images
            manager = ImageManager(repo_path)
            image1 = self.create_test_image("app1:v1")
            manager.store_image(image1, "app1:v1")
            
            image2 = self.create_test_image("app2:v2")
            manager.store_image(image2, "app2:v2")
            
            image3 = self.create_test_image("app3:v3")
            manager.store_image(image3, "app3:v3")
            
            # Verify all images exist
            assert manager.image_exists("app1:v1")
            assert manager.image_exists("app2:v2")
            assert manager.image_exists("app3:v3")
            
            # Mock ConfigManager to use our test config
            with patch('derpy.cli.main.ConfigManager') as mock_cli_config, \
                 patch('derpy.storage.manager.ConfigManager') as mock_storage_config:
                
                mock_cli_instance = MagicMock()
                mock_cli_instance.get_config.return_value = config
                mock_cli_instance.load_config.return_value = config
                mock_cli_config.return_value = mock_cli_instance
                
                mock_storage_instance = MagicMock()
                mock_storage_instance.load_config.return_value = config
                mock_storage_config.return_value = mock_storage_instance
                
                # List images
                result = runner.invoke(cli, ['ls'])
                assert result.exit_code == 0
                assert "app1:v1" in result.output
                assert "app2:v2" in result.output
                assert "app3:v3" in result.output
                assert "Total: 3 image(s)" in result.output
                
                # Purge all images
                result = runner.invoke(cli, ['purge', '--force'])
                assert result.exit_code == 0
                assert "Images removed: 3" in result.output
            
            # Verify all removed
            assert not manager.image_exists("app1:v1")
            assert not manager.image_exists("app2:v2")
            assert not manager.image_exists("app3:v3")
            
            # Mock ConfigManager again for second ls command
            with patch('derpy.cli.main.ConfigManager') as mock_cli_config, \
                 patch('derpy.storage.manager.ConfigManager') as mock_storage_config:
                
                mock_cli_instance = MagicMock()
                mock_cli_instance.get_config.return_value = config
                mock_cli_instance.load_config.return_value = config
                mock_cli_config.return_value = mock_cli_instance
                
                mock_storage_instance = MagicMock()
                mock_storage_instance.load_config.return_value = config
                mock_storage_config.return_value = mock_storage_instance
                
                # List images again - should be empty
                result = runner.invoke(cli, ['ls'])
                assert result.exit_code == 0
                assert "No images found" in result.output
    
    def test_build_purge_with_cache_verify_workflow(self):
        """Test: Build image, purge with cache, verify cache cleared."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "images"
            cache_dir = Path(tmpdir) / "cache" / "base-images"
            cache_dir.mkdir(parents=True)
            config = self.mock_config(tmpdir)
            
            # Create some cache files
            (cache_dir / "cached_layer1.tar.gz").write_bytes(b"cached layer 1")
            (cache_dir / "cached_layer2.tar.gz").write_bytes(b"cached layer 2")
            
            # Simulate building an image
            manager = ImageManager(repo_path)
            image = self.create_test_image("myapp:latest")
            manager.store_image(image, "myapp:latest")
            
            # Verify image and cache exist
            assert manager.image_exists("myapp:latest")
            assert cache_dir.exists()
            assert len(list(cache_dir.iterdir())) == 2
            
            # Mock ConfigManager to use our test config
            with patch('derpy.cli.main.ConfigManager') as mock_cli_config, \
                 patch('derpy.storage.manager.ConfigManager') as mock_storage_config:
                
                mock_cli_instance = MagicMock()
                mock_cli_instance.get_config.return_value = config
                mock_cli_instance.load_config.return_value = config
                mock_cli_config.return_value = mock_cli_instance
                
                mock_storage_instance = MagicMock()
                mock_storage_instance.load_config.return_value = config
                mock_storage_config.return_value = mock_storage_instance
                
                # Purge with cache
                result = runner.invoke(cli, ['purge', '--force'])
                assert result.exit_code == 0
                assert "Clearing base image cache" in result.output
            
            # Verify image removed
            assert not manager.image_exists("myapp:latest")
            
            # Verify cache cleared (directory should exist but be empty)
            assert cache_dir.exists()
            assert len(list(cache_dir.iterdir())) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
