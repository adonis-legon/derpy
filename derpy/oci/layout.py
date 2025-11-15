"""OCI layout management for filesystem operations.

This module implements the OCI Image Layout specification for storing
container images on the filesystem.
"""

from pathlib import Path
from typing import Optional, List
import json
import hashlib
import shutil

from derpy.oci.models import (
    Descriptor,
    Manifest,
    Index,
    ImageConfig,
    MEDIA_TYPE_LAYOUT_HEADER,
    MEDIA_TYPE_IMAGE_MANIFEST,
    MEDIA_TYPE_IMAGE_CONFIG,
    MEDIA_TYPE_IMAGE_LAYER,
)
from derpy.core.platform import normalize_path, ensure_directory, get_default_file_mode, set_file_permissions


class OCILayoutManager:
    """Manages OCI image layout on the filesystem.
    
    Implements the OCI Image Layout specification for content-addressable
    blob storage and manifest management.
    """
    
    OCI_LAYOUT_VERSION = "1.0.0"
    
    def __init__(self, root_path: Path):
        """Initialize OCI layout manager.
        
        Args:
            root_path: Root directory for the OCI layout
        """
        self.root_path = normalize_path(root_path)
        self.blobs_path = self.root_path / "blobs" / "sha256"
        self.index_path = self.root_path / "index.json"
        self.layout_path = self.root_path / "oci-layout"
    
    def create_layout(self) -> None:
        """Create OCI layout directory structure.
        
        Creates the required directories and oci-layout file according to
        the OCI Image Layout specification.
        """
        # Create directory structure with platform-appropriate permissions
        ensure_directory(self.root_path)
        ensure_directory(self.blobs_path)
        
        # Create oci-layout file
        layout_content = {
            "imageLayoutVersion": self.OCI_LAYOUT_VERSION
        }
        with open(self.layout_path, 'w') as f:
            json.dump(layout_content, f, indent=2)
        set_file_permissions(self.layout_path, get_default_file_mode())
        
        # Create empty index if it doesn't exist
        if not self.index_path.exists():
            empty_index = Index()
            self._write_json(self.index_path, empty_index.to_dict())
    
    def store_blob(self, content: bytes, media_type: str) -> Descriptor:
        """Store a blob in content-addressable storage.
        
        Args:
            content: Binary content to store
            media_type: OCI media type of the content
        
        Returns:
            Descriptor referencing the stored blob
        """
        # Compute SHA256 digest
        digest_hash = hashlib.sha256(content).hexdigest()
        digest = f"sha256:{digest_hash}"
        
        # Store blob with content-addressable naming
        blob_path = self.blobs_path / digest_hash
        blob_path.write_bytes(content)
        
        # Create and return descriptor
        return Descriptor(
            media_type=media_type,
            digest=digest,
            size=len(content)
        )
    
    def get_blob(self, digest: str) -> Optional[bytes]:
        """Retrieve a blob by its digest.
        
        Args:
            digest: Content digest (e.g., "sha256:abc123...")
        
        Returns:
            Blob content or None if not found
        """
        if not digest.startswith("sha256:"):
            return None
        
        digest_hash = digest.split(":", 1)[1]
        blob_path = self.blobs_path / digest_hash
        
        if not blob_path.exists():
            return None
        
        return blob_path.read_bytes()
    
    def blob_exists(self, digest: str) -> bool:
        """Check if a blob exists in storage.
        
        Args:
            digest: Content digest (e.g., "sha256:abc123...")
        
        Returns:
            True if blob exists, False otherwise
        """
        if not digest.startswith("sha256:"):
            return False
        
        digest_hash = digest.split(":", 1)[1]
        blob_path = self.blobs_path / digest_hash
        return blob_path.exists()
    
    def store_manifest(self, manifest: Manifest) -> Descriptor:
        """Store an image manifest as a blob.
        
        Args:
            manifest: Manifest to store
        
        Returns:
            Descriptor referencing the stored manifest
        """
        manifest_json = manifest.to_json()
        manifest_bytes = manifest_json.encode('utf-8')
        
        return self.store_blob(manifest_bytes, MEDIA_TYPE_IMAGE_MANIFEST)
    
    def get_manifest(self, digest: str) -> Optional[Manifest]:
        """Retrieve a manifest by its digest.
        
        Args:
            digest: Manifest digest
        
        Returns:
            Manifest object or None if not found
        """
        blob = self.get_blob(digest)
        if blob is None:
            return None
        
        try:
            manifest_json = blob.decode('utf-8')
            return Manifest.from_json(manifest_json)
        except (json.JSONDecodeError, KeyError):
            return None
    
    def store_config(self, config: ImageConfig) -> Descriptor:
        """Store an image config as a blob.
        
        Args:
            config: Image configuration to store
        
        Returns:
            Descriptor referencing the stored config
        """
        config_json = config.to_json()
        config_bytes = config_json.encode('utf-8')
        
        return self.store_blob(config_bytes, MEDIA_TYPE_IMAGE_CONFIG)
    
    def get_config(self, digest: str) -> Optional[ImageConfig]:
        """Retrieve an image config by its digest.
        
        Args:
            digest: Config digest
        
        Returns:
            ImageConfig object or None if not found
        """
        blob = self.get_blob(digest)
        if blob is None:
            return None
        
        try:
            config_json = blob.decode('utf-8')
            return ImageConfig.from_json(config_json)
        except (json.JSONDecodeError, KeyError):
            return None
    
    def store_layer(self, layer_path: Path) -> Descriptor:
        """Store a layer file as a blob.
        
        Args:
            layer_path: Path to the layer tar.gz file
        
        Returns:
            Descriptor referencing the stored layer
        """
        layer_content = layer_path.read_bytes()
        return self.store_blob(layer_content, MEDIA_TYPE_IMAGE_LAYER)
    
    def get_layer_path(self, digest: str) -> Optional[Path]:
        """Get the filesystem path for a layer blob.
        
        Args:
            digest: Layer digest
        
        Returns:
            Path to the layer blob or None if not found
        """
        if not digest.startswith("sha256:"):
            return None
        
        digest_hash = digest.split(":", 1)[1]
        blob_path = self.blobs_path / digest_hash
        
        if not blob_path.exists():
            return None
        
        return blob_path
    
    def create_index(self, manifests: List[Descriptor], annotations: Optional[dict] = None) -> Index:
        """Create an image index.
        
        Args:
            manifests: List of manifest descriptors
            annotations: Optional annotations for the index
        
        Returns:
            Index object
        """
        return Index(
            manifests=manifests,
            annotations=annotations
        )
    
    def save_index(self, index: Index) -> None:
        """Save the index to the layout.
        
        Args:
            index: Index to save
        """
        self._write_json(self.index_path, index.to_dict())
    
    def load_index(self) -> Optional[Index]:
        """Load the index from the layout.
        
        Returns:
            Index object or None if not found
        """
        if not self.index_path.exists():
            return None
        
        try:
            with open(self.index_path, 'r') as f:
                data = json.load(f)
            return Index.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None
    
    def add_manifest_to_index(self, manifest_descriptor: Descriptor, tag: Optional[str] = None) -> None:
        """Add a manifest to the index.
        
        Args:
            manifest_descriptor: Descriptor of the manifest to add
            tag: Optional tag annotation for the manifest
        """
        index = self.load_index()
        if index is None:
            index = Index()
        
        # Add tag annotation if provided
        if tag:
            if manifest_descriptor.annotations is None:
                manifest_descriptor.annotations = {}
            manifest_descriptor.annotations["org.opencontainers.image.ref.name"] = tag
        
        # Add manifest to index if not already present
        existing_digests = {m.digest for m in index.manifests}
        if manifest_descriptor.digest not in existing_digests:
            index.manifests.append(manifest_descriptor)
            self.save_index(index)
    
    def list_manifests(self) -> List[Descriptor]:
        """List all manifests in the index.
        
        Returns:
            List of manifest descriptors
        """
        index = self.load_index()
        if index is None:
            return []
        return index.manifests
    
    def get_manifest_by_tag(self, tag: str) -> Optional[Descriptor]:
        """Get a manifest descriptor by tag.
        
        Args:
            tag: Image tag to search for
        
        Returns:
            Manifest descriptor or None if not found
        """
        manifests = self.list_manifests()
        for manifest in manifests:
            if manifest.annotations:
                ref_name = manifest.annotations.get("org.opencontainers.image.ref.name")
                if ref_name == tag:
                    return manifest
        return None
    
    def remove_manifest_from_index(self, tag: str) -> bool:
        """Remove a manifest reference from the OCI index.
        
        Args:
            tag: Image tag to remove from index
        
        Returns:
            True if removed, False if not found
        
        Raises:
            StorageError: If index update fails
        """
        # Load current index
        index = self.load_index()
        if index is None:
            return False
        
        # Find and filter out manifest entries matching the tag
        original_count = len(index.manifests)
        filtered_manifests = []
        
        for manifest in index.manifests:
            if manifest.annotations:
                ref_name = manifest.annotations.get("org.opencontainers.image.ref.name")
                if ref_name == tag:
                    # Skip this manifest (remove it)
                    continue
            filtered_manifests.append(manifest)
        
        # Check if any manifest was removed
        if len(filtered_manifests) == original_count:
            return False
        
        # Update index with filtered manifests
        index.manifests = filtered_manifests
        
        try:
            self.save_index(index)
            return True
        except Exception as e:
            from derpy.core.exceptions import StorageError
            raise StorageError(f"Failed to update index after removing manifest: {e}")
    
    def delete_blob(self, digest: str) -> bool:
        """Delete a blob from storage.
        
        Args:
            digest: Digest of the blob to delete
        
        Returns:
            True if deleted, False if not found
        """
        if not digest.startswith("sha256:"):
            return False
        
        digest_hash = digest.split(":", 1)[1]
        blob_path = self.blobs_path / digest_hash
        
        if not blob_path.exists():
            return False
        
        blob_path.unlink()
        return True
    
    def cleanup_orphaned_blobs(self) -> int:
        """Remove blobs not referenced by any manifest in the index.
        
        Returns:
            Number of blobs deleted
        """
        # Get all referenced digests from index
        referenced_digests = set()
        index = self.load_index()
        
        if index:
            for manifest_desc in index.manifests:
                referenced_digests.add(manifest_desc.digest)
                
                # Load manifest and get referenced blobs
                manifest = self.get_manifest(manifest_desc.digest)
                if manifest:
                    if manifest.config:
                        referenced_digests.add(manifest.config.digest)
                    for layer in manifest.layers:
                        referenced_digests.add(layer.digest)
        
        # Find orphaned blobs
        deleted_count = 0
        if self.blobs_path.exists():
            for blob_file in self.blobs_path.iterdir():
                if blob_file.is_file():
                    digest = f"sha256:{blob_file.name}"
                    if digest not in referenced_digests:
                        blob_file.unlink()
                        deleted_count += 1
        
        return deleted_count
    
    def _write_json(self, path: Path, data: dict) -> None:
        """Write JSON data to a file.
        
        Args:
            path: File path
            data: Dictionary to write as JSON
        """
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
