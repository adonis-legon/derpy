"""Layer creation and management for container images."""

from pathlib import Path
from typing import Optional
import tarfile
import gzip
import hashlib
import io
import tempfile

from derpy.oci.models import Layer, MEDIA_TYPE_IMAGE_LAYER
from derpy.build.exceptions import BuildError


class LayerBuilder:
    """Builder for creating OCI-compliant filesystem layers."""
    
    @staticmethod
    def create_layer_from_directory(directory: Path, layer_name: Optional[str] = None) -> Layer:
        """Create a tar-gzip layer from a directory.
        
        Args:
            directory: Directory containing the layer filesystem
            layer_name: Optional name for the layer (for debugging)
        
        Returns:
            Layer object with digest, size, and content path
        
        Raises:
            BuildError: If layer creation fails
        """
        if not directory.exists():
            raise BuildError(f"Layer directory does not exist: {directory}")
        
        if not directory.is_dir():
            raise BuildError(f"Layer path is not a directory: {directory}")
        
        # Create tar.gz in memory first to compute digests
        tar_buffer = io.BytesIO()
        
        try:
            # Create tar archive
            with tarfile.open(fileobj=tar_buffer, mode='w', format=tarfile.PAX_FORMAT) as tar:
                # Add all files from directory
                for item in directory.rglob('*'):
                    if item.is_file():
                        arcname = item.relative_to(directory)
                        tar.add(item, arcname=str(arcname))
            
            # Get uncompressed tar data
            tar_data = tar_buffer.getvalue()
            
            # Compute diff_id (SHA256 of uncompressed tar)
            diff_id = f"sha256:{hashlib.sha256(tar_data).hexdigest()}"
            
            # Compress with gzip
            gzip_buffer = io.BytesIO()
            with gzip.GzipFile(fileobj=gzip_buffer, mode='wb') as gz:
                gz.write(tar_data)
            
            # Get compressed data
            compressed_data = gzip_buffer.getvalue()
            
            # Compute digest (SHA256 of compressed tar.gz)
            digest = f"sha256:{hashlib.sha256(compressed_data).hexdigest()}"
            
            # Write to temporary file
            temp_file = tempfile.NamedTemporaryFile(
                mode='wb',
                suffix='.tar.gz',
                delete=False,
                prefix='derpy_layer_'
            )
            temp_file.write(compressed_data)
            temp_file.close()
            
            # Create Layer object
            layer = Layer(
                digest=digest,
                size=len(compressed_data),
                media_type=MEDIA_TYPE_IMAGE_LAYER,
                content_path=Path(temp_file.name),
                diff_id=diff_id
            )
            
            return layer
            
        except Exception as e:
            raise BuildError(f"Failed to create layer: {e}")
    
    @staticmethod
    def create_layer_from_tarball(tarball_path: Path) -> Layer:
        """Create a layer from an existing tar.gz file.
        
        Args:
            tarball_path: Path to tar.gz file
        
        Returns:
            Layer object with digest, size, and content path
        
        Raises:
            BuildError: If layer creation fails
        """
        if not tarball_path.exists():
            raise BuildError(f"Tarball does not exist: {tarball_path}")
        
        if not tarball_path.is_file():
            raise BuildError(f"Tarball path is not a file: {tarball_path}")
        
        try:
            # Read compressed data
            compressed_data = tarball_path.read_bytes()
            
            # Compute digest (SHA256 of compressed tar.gz)
            digest = f"sha256:{hashlib.sha256(compressed_data).hexdigest()}"
            
            # Decompress to compute diff_id
            with gzip.open(tarball_path, 'rb') as gz:
                tar_data = gz.read()
            
            # Compute diff_id (SHA256 of uncompressed tar)
            diff_id = f"sha256:{hashlib.sha256(tar_data).hexdigest()}"
            
            # Create Layer object
            layer = Layer(
                digest=digest,
                size=len(compressed_data),
                media_type=MEDIA_TYPE_IMAGE_LAYER,
                content_path=tarball_path,
                diff_id=diff_id
            )
            
            return layer
            
        except Exception as e:
            raise BuildError(f"Failed to create layer from tarball: {e}")
    
    @staticmethod
    def compute_layer_digest(layer_path: Path) -> str:
        """Compute SHA256 digest of a layer file.
        
        Args:
            layer_path: Path to layer tar.gz file
        
        Returns:
            Digest string in format "sha256:..."
        
        Raises:
            BuildError: If digest computation fails
        """
        if not layer_path.exists():
            raise BuildError(f"Layer file does not exist: {layer_path}")
        
        try:
            data = layer_path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            return f"sha256:{digest}"
        except Exception as e:
            raise BuildError(f"Failed to compute layer digest: {e}")
    
    @staticmethod
    def compute_diff_id(layer_path: Path) -> str:
        """Compute diff_id (uncompressed digest) of a layer.
        
        Args:
            layer_path: Path to layer tar.gz file
        
        Returns:
            Diff ID string in format "sha256:..."
        
        Raises:
            BuildError: If diff_id computation fails
        """
        if not layer_path.exists():
            raise BuildError(f"Layer file does not exist: {layer_path}")
        
        try:
            # Decompress and compute digest
            with gzip.open(layer_path, 'rb') as gz:
                tar_data = gz.read()
            
            diff_id = hashlib.sha256(tar_data).hexdigest()
            return f"sha256:{diff_id}"
        except Exception as e:
            raise BuildError(f"Failed to compute diff_id: {e}")
    
    @staticmethod
    def validate_layer(layer: Layer) -> bool:
        """Validate a layer's integrity.
        
        Args:
            layer: Layer to validate
        
        Returns:
            True if valid, False otherwise
        """
        if not layer.content_path:
            return False
        
        if not layer.content_path.exists():
            return False
        
        try:
            # Verify digest matches file content
            computed_digest = LayerBuilder.compute_layer_digest(layer.content_path)
            if computed_digest != layer.digest:
                return False
            
            # Verify diff_id if present
            if layer.diff_id:
                computed_diff_id = LayerBuilder.compute_diff_id(layer.content_path)
                if computed_diff_id != layer.diff_id:
                    return False
            
            # Verify size
            actual_size = layer.content_path.stat().st_size
            if actual_size != layer.size:
                return False
            
            return True
            
        except Exception:
            return False
