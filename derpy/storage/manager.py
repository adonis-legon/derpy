"""Image manager for local storage operations.

This module provides the ImageManager class for storing, retrieving, and
managing container images in the local repository.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import json
import shutil

from derpy.oci.models import Image, Manifest, ImageConfig
from derpy.oci.layout import OCILayoutManager
from derpy.core.config import ConfigManager
from derpy.core.platform import normalize_path
from derpy.core.exceptions import (
    StorageError,
    ImageNotFoundError,
    ImageValidationError,
    RepositoryError,
    BlobNotFoundError
)


@dataclass
class ImageMetadata:
    """Metadata for a stored image."""
    
    tag: str
    manifest_digest: str
    config_digest: str
    size: int
    created: str
    architecture: str
    os: str
    layers_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "tag": self.tag,
            "manifest_digest": self.manifest_digest,
            "config_digest": self.config_digest,
            "size": self.size,
            "created": self.created,
            "architecture": self.architecture,
            "os": self.os,
            "layers_count": self.layers_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImageMetadata":
        """Create from dictionary during JSON deserialization."""
        return cls(
            tag=data["tag"],
            manifest_digest=data["manifest_digest"],
            config_digest=data["config_digest"],
            size=data["size"],
            created=data["created"],
            architecture=data["architecture"],
            os=data["os"],
            layers_count=data["layers_count"]
        )


@dataclass
class ImageInfo:
    """Information about a local image for listing."""
    
    tag: str
    size: int
    created: str
    architecture: str
    os: str
    
    def __str__(self) -> str:
        """String representation for display."""
        # Format size in human-readable format
        size_str = self._format_size(self.size)
        # Normalize created date to ISO format YYYY-MM-DDTHH:mm:ss
        created_str = self._format_created(self.created)
        return f"{self.tag:<40} {size_str:<10} {created_str:<19} {self.architecture}/{self.os}"
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}TB"
    
    @staticmethod
    def _format_created(created: str) -> str:
        """Format created timestamp to ISO format YYYY-MM-DDTHH:mm:ss.
        
        Args:
            created: ISO timestamp string with varying precision
            
        Returns:
            Normalized timestamp string in format YYYY-MM-DDTHH:mm:ss
        """
        try:
            # Parse the ISO timestamp (handles various formats)
            dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
            # Format to consistent ISO format without microseconds and timezone
            return dt.strftime('%Y-%m-%dT%H:%M:%S')
        except (ValueError, AttributeError):
            # If parsing fails, return original truncated to 19 chars
            return created[:19] if len(created) >= 19 else created


class ImageManager:
    """Manages local image repository operations.
    
    Provides methods for storing, retrieving, and listing container images
    in the local OCI-compliant repository.
    """
    
    METADATA_FILE = "metadata.json"
    
    def __init__(self, repository_path: Optional[Path] = None):
        """Initialize ImageManager.
        
        Args:
            repository_path: Path to local repository. If None, uses config.
        """
        if repository_path is None:
            config_manager = ConfigManager()
            config = config_manager.load_config()
            repository_path = config.images_path
        
        self.repository_path = normalize_path(repository_path)
        self.metadata_path = self.repository_path / self.METADATA_FILE
        self.oci_layout = OCILayoutManager(self.repository_path)
        self.blobs_path = self.repository_path / "blobs" / "sha256"
        
        # Initialize repository structure
        self._initialize_repository()
    
    def _initialize_repository(self) -> None:
        """Initialize local repository structure.
        
        Creates the OCI layout and metadata file if they don't exist.
        
        Raises:
            StorageError: If initialization fails
        """
        try:
            # Create OCI layout
            self.oci_layout.create_layout()
            
            # Create metadata file if it doesn't exist
            if not self.metadata_path.exists():
                self._save_metadata({})
        except Exception as e:
            raise StorageError(f"Failed to initialize repository: {e}")
    
    def store_image(self, image: Image, tag: str) -> None:
        """Store an image in the local repository.
        
        Args:
            tag: Tag for the image (e.g., "myapp:latest")
            image: Image object to store
        
        Raises:
            StorageError: If storage fails
        """
        try:
            # Validate image
            validation_errors = image.validate()
            if validation_errors:
                raise StorageError(f"Image validation failed: {', '.join(validation_errors)}")
            
            # Store layers
            for layer in image.layers:
                if layer.content_path and layer.content_path.exists():
                    # Store layer blob
                    layer_descriptor = self.oci_layout.store_layer(layer.content_path)
                    # Verify digest matches
                    if layer_descriptor.digest != layer.digest:
                        raise StorageError(
                            f"Layer digest mismatch: expected {layer.digest}, "
                            f"got {layer_descriptor.digest}"
                        )
            
            # Store config
            config_descriptor = self.oci_layout.store_config(image.config)
            
            # Update manifest with stored config descriptor
            image.manifest.config = config_descriptor
            
            # Store manifest
            manifest_descriptor = self.oci_layout.store_manifest(image.manifest)
            
            # Add manifest to index with tag
            self.oci_layout.add_manifest_to_index(manifest_descriptor, tag)
            
            # Calculate total image size
            total_size = config_descriptor.size
            for layer in image.layers:
                total_size += layer.size
            
            # Store metadata
            metadata = ImageMetadata(
                tag=tag,
                manifest_digest=manifest_descriptor.digest,
                config_digest=config_descriptor.digest,
                size=total_size,
                created=image.config.created or datetime.now(timezone.utc).isoformat(),
                architecture=image.config.architecture,
                os=image.config.os,
                layers_count=len(image.layers)
            )
            
            self._add_image_metadata(tag, metadata)
            
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to store image '{tag}': {e}")
    
    def get_image(self, tag: str) -> Optional[Image]:
        """Retrieve an image from the local repository.
        
        Args:
            tag: Tag of the image to retrieve
        
        Returns:
            Image object or None if not found
        
        Raises:
            StorageError: If retrieval fails
        """
        try:
            # Get manifest descriptor by tag
            manifest_descriptor = self.oci_layout.get_manifest_by_tag(tag)
            if manifest_descriptor is None:
                return None
            
            # Load manifest
            manifest = self.oci_layout.get_manifest(manifest_descriptor.digest)
            if manifest is None:
                raise StorageError(f"Manifest not found for tag '{tag}'")
            
            # Load config
            if manifest.config is None:
                raise StorageError(f"Manifest config is missing for tag '{tag}'")
            
            config = self.oci_layout.get_config(manifest.config.digest)
            if config is None:
                raise StorageError(f"Config not found for tag '{tag}'")
            
            # Load layers
            from derpy.oci.models import Layer
            layers = []
            for i, layer_desc in enumerate(manifest.layers):
                layer_path = self.oci_layout.get_layer_path(layer_desc.digest)
                if layer_path is None:
                    raise StorageError(f"Layer {i} not found for tag '{tag}'")
                
                # Get diff_id from config
                diff_id = None
                if i < len(config.rootfs.diff_ids):
                    diff_id = config.rootfs.diff_ids[i]
                
                layer = Layer(
                    digest=layer_desc.digest,
                    size=layer_desc.size,
                    media_type=layer_desc.media_type,
                    content_path=layer_path,
                    diff_id=diff_id
                )
                layers.append(layer)
            
            # Create and return image
            image = Image(
                manifest=manifest,
                config=config,
                layers=layers
            )
            
            return image
            
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to retrieve image '{tag}': {e}")
    
    def _load_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Load metadata from file.
        
        Returns:
            Dictionary mapping tags to metadata
        """
        if not self.metadata_path.exists():
            return {}
        
        try:
            with open(self.metadata_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
        except Exception as e:
            raise StorageError(f"Failed to load metadata: {e}")
    
    def _save_metadata(self, metadata: Dict[str, Dict[str, Any]]) -> None:
        """Save metadata to file.
        
        Args:
            metadata: Dictionary mapping tags to metadata
        """
        try:
            with open(self.metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            raise StorageError(f"Failed to save metadata: {e}")
    
    def _add_image_metadata(self, tag: str, metadata: ImageMetadata) -> None:
        """Add or update image metadata.
        
        Args:
            tag: Image tag
            metadata: Image metadata
        """
        all_metadata = self._load_metadata()
        all_metadata[tag] = metadata.to_dict()
        self._save_metadata(all_metadata)
    
    def _get_image_metadata(self, tag: str) -> Optional[ImageMetadata]:
        """Get metadata for a specific image.
        
        Args:
            tag: Image tag
        
        Returns:
            ImageMetadata or None if not found
        """
        all_metadata = self._load_metadata()
        metadata_dict = all_metadata.get(tag)
        if metadata_dict is None:
            return None
        return ImageMetadata.from_dict(metadata_dict)
    
    def list_local_images(self) -> List[ImageInfo]:
        """List all images in the local repository.
        
        Returns:
            List of ImageInfo objects with image details
        
        Raises:
            StorageError: If listing fails
        """
        try:
            all_metadata = self._load_metadata()
            
            images = []
            for tag, metadata_dict in all_metadata.items():
                try:
                    metadata = ImageMetadata.from_dict(metadata_dict)
                    
                    # Create ImageInfo from metadata
                    image_info = ImageInfo(
                        tag=metadata.tag,
                        size=metadata.size,
                        created=metadata.created,
                        architecture=metadata.architecture,
                        os=metadata.os
                    )
                    images.append(image_info)
                except Exception as e:
                    # Skip invalid metadata entries
                    continue
            
            # Sort by creation date (newest first)
            images.sort(key=lambda x: x.created, reverse=True)
            
            return images
            
        except Exception as e:
            raise StorageError(f"Failed to list local images: {e}")
    
    def image_exists(self, tag: str) -> bool:
        """Check if an image exists in the local repository.
        
        Args:
            tag: Image tag to check
        
        Returns:
            True if image exists, False otherwise
        """
        metadata = self._get_image_metadata(tag)
        return metadata is not None
    
    def remove_image(self, tag: str) -> bool:
        """Remove a single image from local repository.
        
        Args:
            tag: Image tag to remove
        
        Returns:
            True if image was removed, False if not found
        
        Raises:
            StorageError: If removal fails
        """
        try:
            # Check if image exists using existing _get_image_metadata()
            metadata = self._get_image_metadata(tag)
            if metadata is None:
                return False
            
            # Load metadata, remove image entry, save updated metadata
            all_metadata = self._load_metadata()
            del all_metadata[tag]
            self._save_metadata(all_metadata)
            
            # Call oci_layout.remove_manifest_from_index(tag)
            self.oci_layout.remove_manifest_from_index(tag)
            
            # Note: We don't delete blobs here as they might be shared
            # Use cleanup_orphaned_blobs() to remove unused blobs
            
            return True
            
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to remove image '{tag}': {e}")
    
    def remove_all_images(self) -> int:
        """Remove all images from local repository.
        
        Returns:
            Number of images removed
        
        Raises:
            StorageError: If removal fails
        """
        try:
            # Load current metadata to count images
            all_metadata = self._load_metadata()
            image_count = len(all_metadata)
            
            # Clear metadata by saving empty dictionary
            self._save_metadata({})
            
            # Recreate OCI layout to clear index and blobs
            # First, remove the blobs directory
            if self.blobs_path.exists():
                shutil.rmtree(self.blobs_path)
            
            # Recreate the layout structure
            self.oci_layout.create_layout()
            
            # Explicitly clear the index by saving an empty index
            from derpy.oci.models import Index
            empty_index = Index()
            self.oci_layout.save_index(empty_index)
            
            return image_count
            
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to remove all images: {e}")
    
    def delete_image(self, tag: str) -> bool:
        """Delete an image from the local repository.
        
        Args:
            tag: Tag of the image to delete
        
        Returns:
            True if deleted, False if not found
        
        Raises:
            StorageError: If deletion fails
        """
        try:
            # Check if image exists
            if not self.image_exists(tag):
                return False
            
            # Remove from metadata
            all_metadata = self._load_metadata()
            del all_metadata[tag]
            self._save_metadata(all_metadata)
            
            # Note: We don't delete blobs here as they might be shared
            # Use cleanup_orphaned_blobs() to remove unused blobs
            
            return True
            
        except Exception as e:
            raise StorageError(f"Failed to delete image '{tag}': {e}")
    
    def cleanup_orphaned_blobs(self) -> int:
        """Remove blobs not referenced by any image.
        
        Returns:
            Number of blobs deleted
        
        Raises:
            StorageError: If cleanup fails
        """
        try:
            return self.oci_layout.cleanup_orphaned_blobs()
        except Exception as e:
            raise StorageError(f"Failed to cleanup orphaned blobs: {e}")
    
    def get_repository_size(self) -> int:
        """Calculate total size of the repository.
        
        Returns:
            Total size in bytes
        
        Raises:
            StorageError: If calculation fails
        """
        try:
            total_size = 0
            
            # Sum up all blob sizes
            blobs_path = self.oci_layout.blobs_path
            if blobs_path.exists():
                for blob_file in blobs_path.rglob('*'):
                    if blob_file.is_file():
                        total_size += blob_file.stat().st_size
            
            return total_size
            
        except Exception as e:
            raise StorageError(f"Failed to calculate repository size: {e}")
    
    def calculate_storage_size(self) -> int:
        """Calculate total size of image storage.
        
        Recursively iterates through repository_path and sums file sizes.
        Handles cases where repository doesn't exist.
        
        Returns:
            Total size in bytes
        
        Raises:
            StorageError: If calculation fails
        """
        try:
            # Return 0 if repository doesn't exist
            if not self.repository_path.exists():
                return 0
            
            total_size = 0
            
            # Recursively iterate through all files in repository
            for file_path in self.repository_path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            
            return total_size
            
        except Exception as e:
            raise StorageError(f"Failed to calculate storage size: {e}")
    
    def get_cache_size(self, cache_dir: Path) -> int:
        """Calculate size of base image cache directory.
        
        Args:
            cache_dir: Path to base image cache directory
        
        Returns:
            Total cache size in bytes
        
        Raises:
            StorageError: If calculation fails
        """
        try:
            # Return 0 if cache directory doesn't exist
            if not cache_dir.exists():
                return 0
            
            total_size = 0
            
            # Recursively iterate through all files in cache directory
            for file_path in cache_dir.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            
            return total_size
            
        except Exception as e:
            raise StorageError(f"Failed to calculate cache size: {e}")
    
    def prepare_image_for_push(self, tag: str) -> tuple[bytes, bytes, list[tuple[str, bytes]]]:
        """Prepare image data for pushing to a registry.
        
        Args:
            tag: Image tag
            
        Returns:
            Tuple of (manifest_bytes, config_bytes, [(layer_digest, layer_bytes), ...])
            
        Raises:
            StorageError: If image not found or preparation fails
        """
        try:
            # Get image
            image = self.get_image(tag)
            if image is None:
                raise StorageError(f"Image '{tag}' not found in local repository")
            
            # Get manifest bytes
            manifest_bytes = image.manifest.to_json().encode('utf-8')
            
            # Get config bytes
            config_bytes = image.config.to_json().encode('utf-8')
            
            # Get layer bytes
            layers_data = []
            for layer in image.layers:
                if layer.content_path is None or not layer.content_path.exists():
                    raise StorageError(f"Layer {layer.digest} content not found")
                
                layer_bytes = layer.content_path.read_bytes()
                layers_data.append((layer.digest, layer_bytes))
            
            return manifest_bytes, config_bytes, layers_data
            
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to prepare image for push: {e}")
