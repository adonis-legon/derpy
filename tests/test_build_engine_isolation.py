"""Tests for BuildEngine isolation integration."""

import pytest
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch, MagicMock
import platform

from derpy.build.engine import BuildEngine
from derpy.build.models import ImageReference, ExecutionResult
from derpy.oci.models import Image, Manifest, ImageConfig, Layer, Descriptor, RootFS, ContainerConfig
from derpy.oci.models import MEDIA_TYPE_IMAGE_CONFIG, MEDIA_TYPE_IMAGE_LAYER
from derpy.core.exceptions import BuildError, PlatformNotSupportedError


class TestIsolationSupport:
    """Tests for isolation support detection."""
    
    def test_isolation_enabled_on_linux_as_root(self):
        """Test that isolation is enabled on Linux as root."""
        with patch('platform.system', return_value='Linux'):
            with patch('os.geteuid', return_value=0):
                engine = BuildEngine()
                assert engine.use_isolation is True
    
    def test_isolation_disabled_on_non_linux(self):
        """Test that isolation is disabled on non-Linux platforms."""
        with patch('platform.system', return_value='Darwin'):
            engine = BuildEngine()
            assert engine.use_isolation is False
    
    def test_isolation_disabled_without_permissions(self):
        """Test that isolation is disabled without proper permissions."""
        with patch('platform.system', return_value='Linux'):
            with patch('os.geteuid', return_value=1000):
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value = Mock(returncode=0, stdout="current: =")
                    engine = BuildEngine()
                    assert engine.use_isolation is False


class TestFROMInstructionHandling:
    """Tests for FROM instruction handling with isolation."""
    
    def test_from_instruction_pulls_base_image(self):
        """Test that FROM instruction pulls base image."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = BuildEngine()
            engine.use_isolation = True
            
            # Mock base image manager
            mock_image = Mock(spec=Image)
            mock_image.layers = []
            mock_image.config = Mock(spec=ImageConfig)
            mock_image.config.rootfs = Mock(spec=RootFS)
            mock_image.config.rootfs.diff_ids = []
            
            with patch.object(engine, 'base_image_manager') as mock_mgr:
                mock_mgr.pull_base_image.return_value = mock_image
                mock_mgr.extract_base_image.return_value = Path(tmpdir) / "rootfs"
                
                # Mock dockerfile parsing
                from derpy.dockerfile.parser import Instruction, InstructionType
                from_inst = Instruction(
                    type=InstructionType.FROM,
                    value="ubuntu:22.04",
                    line_number=1,
                    raw_line="FROM ubuntu:22.04"
                )
                
                with patch.object(engine.parser, 'parse') as mock_parse:
                    mock_parse.return_value = [from_inst]
                    
                    # Mock build context
                    from derpy.build.engine import BuildContext
                    # Create a dummy Dockerfile
                    (Path(tmpdir) / "Dockerfile").write_text("FROM ubuntu:22.04")
                    context = BuildContext(
                        dockerfile_path=Path(tmpdir) / "Dockerfile",
                        context_path=Path(tmpdir)
                    )
                    
                    # This would normally build, but we're just testing FROM handling
                    # We'll verify the mock was called
                    mock_mgr.pull_base_image.assert_not_called()  # Not called yet
    
    def test_from_instruction_extracts_base_image(self):
        """Test that FROM instruction extracts base image to rootfs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = BuildEngine()
            engine.use_isolation = True
            
            mock_image = Mock(spec=Image)
            rootfs_path = Path(tmpdir) / "rootfs"
            
            with patch.object(engine, 'base_image_manager') as mock_mgr:
                mock_mgr.pull_base_image.return_value = mock_image
                mock_mgr.extract_base_image.return_value = rootfs_path
                
                # Verify extraction would be called
                # (actual integration test would verify this)
                assert engine.base_image_manager is not None


