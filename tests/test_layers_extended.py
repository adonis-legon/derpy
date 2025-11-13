"""Additional tests for LayerBuilder to increase coverage."""

import pytest
from pathlib import Path
import tempfile
import gzip
import tarfile
from derpy.build.layers import LayerBuilder
from derpy.build.exceptions import BuildError
from derpy.oci.models import Layer, MEDIA_TYPE_IMAGE_LAYER


class TestLayerBuilderErrors:
    """Test error handling in LayerBuilder."""
    
    def test_create_layer_from_nonexistent_directory(self):
        """Test creating layer from non-existent directory raises error."""
        non_existent = Path("/nonexistent/directory")
        
        with pytest.raises(BuildError, match="does not exist"):
            LayerBuilder.create_layer_from_directory(non_existent)
    
    def test_create_layer_from_file_not_directory(self):
        """Test creating layer from file instead of directory raises error."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            file_path = Path(f.name)
        
        try:
            with pytest.raises(BuildError, match="not a directory"):
                LayerBuilder.create_layer_from_directory(file_path)
        finally:
            file_path.unlink()
    
    def test_create_layer_from_nonexistent_tarball(self):
        """Test creating layer from non-existent tarball raises error."""
        non_existent = Path("/nonexistent/tarball.tar.gz")
        
        with pytest.raises(BuildError, match="does not exist"):
            LayerBuilder.create_layer_from_tarball(non_existent)
    
    def test_create_layer_from_directory_not_file(self):
        """Test creating layer from tarball that is a directory raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)
            
            with pytest.raises(BuildError, match="not a file"):
                LayerBuilder.create_layer_from_tarball(dir_path)
    
    def test_compute_digest_nonexistent_file(self):
        """Test computing digest of non-existent file raises error."""
        non_existent = Path("/nonexistent/layer.tar.gz")
        
        with pytest.raises(BuildError, match="does not exist"):
            LayerBuilder.compute_layer_digest(non_existent)
    
    def test_compute_diff_id_nonexistent_file(self):
        """Test computing diff_id of non-existent file raises error."""
        non_existent = Path("/nonexistent/layer.tar.gz")
        
        with pytest.raises(BuildError, match="does not exist"):
            LayerBuilder.compute_diff_id(non_existent)
    
    def test_validate_layer_no_content_path(self):
        """Test validating layer without content_path returns False."""
        layer = Layer(
            digest="sha256:abc123",
            size=100,
            media_type=MEDIA_TYPE_IMAGE_LAYER,
            content_path=None
        )
        
        assert LayerBuilder.validate_layer(layer) is False
    
    def test_validate_layer_nonexistent_content_path(self):
        """Test validating layer with non-existent content_path returns False."""
        layer = Layer(
            digest="sha256:abc123",
            size=100,
            media_type=MEDIA_TYPE_IMAGE_LAYER,
            content_path=Path("/nonexistent/layer.tar.gz")
        )
        
        assert LayerBuilder.validate_layer(layer) is False


