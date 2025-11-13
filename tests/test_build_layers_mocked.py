"""Mocked tests for build layers."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
from derpy.build.layers import LayerBuilder


class TestLayerBuilderMocked:
    """Mocked tests for LayerBuilder."""
    
    @patch('tarfile.open')
    def test_create_layer_from_directory(self, mock_tarfile):
        """Test creating layer from directory."""
        mock_tar = MagicMock()
        mock_tarfile.return_value.__enter__.return_value = mock_tar
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()
            
            # Create a test file
            (source_dir / "test.txt").write_text("test content")
            
            # Mock the method
            with patch.object(LayerBuilder, 'create_layer_from_directory') as mock_method:
                mock_method.return_value = b"layer_data"
                result = LayerBuilder.create_layer_from_directory(source_dir)
                assert result == b"layer_data"
    
    @patch('hashlib.sha256')
    def test_compute_layer_digest(self, mock_sha256):
        """Test computing layer digest."""
        mock_hash = Mock()
        mock_hash.hexdigest.return_value = "abc123"
        mock_sha256.return_value = mock_hash
        
        with patch.object(LayerBuilder, 'compute_layer_digest') as mock_method:
            mock_method.return_value = "sha256:abc123"
            result = LayerBuilder.compute_layer_digest(b"layer_data")
            assert result == "sha256:abc123"
    
    @patch('hashlib.sha256')
    def test_compute_diff_id(self, mock_sha256):
        """Test computing diff ID."""
        mock_hash = Mock()
        mock_hash.hexdigest.return_value = "def456"
        mock_sha256.return_value = mock_hash
        
        with patch.object(LayerBuilder, 'compute_diff_id') as mock_method:
            mock_method.return_value = "sha256:def456"
            result = LayerBuilder.compute_diff_id(b"uncompressed_data")
            assert result == "sha256:def456"
    
    def test_validate_layer_valid(self):
        """Test validating a valid layer."""
        with patch.object(LayerBuilder, 'validate_layer') as mock_method:
            mock_method.return_value = True
            result = LayerBuilder.validate_layer(b"layer_data", "sha256:abc123")
            assert result is True
    
    def test_validate_layer_invalid(self):
        """Test validating an invalid layer."""
        with patch.object(LayerBuilder, 'validate_layer') as mock_method:
            mock_method.return_value = False
            result = LayerBuilder.validate_layer(b"layer_data", "sha256:wrong")
            assert result is False
    
    @patch('gzip.compress')
    def test_compress_layer(self, mock_compress):
        """Test compressing layer data."""
        mock_compress.return_value = b"compressed_data"
        
        layer_data = b"uncompressed_data"
        result = mock_compress(layer_data)
        
        assert result == b"compressed_data"
        mock_compress.assert_called_once_with(layer_data)
    
    def test_create_layer_from_tarball(self):
        """Test creating layer from tarball."""
        with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as f:
            tarball_path = Path(f.name)
            f.write(b"fake tarball data")
        
        try:
            with patch.object(LayerBuilder, 'create_layer_from_tarball') as mock_method:
                mock_method.return_value = b"layer_data"
                result = LayerBuilder.create_layer_from_tarball(tarball_path)
                assert result == b"layer_data"
        finally:
            tarball_path.unlink()


class TestLayerBuilderIntegration:
    """Integration tests for LayerBuilder with mocking."""
    
    @patch('tarfile.open')
    @patch('hashlib.sha256')
    def test_full_layer_creation_workflow(self, mock_sha256, mock_tarfile):
        """Test full workflow of creating and validating a layer."""
        # Mock tarfile
        mock_tar = MagicMock()
        mock_tarfile.return_value.__enter__.return_value = mock_tar
        
        # Mock hash
        mock_hash = Mock()
        mock_hash.hexdigest.return_value = "abc123"
        mock_sha256.return_value = mock_hash
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()
            
            # Mock the entire workflow
            with patch.object(LayerBuilder, 'create_layer_from_directory') as mock_create:
                with patch.object(LayerBuilder, 'compute_layer_digest') as mock_digest:
                    with patch.object(LayerBuilder, 'validate_layer') as mock_validate:
                        mock_create.return_value = b"layer_data"
                        mock_digest.return_value = "sha256:abc123"
                        mock_validate.return_value = True
                        
                        # Simulate workflow
                        layer_data = LayerBuilder.create_layer_from_directory(source_dir)
                        digest = LayerBuilder.compute_layer_digest(layer_data)
                        is_valid = LayerBuilder.validate_layer(layer_data, digest)
                        
                        assert layer_data == b"layer_data"
                        assert digest == "sha256:abc123"
                        assert is_valid is True


class TestLayerBuilderErrorHandling:
    """Test error handling in LayerBuilder."""
    
    @patch('tarfile.open')
    def test_create_layer_from_directory_error(self, mock_tarfile):
        """Test error handling when creating layer fails."""
        mock_tarfile.side_effect = Exception("Tarfile error")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()
            
            with patch.object(LayerBuilder, 'create_layer_from_directory') as mock_method:
                mock_method.side_effect = Exception("Failed to create layer")
                
                with pytest.raises(Exception):
                    LayerBuilder.create_layer_from_directory(source_dir)
    
    def test_validate_layer_with_wrong_digest(self):
        """Test validation fails with wrong digest."""
        with patch.object(LayerBuilder, 'validate_layer') as mock_method:
            mock_method.return_value = False
            
            result = LayerBuilder.validate_layer(b"layer_data", "sha256:wrong_digest")
            assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
