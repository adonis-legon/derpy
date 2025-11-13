"""OCI specification data models.

This module implements OCI-compliant data structures for container images,
including manifests, image configurations, descriptors, and layers.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import hashlib


# OCI Media Types
MEDIA_TYPE_DESCRIPTOR = "application/vnd.oci.descriptor.v1+json"
MEDIA_TYPE_LAYOUT_HEADER = "application/vnd.oci.layout.header.v1+json"
MEDIA_TYPE_IMAGE_MANIFEST = "application/vnd.oci.image.manifest.v1+json"
MEDIA_TYPE_IMAGE_INDEX = "application/vnd.oci.image.index.v1+json"
MEDIA_TYPE_IMAGE_CONFIG = "application/vnd.oci.image.config.v1+json"
MEDIA_TYPE_IMAGE_LAYER = "application/vnd.oci.image.layer.v1.tar+gzip"
MEDIA_TYPE_IMAGE_LAYER_NONDIST = "application/vnd.oci.image.layer.nondistributable.v1.tar+gzip"


@dataclass
class Descriptor:
    """OCI Content Descriptor.
    
    A descriptor is a reference to content stored in a content-addressable
    storage system.
    """
    media_type: str
    digest: str
    size: int
    urls: Optional[List[str]] = None
    annotations: Optional[Dict[str, str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "mediaType": self.media_type,
            "digest": self.digest,
            "size": self.size
        }
        if self.urls:
            result["urls"] = self.urls
        if self.annotations:
            result["annotations"] = self.annotations
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Descriptor":
        """Create Descriptor from dictionary."""
        return cls(
            media_type=data["mediaType"],
            digest=data["digest"],
            size=data["size"],
            urls=data.get("urls"),
            annotations=data.get("annotations")
        )
    
    def validate(self) -> List[str]:
        """Validate OCI compliance.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not self.media_type:
            errors.append("media_type is required")
        
        if not self.digest:
            errors.append("digest is required")
        elif not self.digest.startswith("sha256:"):
            errors.append("digest must start with 'sha256:'")
        
        if self.size < 0:
            errors.append("size must be non-negative")
        
        return errors


