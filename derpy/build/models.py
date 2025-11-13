"""Build isolation data models.

This module implements data models for build isolation features including
image references, filesystem snapshots, diffs, and execution results.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List
from pathlib import Path
from datetime import datetime
import re


@dataclass
class ImageReference:
    """Parsed container image reference.
    
    Represents a parsed image reference string like "ubuntu:22.04" or
    "ghcr.io/org/app:v1.0".
    """
    registry: str
    repository: str
    tag: str
    digest: Optional[str] = None
    
    @classmethod
    def parse(cls, ref: str) -> "ImageReference":
        """Parse image reference string into components.
        
        Examples:
            "ubuntu:22.04" → ImageReference(
                registry="docker.io",
                repository="library/ubuntu",
                tag="22.04"
            )
            "ghcr.io/org/app:v1" → ImageReference(
                registry="ghcr.io",
                repository="org/app",
                tag="v1"
            )
            "nginx" → ImageReference(
                registry="docker.io",
                repository="library/nginx",
                tag="latest"
            )
            "ubuntu@sha256:abc..." → ImageReference(
                registry="docker.io",
                repository="library/ubuntu",
                tag="latest",
                digest="sha256:abc..."
            )
        
        Args:
            ref: Image reference string
            
        Returns:
            Parsed ImageReference object
            
        Raises:
            ValueError: If the reference format is invalid
        """
        if not ref or not ref.strip():
            raise ValueError("Image reference cannot be empty")
        
        ref = ref.strip()
        digest = None
        
        # Extract digest if present (e.g., ubuntu@sha256:abc...)
        if "@" in ref:
            ref, digest = ref.rsplit("@", 1)
            if not digest.startswith("sha256:"):
                raise ValueError(f"Invalid digest format: {digest}")
        
        # Extract tag if present
        tag = "latest"
        if ":" in ref:
            ref, tag = ref.rsplit(":", 1)
            # Validate tag format (alphanumeric, dots, dashes, underscores)
            if not re.match(r'^[a-zA-Z0-9._-]+$', tag):
                raise ValueError(f"Invalid tag format: {tag}")
        
        # Parse registry and repository
        parts = ref.split("/")
        
        # Check if first part is a registry (contains dot or is localhost)
        if len(parts) > 1 and ("." in parts[0] or ":" in parts[0] or parts[0] == "localhost"):
            registry = parts[0]
            repository = "/".join(parts[1:])
        else:
            # Default to Docker Hub
            registry = "docker.io"
            repository = ref
            
            # Add library/ prefix for official images (single name without slash)
            if "/" not in repository:
                repository = f"library/{repository}"
        
        if not repository:
            raise ValueError(f"Invalid image reference: {ref}")
        
        return cls(
            registry=registry,
            repository=repository,
            tag=tag,
            digest=digest
        )
    
    def to_string(self, include_registry: bool = False) -> str:
        """Convert back to string format.
        
        Args:
            include_registry: Whether to include registry in output
            
        Returns:
            Image reference string
        """
        result = ""
        
        # Build the base reference
        if include_registry:
            result = f"{self.registry}/{self.repository}"
        elif self.registry != "docker.io":
            result = f"{self.registry}/{self.repository}"
        else:
            # For Docker Hub, remove library/ prefix for official images
            if self.repository.startswith("library/"):
                result = self.repository.replace("library/", "", 1)
            else:
                result = self.repository
        
        # Add tag or digest
        if self.digest:
            result += f"@{self.digest}"
        else:
            result += f":{self.tag}"
        
        return result
    
    def __str__(self) -> str:
        """String representation."""
        return self.to_string()


@dataclass
class FileEntry:
    """Represents a file in the filesystem snapshot.
    
    Captures metadata about a file for comparison purposes.
    """
    path: Path
    size: int
    mtime: float
    mode: int
    is_dir: bool
    is_symlink: bool
    link_target: Optional[str] = None
    
    def __eq__(self, other) -> bool:
        """Compare two file entries for equality.
        
        Files are considered equal if they have the same size, mtime, and mode.
        """
        if not isinstance(other, FileEntry):
            return False
        
        return (
            self.path == other.path
            and self.size == other.size
            and self.mtime == other.mtime
            and self.mode == other.mode
            and self.is_dir == other.is_dir
            and self.is_symlink == other.is_symlink
            and self.link_target == other.link_target
        )
    
    def is_modified(self, other: "FileEntry") -> bool:
        """Check if this file is modified compared to another.
        
        Args:
            other: Another FileEntry to compare against
            
        Returns:
            True if the file has been modified
        """
        if self.path != other.path:
            return False
        
        # Different types means modified
        if self.is_dir != other.is_dir or self.is_symlink != other.is_symlink:
            return True
        
        # For symlinks, check target
        if self.is_symlink:
            return self.link_target != other.link_target
        
        # For regular files, check size and mtime
        if not self.is_dir:
            return self.size != other.size or self.mtime != other.mtime
        
        # Directories are not considered modified based on metadata
        return False


@dataclass
class Snapshot:
    """Filesystem snapshot for diff comparison.
    
    Captures the state of a filesystem at a point in time for later comparison.
    """
    timestamp: datetime
    files: Dict[str, FileEntry] = field(default_factory=dict)
    
    def add_file(self, entry: FileEntry) -> None:
        """Add a file entry to the snapshot.
        
        Args:
            entry: FileEntry to add
        """
        self.files[str(entry.path)] = entry
    
    def get_file(self, path: Path) -> Optional[FileEntry]:
        """Get a file entry by path.
        
        Args:
            path: Path to look up
            
        Returns:
            FileEntry if found, None otherwise
        """
        return self.files.get(str(path))
    
    def compare(self, other: "Snapshot") -> "FilesystemDiff":
        """Compare two snapshots to find changes.
        
        Args:
            other: Another snapshot to compare against (the "after" snapshot)
            
        Returns:
            FilesystemDiff containing added, modified, and deleted files
        """
        added = []
        modified = []
        deleted = []
        
        # Find added and modified files
        for path, entry in other.files.items():
            if path not in self.files:
                added.append(Path(path))
            else:
                old_entry = self.files[path]
                if entry.is_modified(old_entry):
                    modified.append(Path(path))
        
        # Find deleted files
        for path in self.files:
            if path not in other.files:
                deleted.append(Path(path))
        
        return FilesystemDiff(
            added=added,
            modified=modified,
            deleted=deleted
        )


@dataclass
class FilesystemDiff:
    """Represents changes between two filesystem snapshots.
    
    Contains lists of added, modified, and deleted files.
    """
    added: List[Path] = field(default_factory=list)
    modified: List[Path] = field(default_factory=list)
    deleted: List[Path] = field(default_factory=list)
    
    def is_empty(self) -> bool:
        """Check if the diff contains any changes.
        
        Returns:
            True if no files were added, modified, or deleted
        """
        return not (self.added or self.modified or self.deleted)
    
    def get_changed_files(self) -> List[Path]:
        """Get all changed files (added + modified).
        
        Returns:
            List of paths that were added or modified
        """
        return self.added + self.modified
    
    def total_changes(self) -> int:
        """Get total number of changes.
        
        Returns:
            Total count of added, modified, and deleted files
        """
        return len(self.added) + len(self.modified) + len(self.deleted)
    
    def __str__(self) -> str:
        """String representation of the diff."""
        return (
            f"FilesystemDiff(added={len(self.added)}, "
            f"modified={len(self.modified)}, "
            f"deleted={len(self.deleted)})"
        )


@dataclass
class ExecutionResult:
    """Result of command execution in isolated environment.
    
    Contains the output and status of a command executed in chroot.
    """
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    command: Optional[str] = None
    
    def is_success(self) -> bool:
        """Check if the command executed successfully.
        
        Returns:
            True if exit code is 0
        """
        return self.exit_code == 0
    
    def is_failure(self) -> bool:
        """Check if the command failed.
        
        Returns:
            True if exit code is non-zero
        """
        return self.exit_code != 0
    
    def get_output(self) -> str:
        """Get combined stdout and stderr.
        
        Returns:
            Combined output string
        """
        output = ""
        if self.stdout:
            output += self.stdout
        if self.stderr:
            if output:
                output += "\n"
            output += self.stderr
        return output
    
    def __str__(self) -> str:
        """String representation of the execution result."""
        status = "SUCCESS" if self.is_success() else f"FAILED (exit code {self.exit_code})"
        return f"ExecutionResult({status}, duration={self.duration:.2f}s)"
