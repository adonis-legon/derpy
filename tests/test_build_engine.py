"""Tests for build engine."""

import pytest
from derpy.build import BuildEngine, BuildContext, BuildError, LayerBuilder, InstructionPipeline


class TestBuildEngineImports:
    """Tests for build engine module imports."""
    
    def test_imports_successful(self):
        """Test that all build module imports are successful."""
        assert BuildEngine is not None
        assert BuildContext is not None
        assert BuildError is not None
        assert LayerBuilder is not None
        assert InstructionPipeline is not None
    
    def test_build_engine_instantiation(self):
        """Test creating BuildEngine instance."""
        engine = BuildEngine()
        assert engine is not None
        assert hasattr(engine, 'build_image')
        assert hasattr(engine, 'layer_builder')
        assert hasattr(engine, 'parser')
    
    def test_build_engine_has_required_methods(self):
        """Test BuildEngine has required methods."""
        engine = BuildEngine()
        assert callable(getattr(engine, 'build_image', None))
        assert hasattr(engine, 'layer_builder')
        assert hasattr(engine, 'parser')


class TestLayerBuilder:
    """Tests for LayerBuilder."""
    
    def test_layer_builder_has_required_methods(self):
        """Test LayerBuilder has required static methods."""
        assert hasattr(LayerBuilder, 'create_layer_from_directory')
        assert hasattr(LayerBuilder, 'create_layer_from_tarball')
        assert hasattr(LayerBuilder, 'compute_layer_digest')
        assert hasattr(LayerBuilder, 'compute_diff_id')
        assert hasattr(LayerBuilder, 'validate_layer')
    
    def test_layer_builder_methods_callable(self):
        """Test LayerBuilder methods are callable."""
        assert callable(getattr(LayerBuilder, 'create_layer_from_directory', None))
        assert callable(getattr(LayerBuilder, 'create_layer_from_tarball', None))
        assert callable(getattr(LayerBuilder, 'compute_layer_digest', None))
        assert callable(getattr(LayerBuilder, 'compute_diff_id', None))


class TestInstructionPipeline:
    """Tests for InstructionPipeline."""
    
    def test_instruction_pipeline_exists(self):
        """Test InstructionPipeline class exists."""
        assert InstructionPipeline is not None
    
    def test_instruction_pipeline_has_execute_method(self):
        """Test InstructionPipeline has execute method."""
        assert hasattr(InstructionPipeline, 'execute')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