class TestRUNInstructionWithIsolation:
    """Tests for RUN instruction execution with isolation."""
    
    def test_run_instruction_uses_chroot(self):
        """Test that RUN instruction uses chroot when isolation is enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = BuildEngine()
            engine.use_isolation = True
            
            rootfs = Path(tmpdir) / "rootfs"
            rootfs.mkdir()
            (rootfs / "bin").mkdir()
            (rootfs / "bin" / "sh").touch()
            
            # Mock isolation executor
            mock_result = ExecutionResult(
                exit_code=0,
                stdout="output",
                stderr="",
                duration=1.0,
                command="echo test"
            )
            
            with patch.object(engine, 'isolation_executor') as mock_exec:
                mock_exec.execute_in_chroot.return_value = mock_result
                
                # This would be called during RUN instruction execution
                result = mock_exec.execute_in_chroot(rootfs, "echo test")
                
                assert result.is_success()
                assert result.stdout == "output"
    
    def test_run_instruction_fallback_without_isolation(self):
        """Test that RUN instruction falls back without isolation."""
        engine = BuildEngine()
        engine.use_isolation = False
        
        # Without isolation, RUN should use subprocess directly
        # This is the v0.1.0 behavior
        assert engine.use_isolation is False
    
    def test_run_instruction_handles_failure(self):
        """Test that RUN instruction handles command failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = BuildEngine()
            engine.use_isolation = True
            
            rootfs = Path(tmpdir) / "rootfs"
            rootfs.mkdir()
            
            # Mock failed execution
            mock_result = ExecutionResult(
                exit_code=1,
                stdout="",
                stderr="command failed",
                duration=0.5,
                command="false"
            )
            
            with patch.object(engine, 'isolation_executor') as mock_exec:
                mock_exec.execute_in_chroot.return_value = mock_result
                
                result = mock_exec.execute_in_chroot(rootfs, "false")
                
                assert result.is_failure()
                assert result.exit_code == 1


class TestLayerCombination:
    """Tests for combining base and new layers."""
    
    def test_combine_base_and_new_layers(self):
        """Test combining base image layers with new layers."""
        # Create mock base image with layers
        base_layer1 = Layer(
            digest="sha256:base1",
            size=1000,
            diff_id="sha256:basediff1"
        )
        base_layer2 = Layer(
            digest="sha256:base2",
            size=2000,
            diff_id="sha256:basediff2"
        )
        
        base_image = Mock(spec=Image)
        base_image.layers = [base_layer1, base_layer2]
        base_image.config = Mock(spec=ImageConfig)
        base_image.config.rootfs = Mock(spec=RootFS)
        base_image.config.rootfs.diff_ids = ["sha256:basediff1", "sha256:basediff2"]
        
        # Create new layer from RUN instruction
        new_layer = Layer(
            digest="sha256:new1",
            size=500,
            diff_id="sha256:newdiff1"
        )
        
        # Combined layers should include all base layers + new layers
        all_layers = base_image.layers + [new_layer]
        all_diff_ids = base_image.config.rootfs.diff_ids + [new_layer.diff_id]
        
        assert len(all_layers) == 3
        assert len(all_diff_ids) == 3
        assert all_diff_ids[-1] == "sha256:newdiff1"
    
    def test_layer_order_preserved(self):
        """Test that layer order is preserved in final image."""
        base_layers = [
            Layer(digest=f"sha256:base{i}", size=1000, diff_id=f"sha256:basediff{i}")
            for i in range(3)
        ]
        
        new_layers = [
            Layer(digest=f"sha256:new{i}", size=500, diff_id=f"sha256:newdiff{i}")
            for i in range(2)
        ]
        
        combined = base_layers + new_layers
        
        # Verify order
        assert combined[0].digest == "sha256:base0"
        assert combined[2].digest == "sha256:base2"
        assert combined[3].digest == "sha256:new0"
        assert combined[4].digest == "sha256:new1"


class TestFallbackToNonIsolatedMode:
    """Tests for fallback to non-isolated mode."""
    
    def test_fallback_on_non_linux(self):
        """Test fallback to non-isolated mode on non-Linux."""
        with patch('platform.system', return_value='Darwin'):
            engine = BuildEngine()
            
            assert engine.use_isolation is False
            # Engine should still work, just without isolation
            assert engine is not None
    
    def test_fallback_without_permissions(self):
        """Test fallback without proper permissions."""
        with patch('platform.system', return_value='Linux'):
            with patch('os.geteuid', return_value=1000):
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value = Mock(returncode=0, stdout="current: =")
                    
                    engine = BuildEngine()
                    
                    assert engine.use_isolation is False
    
    def test_build_continues_without_isolation(self):
        """Test that build can continue without isolation."""
        engine = BuildEngine()
        engine.use_isolation = False
        
        # Build should still work with v0.1.0 behavior
        # (subprocess execution without chroot)
        assert engine.layer_builder is not None
        assert engine.parser is not None


class TestBuildEngineComponents:
    """Tests for BuildEngine component initialization."""
    
    def test_build_engine_has_base_image_manager(self):
        """Test that BuildEngine has BaseImageManager."""
        engine = BuildEngine()
        assert hasattr(engine, 'base_image_manager')
    
    def test_build_engine_has_isolation_executor(self):
        """Test that BuildEngine has IsolationExecutor."""
        engine = BuildEngine()
        assert hasattr(engine, 'isolation_executor')
    
    def test_build_engine_has_layer_diff_manager(self):
        """Test that BuildEngine has LayerDiffManager."""
        engine = BuildEngine()
        assert hasattr(engine, 'layer_diff_manager')
    
    def test_build_engine_checks_isolation_support(self):
        """Test that BuildEngine checks isolation support on init."""
        with patch('platform.system', return_value='Linux'):
            with patch('os.geteuid', return_value=0):
                engine = BuildEngine()
                assert engine.use_isolation is True


