"""Tests for build layers module."""

import pytest
from derpy.build.layers import LayerBuilder


class TestLayerBuilder:
    """Tests for LayerBuilder class."""
    
    def test_layer_builder_has_create_layer_from_directory(self):
        """Test LayerBuilder has create_layer_from_directory method."""
        assert hasattr(LayerBuilder, 'create_layer_from_directory')
        assert callable(getattr(LayerBuilder, 'create_layer_from_directory', None))
    
    def test_layer_builder_has_create_layer_from_tarball(self):
        """Test LayerBuilder has create_layer_from_tarball method."""
        assert hasattr(LayerBuilder, 'create_layer_from_tarball')
        assert callable(getattr(LayerBuilder, 'create_layer_from_tarball', None))
    
    def test_layer_builder_has_compute_layer_digest(self):
        """Test LayerBuilder has compute_layer_digest method."""
        assert hasattr(LayerBuilder, 'compute_layer_digest')
        assert callable(getattr(LayerBuilder, 'compute_layer_digest', None))
    
    def test_layer_builder_has_compute_diff_id(self):
        """Test LayerBuilder has compute_diff_id method."""
        assert hasattr(LayerBuilder, 'compute_diff_id')
        assert callable(getattr(LayerBuilder, 'compute_diff_id', None))
    
    def test_layer_builder_has_validate_layer(self):
        """Test LayerBuilder has validate_layer method."""
        assert hasattr(LayerBuilder, 'validate_layer')
        assert callable(getattr(LayerBuilder, 'validate_layer', None))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
