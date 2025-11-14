"""Filesystem diff capture and layer creation.

This module implements filesystem snapshot and diff capture functionality
for creating OCI layers from filesystem changes during build execution.
"""

from pathlib import Path
from typing import Optional
from datetime import datetime
import os
import stat

from derpy.build.models import Snapshot, FileEntry, FilesystemDiff
from derpy.build.layers import LayerBuilder
from derpy.core.exceptions import FilesystemDiffError
from derpy.oci.models import Layer
from derpy.core.logging import get_logger


class LayerDiffManager:
    """Manages filesystem diff capture and layer creation.
    
    This class provides functionality to:
    - Create snapshots of filesystem state
    - Compare snapshots to identify changes
    - Create OCI layers from filesystem diffs
    """
    
    def __init__(self, layer_builder: Optional[LayerBuilder] = None):
        """Initialize LayerDiffManager.
        
        Args:
            layer_builder: LayerBuilder instance for creating layers
        """
        self.layer_builder = layer_builder or LayerBuilder()
        self.logger = get_logger('diff')
    
    def create_snapshot(self, rootfs: Path) -> Snapshot:
        """Create filesystem snapshot before command execution.
        
        Recursively scans the rootfs directory and captures metadata
        for all files, directories, and symlinks.
        
        Args:
            rootfs: Path to root filesystem directory
            
        Returns:
            Snapshot object containing filesystem state
            
        Raises:
            FilesystemDiffError: If snapshot creation fails
        """
        if not rootfs.exists():
            raise FilesystemDiffError(
                f"Cannot create snapshot: rootfs does not exist\n"
                f"Path: {rootfs}\n"
                "Ensure the base image was extracted successfully.",
                cause=None
            )
        
        if not rootfs.is_dir():
            raise FilesystemDiffError(
                f"Cannot create snapshot: rootfs is not a directory\n"
                f"Path: {rootfs}",
                cause=None
            )
        
        self.logger.debug(f"Creating snapshot of {rootfs}")
        
        snapshot = Snapshot(timestamp=datetime.now())
        
        # Directories to skip (virtual filesystems)
        skip_dirs = {'proc', 'sys', 'dev'}
        
        try:
            # Walk the directory tree
            for root, dirs, files in os.walk(rootfs, followlinks=False):
                root_path = Path(root)
                
                # Skip virtual filesystem directories at root level
                if root_path == rootfs:
                    dirs[:] = [d for d in dirs if d not in skip_dirs]
                
                # Process directories
                for dir_name in dirs:
                    dir_path = root_path / dir_name
                    
                    # Skip if it's a symlink (will be handled separately)
                    if dir_path.is_symlink():
                        continue
                    
                    try:
                        # Get directory metadata
                        st = dir_path.stat()
                        relative_path = dir_path.relative_to(rootfs)
                        
                        entry = FileEntry(
                            path=relative_path,
                            size=0,  # Directories don't have meaningful size
                            mtime=st.st_mtime,
                            mode=st.st_mode,
                            is_dir=True,
                            is_symlink=False
                        )
                        snapshot.add_file(entry)
                        
                    except (OSError, PermissionError) as e:
                        self.logger.warning(f"Cannot stat directory {dir_path}: {e}")
                        continue
                
                # Process files
                for file_name in files:
                    file_path = root_path / file_name
                    
                    try:
                        # Check if it's a symlink
                        is_symlink = file_path.is_symlink()
                        
                        if is_symlink:
                            # For symlinks, use lstat to get link metadata
                            st = file_path.lstat()
                            link_target = os.readlink(file_path)
                            relative_path = file_path.relative_to(rootfs)
                            
                            entry = FileEntry(
                                path=relative_path,
                                size=0,
                                mtime=st.st_mtime,
                                mode=st.st_mode,
                                is_dir=False,
                                is_symlink=True,
                                link_target=link_target
                            )
                        else:
                            # Regular file
                            st = file_path.stat()
                            relative_path = file_path.relative_to(rootfs)
                            
                            entry = FileEntry(
                                path=relative_path,
                                size=st.st_size,
                                mtime=st.st_mtime,
                                mode=st.st_mode,
                                is_dir=False,
                                is_symlink=False
                            )
                        
                        snapshot.add_file(entry)
                        
                    except (OSError, PermissionError) as e:
                        self.logger.warning(f"Cannot stat file {file_path}: {e}")
                        continue
            
            self.logger.debug(f"Snapshot created with {len(snapshot.files)} entries")
            return snapshot
            
        except FilesystemDiffError:
            raise
        except Exception as e:
            raise FilesystemDiffError(
                f"Unexpected error while creating filesystem snapshot\n"
                f"Rootfs: {rootfs}\n"
                f"Error: {e}",
                cause=e
            )

    def compare_snapshots(
        self,
        before: Snapshot,
        after: Snapshot
    ) -> FilesystemDiff:
        """Compare two snapshots to identify filesystem changes.
        
        Identifies files that were added, modified, or deleted between
        the two snapshots.
        
        Args:
            before: Snapshot taken before changes
            after: Snapshot taken after changes
            
        Returns:
            FilesystemDiff containing added, modified, and deleted files
        """
        self.logger.debug(
            f"Comparing snapshots: before={len(before.files)} files, "
            f"after={len(after.files)} files"
        )
        
        diff = before.compare(after)
        
        self.logger.debug(
            f"Diff: {len(diff.added)} added, {len(diff.modified)} modified, "
            f"{len(diff.deleted)} deleted"
        )
        
        return diff

    def create_layer_from_diff(
        self,
        rootfs: Path,
        diff: FilesystemDiff,
        instruction: str
    ) -> Layer:
        """Create OCI layer from filesystem diff.
        
        Creates a tar.gz archive containing:
        - All added and modified files with their full content
        - Whiteout markers (.wh.filename) for deleted files
        - Proper file permissions, ownership, and timestamps
        
        Args:
            rootfs: Path to root filesystem
            diff: FilesystemDiff containing changes
            instruction: Dockerfile instruction that caused the changes
            
        Returns:
            Layer object with proper metadata
            
        Raises:
            FilesystemDiffError: If layer creation fails
        """
        import tarfile
        import gzip
        import hashlib
        import io
        import tempfile
        
        self.logger.debug(f"Creating layer from diff for instruction: {instruction}")
        
        temp_file = None
        try:
            # Create tar archive in memory
            tar_buffer = io.BytesIO()
            
            try:
                with tarfile.open(fileobj=tar_buffer, mode='w', format=tarfile.PAX_FORMAT) as tar:
                    # Add changed files (added + modified)
                    changed_files = diff.get_changed_files()
                    
                    for relative_path in changed_files:
                        file_path = rootfs / relative_path
                        
                        if not file_path.exists():
                            self.logger.warning(
                                f"File {relative_path} in diff but not found in rootfs"
                            )
                            continue
                        
                        try:
                            # Add file to tar with relative path
                            tar.add(file_path, arcname=str(relative_path), recursive=False)
                            self.logger.debug(f"Added to layer: {relative_path}")
                            
                        except (OSError, PermissionError) as e:
                            self.logger.warning(f"Cannot add {relative_path} to layer: {e}")
                            continue
                    
                    # Add whiteout markers for deleted files
                    for relative_path in diff.deleted:
                        # Create whiteout marker: .wh.<filename>
                        parent = relative_path.parent
                        filename = relative_path.name
                        whiteout_name = f".wh.{filename}"
                        whiteout_path = parent / whiteout_name
                        
                        # Create empty file as whiteout marker
                        tarinfo = tarfile.TarInfo(name=str(whiteout_path))
                        tarinfo.size = 0
                        tarinfo.mtime = int(datetime.now().timestamp())
                        tarinfo.mode = 0o644
                        tarinfo.type = tarfile.REGTYPE
                        
                        tar.addfile(tarinfo, io.BytesIO(b''))
                        self.logger.debug(f"Added whiteout marker: {whiteout_path}")
            except tarfile.TarError as tar_error:
                raise FilesystemDiffError(
                    f"Failed to create tar archive for layer\n"
                    f"Instruction: {instruction}\n"
                    f"Changes: {diff.total_changes()} files\n"
                    f"Error: {tar_error}",
                    cause=tar_error
                )
            
            # Get uncompressed tar data
            tar_data = tar_buffer.getvalue()
            
            # Compute diff_id (SHA256 of uncompressed tar)
            try:
                diff_id = f"sha256:{hashlib.sha256(tar_data).hexdigest()}"
            except Exception as hash_error:
                raise FilesystemDiffError(
                    f"Failed to compute diff_id hash for layer\n"
                    f"Instruction: {instruction}",
                    cause=hash_error
                )
            
            # Compress with gzip
            try:
                gzip_buffer = io.BytesIO()
                with gzip.GzipFile(fileobj=gzip_buffer, mode='wb') as gz:
                    gz.write(tar_data)
                compressed_data = gzip_buffer.getvalue()
            except Exception as gzip_error:
                raise FilesystemDiffError(
                    f"Failed to compress layer with gzip\n"
                    f"Instruction: {instruction}\n"
                    f"Uncompressed size: {len(tar_data)} bytes",
                    cause=gzip_error
                )
            
            # Compute digest (SHA256 of compressed tar.gz)
            try:
                digest = f"sha256:{hashlib.sha256(compressed_data).hexdigest()}"
            except Exception as hash_error:
                raise FilesystemDiffError(
                    f"Failed to compute digest hash for layer\n"
                    f"Instruction: {instruction}",
                    cause=hash_error
                )
            
            # Write to temporary file
            try:
                temp_file = tempfile.NamedTemporaryFile(
                    mode='wb',
                    suffix='.tar.gz',
                    delete=False,
                    prefix='derpy_layer_'
                )
                temp_file.write(compressed_data)
                temp_file.close()
            except (OSError, IOError) as file_error:
                raise FilesystemDiffError(
                    f"Failed to write layer to temporary file\n"
                    f"Instruction: {instruction}\n"
                    f"Layer size: {len(compressed_data)} bytes\n"
                    "Check disk space and permissions.",
                    cause=file_error
                )
            
            # Create Layer object
            from derpy.oci.models import Layer as OCILayer, MEDIA_TYPE_IMAGE_LAYER
            
            layer = OCILayer(
                digest=digest,
                size=len(compressed_data),
                media_type=MEDIA_TYPE_IMAGE_LAYER,
                content_path=Path(temp_file.name),
                diff_id=diff_id
            )
            
            self.logger.info(
                f"Created layer: {digest[:19]}... "
                f"({len(compressed_data)} bytes, {diff.total_changes()} changes)"
            )
            
            return layer
            
        except FilesystemDiffError:
            # Clean up temp file on error
            if temp_file and hasattr(temp_file, 'name'):
                try:
                    Path(temp_file.name).unlink(missing_ok=True)
                except Exception:
                    pass
            raise
        except Exception as e:
            # Clean up temp file on error
            if temp_file and hasattr(temp_file, 'name'):
                try:
                    Path(temp_file.name).unlink(missing_ok=True)
                except Exception:
                    pass
            raise FilesystemDiffError(
                f"Unexpected error while creating layer from diff\n"
                f"Instruction: {instruction}\n"
                f"Error: {e}",
                cause=e
            )

    def capture_diff(
        self,
        rootfs: Path,
        before_snapshot: Snapshot,
        instruction: str
    ) -> Optional[Layer]:
        """Capture filesystem changes after command execution.
        
        This is the main method that orchestrates the diff capture process:
        1. Create a new snapshot of the current rootfs state
        2. Compare with the before snapshot to identify changes
        3. If changes exist, create a layer from the diff
        4. If no changes, return None (empty layer)
        
        Args:
            rootfs: Path to root filesystem
            before_snapshot: Snapshot taken before command execution
            instruction: Dockerfile instruction that was executed
            
        Returns:
            Layer object if changes were detected, None if no changes
            
        Raises:
            FilesystemDiffError: If diff capture fails
        """
        self.logger.debug(f"Capturing diff for instruction: {instruction}")
        
        try:
            # Create snapshot of current state
            try:
                after_snapshot = self.create_snapshot(rootfs)
            except FilesystemDiffError as snapshot_error:
                raise FilesystemDiffError(
                    f"Failed to create post-execution snapshot\n"
                    f"Instruction: {instruction}\n"
                    f"Error: {snapshot_error.message}",
                    cause=snapshot_error
                )
            
            # Compare snapshots
            try:
                diff = self.compare_snapshots(before_snapshot, after_snapshot)
            except Exception as compare_error:
                raise FilesystemDiffError(
                    f"Failed to compare filesystem snapshots\n"
                    f"Instruction: {instruction}\n"
                    f"Before: {len(before_snapshot.files)} files\n"
                    f"After: {len(after_snapshot.files)} files",
                    cause=compare_error
                )
            
            # Check if diff is empty
            if diff.is_empty():
                self.logger.info(
                    f"No filesystem changes detected for instruction: {instruction}"
                )
                return None
            
            # Create layer from diff
            try:
                layer = self.create_layer_from_diff(rootfs, diff, instruction)
            except FilesystemDiffError:
                raise
            
            return layer
            
        except FilesystemDiffError:
            raise
        except Exception as e:
            raise FilesystemDiffError(
                f"Unexpected error while capturing filesystem diff\n"
                f"Instruction: {instruction}\n"
                f"Rootfs: {rootfs}",
                cause=e
            )
    
    def create_empty_layer_marker(self, instruction: str) -> Optional[Layer]:
        """Create an empty layer marker for no-op commands.
        
        Some Dockerfile instructions (like ENV, LABEL) don't modify the
        filesystem but should still be recorded in the image history.
        This method can be used to create a marker for such instructions.
        
        Note: In the current implementation, we return None for empty diffs
        and let the build engine handle history entries separately.
        
        Args:
            instruction: Dockerfile instruction
            
        Returns:
            None (empty layers are not created as separate files)
        """
        self.logger.debug(f"Empty layer marker for instruction: {instruction}")
        return None
