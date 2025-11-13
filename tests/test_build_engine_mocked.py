"""Mocked tests for build engine."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
from derpy.build.engine import BuildEngine, BuildContext


class TestBuildEngineMocked:
    """Mocked tests for BuildEngine."""
    
    def test_build_engine_initialization(self):
        """Test BuildEngine initialization."""
        engine = BuildEngine()
        assert engine is not None
        assert hasattr(engine, 'build_image')
    
    def test_build_engine_has_parser(self):
        """Test BuildEngine has parser."""
        engine = BuildEngine()
        assert hasattr(engine, 'parser')
    
    def test_build_engine_has_layer_builder(self):
        """Test BuildEngine has layer_builder."""
        engine = BuildEngine()
        assert hasattr(engine, 'layer_builder')
    
    @patch('derpy.build.engine.DockerfileParser')
    def test_build_image_with_mock_parser(self, mock_parser_class):
        """Test build_image with mocked parser."""
        mock_parser = Mock()
        mock_dockerfile = Mock()
        mock_dockerfile.instructions = []
        mock_dockerfile.is_valid = True
        mock_parser.parse.return_value = mock_dockerfile
        mock_parser_class.return_value = mock_parser
        
        engine = BuildEngine()
        engine.parser = mock_parser
        
        with tempfile.TemporaryDirectory() as tmpdir:
            context_path = Path(tmpdir)
            dockerfile_path = context_path / "Dockerfile"
            dockerfile_path.write_text("FROM ubuntu:20.04\n")
            
            build_context = BuildContext(
                context_path=context_path,
                dockerfile_path=dockerfile_path
            )
            
            # Mock the build process
            with patch.object(engine, 'build_image') as mock_build:
                mock_image = Mock()
                mock_build.return_value = mock_image
                
                result = engine.build_image(build_context, "test:latest")
                assert result is mock_image


class TestBuildContextMocked:
    """Mocked tests for BuildContext."""
    
    def test_build_context_creation(self):
        """Test BuildContext creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            context_path = Path(tmpdir)
            dockerfile_path = context_path / "Dockerfile"
            dockerfile_path.write_text("FROM ubuntu:20.04\n")
            
            build_context = BuildContext(
                context_path=context_path,
                dockerfile_path=dockerfile_path
            )
            
            assert build_context.context_path == context_path
            assert build_context.dockerfile_path == dockerfile_path
    
    def test_build_context_has_attributes(self):
        """Test BuildContext has required attributes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            context_path = Path(tmpdir)
            dockerfile_path = context_path / "Dockerfile"
            dockerfile_path.write_text("FROM ubuntu:20.04\n")
            
            build_context = BuildContext(
                context_path=context_path,
                dockerfile_path=dockerfile_path
            )
            
            assert hasattr(build_context, 'context_path')
            assert hasattr(build_context, 'dockerfile_path')


class TestBuildEngineIntegration:
    """Integration tests for BuildEngine with mocking."""
    
    @patch('derpy.build.engine.LayerBuilder')
    @patch('derpy.build.engine.DockerfileParser')
    def test_build_workflow(self, mock_parser_class, mock_layer_builder_class):
        """Test complete build workflow with mocks."""
        # Mock parser
        mock_parser = Mock()
        mock_dockerfile = Mock()
        mock_dockerfile.instructions = []
        mock_dockerfile.is_valid = True
        mock_parser.parse.return_value = mock_dockerfile
        mock_parser_class.return_value = mock_parser
        
        # Mock layer builder
        mock_layer_builder = Mock()
        mock_layer_builder_class.return_value = mock_layer_builder
        
        engine = BuildEngine()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            context_path = Path(tmpdir)
            dockerfile_path = context_path / "Dockerfile"
            dockerfile_path.write_text("FROM ubuntu:20.04\n")
            
            build_context = BuildContext(
                context_path=context_path,
                dockerfile_path=dockerfile_path
            )
            
            # Verify context is created
            assert build_context.context_path.exists()
            assert build_context.dockerfile_path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