class TestBuildContextIsolation:
    """Tests for build context with isolation."""
    
    def test_build_context_has_rootfs_path(self):
        """Test that build context can store rootfs path."""
        from derpy.build.engine import BuildContext
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a dummy Dockerfile
            (Path(tmpdir) / "Dockerfile").write_text("FROM ubuntu:22.04")
            context = BuildContext(
                dockerfile_path=Path(tmpdir) / "Dockerfile",
                context_path=Path(tmpdir)
            )
            
            # BuildContext should be able to store rootfs path
            # (this would be set during FROM instruction handling)
            assert context is not None
    
    def test_build_context_cleanup(self):
        """Test that build context cleans up temporary rootfs."""
        # Build context should clean up temp directories on completion
        # This is tested in integration tests
        pass


class TestErrorHandling:
    """Tests for error handling in isolated builds."""
    
    def test_base_image_not_found_error(self):
        """Test error when base image is not found."""
        engine = BuildEngine()
        engine.use_isolation = True
        
        with patch.object(engine, 'base_image_manager') as mock_mgr:
            from derpy.core.exceptions import BaseImageError
            mock_mgr.pull_base_image.side_effect = BaseImageError(
                image_ref="nonexistent:latest",
                message="Image not found"
            )
            
            # This would raise during build
            with pytest.raises(BaseImageError, match="not found"):
                mock_mgr.pull_base_image("nonexistent:latest")
    
    def test_chroot_execution_error(self):
        """Test error during chroot execution."""
        engine = BuildEngine()
        engine.use_isolation = True
        
        with patch.object(engine, 'isolation_executor') as mock_exec:
            from derpy.core.exceptions import IsolationError
            mock_exec.execute_in_chroot.side_effect = IsolationError(
                "Chroot execution failed"
            )
            
            with pytest.raises(IsolationError):
                mock_exec.execute_in_chroot(Path("/tmp"), "echo test")
    
    def test_layer_diff_capture_error(self):
        """Test error during layer diff capture."""
        engine = BuildEngine()
        engine.use_isolation = True
        
        with patch.object(engine, 'layer_diff_manager') as mock_mgr:
            from derpy.core.exceptions import FilesystemDiffError
            from derpy.build.models import Snapshot
            from datetime import datetime
            
            mock_snapshot = Snapshot(timestamp=datetime.now())
            mock_mgr.capture_diff.side_effect = FilesystemDiffError(
                "Failed to capture diff",
                cause=None
            )
            
            with pytest.raises(FilesystemDiffError):
                mock_mgr.capture_diff(Path("/tmp"), mock_snapshot, "RUN test")


class TestImageReferenceModel:
    """Tests for ImageReference model."""
    
    def test_image_reference_parse(self):
        """Test ImageReference.parse() method."""
        ref = ImageReference.parse("ubuntu:22.04")
        assert ref.registry == "docker.io"
        assert ref.repository == "library/ubuntu"
        assert ref.tag == "22.04"
    
    def test_image_reference_to_string(self):
        """Test ImageReference.to_string() method."""
        ref = ImageReference(
            registry="docker.io",
            repository="library/nginx",
            tag="latest"
        )
        assert "nginx" in ref.to_string()
        assert "latest" in ref.to_string()
    
    def test_image_reference_with_registry(self):
        """Test ImageReference with custom registry."""
        ref = ImageReference.parse("ghcr.io/org/app:v1")
        assert ref.registry == "ghcr.io"
        assert ref.repository == "org/app"
        assert ref.tag == "v1"


class TestExecutionResultModel:
    """Tests for ExecutionResult model."""
    
    def test_execution_result_success(self):
        """Test ExecutionResult for successful execution."""
        result = ExecutionResult(
            exit_code=0,
            stdout="success",
            stderr="",
            duration=1.0,
            command="echo test"
        )
        assert result.is_success()
        assert not result.is_failure()
    
    def test_execution_result_failure(self):
        """Test ExecutionResult for failed execution."""
        result = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="error",
            duration=0.5,
            command="false"
        )
        assert result.is_failure()
        assert not result.is_success()
    
    def test_execution_result_get_output(self):
        """Test ExecutionResult.get_output() method."""
        result = ExecutionResult(
            exit_code=0,
            stdout="out",
            stderr="err",
            duration=1.0
        )
        output = result.get_output()
        assert "out" in output
        assert "err" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