class TestLayerBuilderValidation:
    """Test layer validation functionality."""
    
    def test_validate_layer_wrong_digest(self):
        """Test validating layer with wrong digest returns False."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tar.gz') as f:
            f.write(b"test data")
            layer_path = Path(f.name)
        
        try:
            layer = Layer(
                digest="sha256:wrongdigest",
                size=9,
                media_type=MEDIA_TYPE_IMAGE_LAYER,
                content_path=layer_path
            )
            
            assert LayerBuilder.validate_layer(layer) is False
        finally:
            layer_path.unlink()
    
    def test_validate_layer_wrong_size(self):
        """Test validating layer with wrong size returns False."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tar.gz') as f:
            data = b"test data"
            f.write(data)
            layer_path = Path(f.name)
        
        try:
            import hashlib
            digest = f"sha256:{hashlib.sha256(data).hexdigest()}"
            
            layer = Layer(
                digest=digest,
                size=999,  # Wrong size
                media_type=MEDIA_TYPE_IMAGE_LAYER,
                content_path=layer_path
            )
            
            assert LayerBuilder.validate_layer(layer) is False
        finally:
            layer_path.unlink()
    
    def test_validate_layer_wrong_diff_id(self):
        """Test validating layer with wrong diff_id returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple tar.gz file
            tar_path = Path(tmpdir) / "test.tar.gz"
            with gzip.open(tar_path, 'wb') as gz:
                gz.write(b"test tar content")
            
            import hashlib
            data = tar_path.read_bytes()
            digest = f"sha256:{hashlib.sha256(data).hexdigest()}"
            
            layer = Layer(
                digest=digest,
                size=len(data),
                media_type=MEDIA_TYPE_IMAGE_LAYER,
                content_path=tar_path,
                diff_id="sha256:wrongdiffid"
            )
            
            assert LayerBuilder.validate_layer(layer) is False


class TestLayerBuilderRealOperations:
    """Test real layer operations."""
    
    def test_create_layer_from_empty_directory(self):
        """Test creating layer from empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "empty"
            source_dir.mkdir()
            
            layer = LayerBuilder.create_layer_from_directory(source_dir)
            
            assert layer is not None
            assert layer.digest.startswith("sha256:")
            assert layer.size > 0
            assert layer.content_path.exists()
            
            # Cleanup
            layer.content_path.unlink()
    
    def test_create_layer_from_directory_with_files(self):
        """Test creating layer from directory with files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()
            
            # Create test files
            (source_dir / "file1.txt").write_text("content1")
            (source_dir / "file2.txt").write_text("content2")
            
            layer = LayerBuilder.create_layer_from_directory(source_dir)
            
            assert layer is not None
            assert layer.digest.startswith("sha256:")
            assert layer.diff_id.startswith("sha256:")
            assert layer.size > 0
            assert layer.content_path.exists()
            assert layer.media_type == MEDIA_TYPE_IMAGE_LAYER
            
            # Cleanup
            layer.content_path.unlink()
    
    def test_compute_layer_digest_real_file(self):
        """Test computing digest of real file."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tar.gz') as f:
            f.write(b"test layer data")
            layer_path = Path(f.name)
        
        try:
            digest = LayerBuilder.compute_layer_digest(layer_path)
            
            assert digest.startswith("sha256:")
            assert len(digest) == 71  # "sha256:" + 64 hex chars
        finally:
            layer_path.unlink()
    
    def test_compute_diff_id_real_file(self):
        """Test computing diff_id of real gzipped file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tar_path = Path(tmpdir) / "test.tar.gz"
            
            # Create a gzipped file
            with gzip.open(tar_path, 'wb') as gz:
                gz.write(b"uncompressed tar data")
            
            diff_id = LayerBuilder.compute_diff_id(tar_path)
            
            assert diff_id.startswith("sha256:")
            assert len(diff_id) == 71
    
    def test_create_layer_from_tarball_real(self):
        """Test creating layer from real tarball."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a tar.gz file
            tar_path = Path(tmpdir) / "test.tar.gz"
            
            # Create tar first, then compress
            tar_buffer_path = Path(tmpdir) / "test.tar"
            with tarfile.open(tar_buffer_path, 'w') as tar:
                # Add a simple file
                info = tarfile.TarInfo(name="test.txt")
                info.size = 0
                tar.addfile(info)
            
            # Compress the tar file
            with open(tar_buffer_path, 'rb') as f_in:
                with gzip.open(tar_path, 'wb') as f_out:
                    f_out.write(f_in.read())
            
            layer = LayerBuilder.create_layer_from_tarball(tar_path)
            
            assert layer is not None
            assert layer.digest.startswith("sha256:")
            assert layer.diff_id.startswith("sha256:")
            assert layer.size > 0
            assert layer.content_path == tar_path


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