@dataclass
class Layer:
    """Container image layer.
    
    Represents a filesystem layer in a container image.
    """
    digest: str
    size: int
    media_type: str = MEDIA_TYPE_IMAGE_LAYER
    content_path: Optional[Path] = None
    diff_id: Optional[str] = None
    
    def to_descriptor(self) -> Descriptor:
        """Convert layer to OCI descriptor."""
        return Descriptor(
            media_type=self.media_type,
            digest=self.digest,
            size=self.size
        )
    
    def validate(self) -> List[str]:
        """Validate layer data.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not self.digest:
            errors.append("digest is required")
        elif not self.digest.startswith("sha256:"):
            errors.append("digest must start with 'sha256:'")
        
        if self.size < 0:
            errors.append("size must be non-negative")
        
        if not self.media_type:
            errors.append("media_type is required")
        
        return errors


@dataclass
class RootFS:
    """Root filesystem configuration."""
    type: str = "layers"
    diff_ids: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type,
            "diff_ids": self.diff_ids
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RootFS":
        """Create RootFS from dictionary."""
        return cls(
            type=data.get("type", "layers"),
            diff_ids=data.get("diff_ids", [])
        )


@dataclass
class HistoryEntry:
    """Image history entry."""
    created: Optional[str] = None
    created_by: Optional[str] = None
    author: Optional[str] = None
    comment: Optional[str] = None
    empty_layer: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {}
        if self.created:
            result["created"] = self.created
        if self.created_by:
            result["created_by"] = self.created_by
        if self.author:
            result["author"] = self.author
        if self.comment:
            result["comment"] = self.comment
        if self.empty_layer:
            result["empty_layer"] = self.empty_layer
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HistoryEntry":
        """Create HistoryEntry from dictionary."""
        return cls(
            created=data.get("created"),
            created_by=data.get("created_by"),
            author=data.get("author"),
            comment=data.get("comment"),
            empty_layer=data.get("empty_layer", False)
        )


@dataclass
class ContainerConfig:
    """Container runtime configuration."""
    user: Optional[str] = None
    exposed_ports: Optional[Dict[str, Dict]] = None
    env: Optional[List[str]] = None
    entrypoint: Optional[List[str]] = None
    cmd: Optional[List[str]] = None
    volumes: Optional[Dict[str, Dict]] = None
    working_dir: Optional[str] = None
    labels: Optional[Dict[str, str]] = None
    stop_signal: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {}
        if self.user:
            result["User"] = self.user
        if self.exposed_ports:
            result["ExposedPorts"] = self.exposed_ports
        if self.env:
            result["Env"] = self.env
        if self.entrypoint:
            result["Entrypoint"] = self.entrypoint
        if self.cmd:
            result["Cmd"] = self.cmd
        if self.volumes:
            result["Volumes"] = self.volumes
        if self.working_dir:
            result["WorkingDir"] = self.working_dir
        if self.labels:
            result["Labels"] = self.labels
        if self.stop_signal:
            result["StopSignal"] = self.stop_signal
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContainerConfig":
        """Create ContainerConfig from dictionary."""
        return cls(
            user=data.get("User"),
            exposed_ports=data.get("ExposedPorts"),
            env=data.get("Env"),
            entrypoint=data.get("Entrypoint"),
            cmd=data.get("Cmd"),
            volumes=data.get("Volumes"),
            working_dir=data.get("WorkingDir"),
            labels=data.get("Labels"),
            stop_signal=data.get("StopSignal")
        )


@dataclass
class ImageConfig:
    """OCI Image Configuration.
    
    Contains the configuration and metadata for a container image.
    """
    architecture: str
    os: str
    config: ContainerConfig = field(default_factory=ContainerConfig)
    rootfs: RootFS = field(default_factory=RootFS)
    history: List[HistoryEntry] = field(default_factory=list)
    created: Optional[str] = None
    author: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "architecture": self.architecture,
            "os": self.os,
            "config": self.config.to_dict(),
            "rootfs": self.rootfs.to_dict()
        }
        if self.history:
            result["history"] = [h.to_dict() for h in self.history]
        if self.created:
            result["created"] = self.created
        if self.author:
            result["author"] = self.author
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImageConfig":
        """Create ImageConfig from dictionary."""
        return cls(
            architecture=data["architecture"],
            os=data["os"],
            config=ContainerConfig.from_dict(data.get("config", {})),
            rootfs=RootFS.from_dict(data.get("rootfs", {})),
            history=[HistoryEntry.from_dict(h) for h in data.get("history", [])],
            created=data.get("created"),
            author=data.get("author")
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "ImageConfig":
        """Create ImageConfig from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    def validate(self) -> List[str]:
        """Validate OCI compliance.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not self.architecture:
            errors.append("architecture is required")
        
        if not self.os:
            errors.append("os is required")
        
        if not self.rootfs.diff_ids:
            errors.append("rootfs must contain at least one diff_id")
        
        return errors
    
    def compute_digest(self) -> str:
        """Compute SHA256 digest of the config JSON."""
        json_bytes = self.to_json().encode('utf-8')
        return f"sha256:{hashlib.sha256(json_bytes).hexdigest()}"


@dataclass
class Manifest:
    """OCI Image Manifest.
    
    Provides a configuration and set of layers for a container image.
    """
    schema_version: int = 2
    media_type: str = MEDIA_TYPE_IMAGE_MANIFEST
    config: Optional[Descriptor] = None
    layers: List[Descriptor] = field(default_factory=list)
    annotations: Optional[Dict[str, str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "schemaVersion": self.schema_version,
            "mediaType": self.media_type
        }
        
        if self.config:
            result["config"] = self.config.to_dict()
        
        if self.layers:
            result["layers"] = [layer.to_dict() for layer in self.layers]
        
        if self.annotations:
            result["annotations"] = self.annotations
        
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Manifest":
        """Create Manifest from dictionary."""
        return cls(
            schema_version=data.get("schemaVersion", 2),
            media_type=data.get("mediaType", MEDIA_TYPE_IMAGE_MANIFEST),
            config=Descriptor.from_dict(data["config"]) if "config" in data else None,
            layers=[Descriptor.from_dict(l) for l in data.get("layers", [])],
            annotations=data.get("annotations")
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "Manifest":
        """Create Manifest from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    def validate(self) -> List[str]:
        """Validate OCI compliance.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if self.schema_version != 2:
            errors.append("schemaVersion must be 2")
        
        if self.media_type != MEDIA_TYPE_IMAGE_MANIFEST:
            errors.append(f"mediaType must be {MEDIA_TYPE_IMAGE_MANIFEST}")
        
        if not self.config:
            errors.append("config descriptor is required")
        else:
            config_errors = self.config.validate()
            errors.extend([f"config.{e}" for e in config_errors])
        
        if not self.layers:
            errors.append("at least one layer is required")
        else:
            for i, layer in enumerate(self.layers):
                layer_errors = layer.validate()
                errors.extend([f"layers[{i}].{e}" for e in layer_errors])
        
        return errors
    
    def compute_digest(self) -> str:
        """Compute SHA256 digest of the manifest JSON."""
        json_bytes = self.to_json().encode('utf-8')
        return f"sha256:{hashlib.sha256(json_bytes).hexdigest()}"


@dataclass
class Index:
    """OCI Image Index.
    
    An index is a higher-level manifest that points to specific image manifests.
    """
    schema_version: int = 2
    media_type: str = MEDIA_TYPE_IMAGE_INDEX
    manifests: List[Descriptor] = field(default_factory=list)
    annotations: Optional[Dict[str, str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "schemaVersion": self.schema_version,
            "mediaType": self.media_type,
            "manifests": [m.to_dict() for m in self.manifests]
        }
        
        if self.annotations:
            result["annotations"] = self.annotations
        
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Index":
        """Create Index from dictionary."""
        return cls(
            schema_version=data.get("schemaVersion", 2),
            media_type=data.get("mediaType", MEDIA_TYPE_IMAGE_INDEX),
            manifests=[Descriptor.from_dict(m) for m in data.get("manifests", [])],
            annotations=data.get("annotations")
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "Index":
        """Create Index from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    def validate(self) -> List[str]:
        """Validate OCI compliance.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if self.schema_version != 2:
            errors.append("schemaVersion must be 2")
        
        if self.media_type != MEDIA_TYPE_IMAGE_INDEX:
            errors.append(f"mediaType must be {MEDIA_TYPE_IMAGE_INDEX}")
        
        for i, manifest in enumerate(self.manifests):
            manifest_errors = manifest.validate()
            errors.extend([f"manifests[{i}].{e}" for e in manifest_errors])
        
        return errors


@dataclass
class Image:
    """Complete OCI image representation.
    
    Combines manifest, config, and layers into a single image object.
    """
    manifest: Manifest
    config: ImageConfig
    layers: List[Layer]
    
    def validate(self) -> List[str]:
        """Validate complete image OCI compliance.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Validate manifest
        manifest_errors = self.manifest.validate()
        errors.extend([f"manifest.{e}" for e in manifest_errors])
        
        # Validate config
        config_errors = self.config.validate()
        errors.extend([f"config.{e}" for e in config_errors])
        
        # Validate layers
        for i, layer in enumerate(self.layers):
            layer_errors = layer.validate()
            errors.extend([f"layers[{i}].{e}" for e in layer_errors])
        
        # Validate consistency between manifest and layers
        if len(self.manifest.layers) != len(self.layers):
            errors.append("manifest layer count does not match actual layer count")
        
        # Validate consistency between config and layers
        if len(self.config.rootfs.diff_ids) != len(self.layers):
            errors.append("config rootfs diff_ids count does not match layer count")
        
        return errors
