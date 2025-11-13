"""Tests for LayerDiffManager."""

import pytest
from pathlib import Path
import tempfile
import tarfile
import gzip
from datetime import datetime

from derpy.build.diff import LayerDiffManager
from derpy.build.models import Snapshot, FileEntry, FilesystemDiff
from derpy.build.layers import LayerBuilder
from derpy.core.exceptions import FilesystemDiffError


class TestSnapshotCreation:
    """Tests for filesystem snapshot creation."""
    
    def test_create_snapshot_empty_directory(self):
        """Test creating snapshot of empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir)
            
            manager = LayerDiffManager()
            snapshot = manager.create_snapshot(rootfs)
            
            assert isinstance(snapshot, Snapshot)
            assert len(snapshot.files) == 0
    
    def test_create_snapshot_with_files(self):
        """Test creating snapshot with files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir)
            (rootfs / "file1.txt").write_text("content1")
            (rootfs / "file2.txt").write_text("content2")
            
            manager = LayerDiffManager()
            snapshot = manager.create_snapshot(rootfs)
            
            assert len(snapshot.files) == 2
            assert "file1.txt" in snapshot.files
            assert "file2.txt" in snapshot.files
    
    def test_create_snapshot_with_directories(self):
        """Test creating snapshot with directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir)
            (rootfs / "dir1").mkdir()
            (rootfs / "dir1" / "file.txt").write_text("content")
            (rootfs / "dir2").mkdir()
            
            manager = LayerDiffManager()
            snapshot = manager.create_snapshot(rootfs)
            
            assert len(snapshot.files) >= 3  # dir1, dir2, file.txt
            assert any("dir1" in str(entry.path) for entry in snapshot.files.values())
    
    def test_create_snapshot_with_symlinks(self):
        """Test creating snapshot with symlinks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir)
            (rootfs / "target.txt").write_text("target")
            (rootfs / "link.txt").symlink_to("target.txt")
            
            manager = LayerDiffManager()
            snapshot = manager.create_snapshot(rootfs)
            
            link_entry = snapshot.get_file(Path("link.txt"))
            assert link_entry is not None
            assert link_entry.is_symlink
            assert link_entry.link_target == "target.txt"
    
    def test_create_snapshot_nonexistent_directory(self):
        """Test creating snapshot of nonexistent directory."""
        manager = LayerDiffManager()
        
        with pytest.raises(FilesystemDiffError, match="does not exist"):
            manager.create_snapshot(Path("/nonexistent"))
    
    def test_create_snapshot_not_directory(self):
        """Test creating snapshot of non-directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "file.txt"
            file_path.write_text("content")
            
            manager = LayerDiffManager()
            
            with pytest.raises(FilesystemDiffError, match="not a directory"):
                manager.create_snapshot(file_path)


class TestSnapshotComparison:
    """Tests for snapshot comparison."""
    
    def test_compare_identical_snapshots(self):
        """Test comparing identical snapshots."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir)
            (rootfs / "file.txt").write_text("content")
            
            manager = LayerDiffManager()
            snapshot1 = manager.create_snapshot(rootfs)
            snapshot2 = manager.create_snapshot(rootfs)
            
            diff = manager.compare_snapshots(snapshot1, snapshot2)
            
            assert diff.is_empty()
            assert len(diff.added) == 0
            assert len(diff.modified) == 0
            assert len(diff.deleted) == 0
    
    def test_compare_with_added_files(self):
        """Test comparing snapshots with added files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir)
            
            manager = LayerDiffManager()
            snapshot1 = manager.create_snapshot(rootfs)
            
            # Add files
            (rootfs / "new1.txt").write_text("new1")
            (rootfs / "new2.txt").write_text("new2")
            
            snapshot2 = manager.create_snapshot(rootfs)
            diff = manager.compare_snapshots(snapshot1, snapshot2)
            
            assert not diff.is_empty()
            assert len(diff.added) == 2
            assert len(diff.modified) == 0
            assert len(diff.deleted) == 0
    
    def test_compare_with_modified_files(self):
        """Test comparing snapshots with modified files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir)
            file_path = rootfs / "file.txt"
            file_path.write_text("original")
            
            manager = LayerDiffManager()
            snapshot1 = manager.create_snapshot(rootfs)
            
            # Modify file
            import time
            time.sleep(0.01)  # Ensure mtime changes
            file_path.write_text("modified")
            
            snapshot2 = manager.create_snapshot(rootfs)
            diff = manager.compare_snapshots(snapshot1, snapshot2)
            
            assert not diff.is_empty()
            assert len(diff.modified) == 1
            assert Path("file.txt") in diff.modified
    
    def test_compare_with_deleted_files(self):
        """Test comparing snapshots with deleted files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir)
            (rootfs / "file1.txt").write_text("content1")
            (rootfs / "file2.txt").write_text("content2")
            
            manager = LayerDiffManager()
            snapshot1 = manager.create_snapshot(rootfs)
            
            # Delete file
            (rootfs / "file1.txt").unlink()
            
            snapshot2 = manager.create_snapshot(rootfs)
            diff = manager.compare_snapshots(snapshot1, snapshot2)
            
            assert not diff.is_empty()
            assert len(diff.deleted) == 1
            assert Path("file1.txt") in diff.deleted
    
    def test_compare_with_mixed_changes(self):
        """Test comparing snapshots with mixed changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir)
            (rootfs / "keep.txt").write_text("keep")
            (rootfs / "modify.txt").write_text("original")
            (rootfs / "delete.txt").write_text("delete")
            
            manager = LayerDiffManager()
            snapshot1 = manager.create_snapshot(rootfs)
            
            # Make changes
            import time
            time.sleep(0.01)
            (rootfs / "add.txt").write_text("new")
            (rootfs / "modify.txt").write_text("modified")
            (rootfs / "delete.txt").unlink()
            
            snapshot2 = manager.create_snapshot(rootfs)
            diff = manager.compare_snapshots(snapshot1, snapshot2)
            
            assert not diff.is_empty()
            assert len(diff.added) == 1
            assert len(diff.modified) == 1
            assert len(diff.deleted) == 1


class TestLayerCreation:
    """Tests for layer creation from diff."""
    
    def test_create_layer_with_added_files(self):
        """Test creating layer with added files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir)
            (rootfs / "new.txt").write_text("content")
            
            diff = FilesystemDiff(
                added=[Path("new.txt")],
                modified=[],
                deleted=[]
            )
            
            manager = LayerDiffManager()
            layer = manager.create_layer_from_diff(rootfs, diff, "RUN echo test")
            
            assert layer is not None
            assert layer.digest.startswith("sha256:")
            assert layer.diff_id.startswith("sha256:")
            assert layer.size > 0
            assert layer.content_path.exists()
    
    def test_create_layer_with_deleted_files(self):
        """Test creating layer with whiteout markers for deleted files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir)
            
            diff = FilesystemDiff(
                added=[],
                modified=[],
                deleted=[Path("deleted.txt")]
            )
            
            manager = LayerDiffManager()
            layer = manager.create_layer_from_diff(rootfs, diff, "RUN rm deleted.txt")
            
            assert layer is not None
            assert layer.content_path.exists()
            
            # Verify whiteout marker is in the tar
            with tarfile.open(layer.content_path, 'r:gz') as tar:
                names = tar.getnames()
                assert ".wh.deleted.txt" in names
    
    def test_create_layer_with_modified_files(self):
        """Test creating layer with modified files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir)
            (rootfs / "modified.txt").write_text("new content")
            
            diff = FilesystemDiff(
                added=[],
                modified=[Path("modified.txt")],
                deleted=[]
            )
            
            manager = LayerDiffManager()
            layer = manager.create_layer_from_diff(rootfs, diff, "RUN echo modified")
            
            assert layer is not None
            assert layer.content_path.exists()
            
            # Verify file is in the tar
            with tarfile.open(layer.content_path, 'r:gz') as tar:
                names = tar.getnames()
                assert "modified.txt" in names
    
    def test_create_layer_preserves_permissions(self):
        """Test that layer creation preserves file permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir)
            file_path = rootfs / "executable.sh"
            file_path.write_text("#!/bin/sh")
            file_path.chmod(0o755)
            
            diff = FilesystemDiff(
                added=[Path("executable.sh")],
                modified=[],
                deleted=[]
            )
            
            manager = LayerDiffManager()
            layer = manager.create_layer_from_diff(rootfs, diff, "RUN chmod +x")
            
            assert layer is not None
            
            # Verify permissions are preserved in tar
            with tarfile.open(layer.content_path, 'r:gz') as tar:
                member = tar.getmember("executable.sh")
                # Check that executable bit is set
                assert member.mode & 0o111 != 0


class TestEmptyDiffHandling:
    """Tests for empty diff handling."""
    
    def test_capture_diff_with_no_changes(self):
        """Test capturing diff when no changes occurred."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir)
            (rootfs / "file.txt").write_text("content")
            
            manager = LayerDiffManager()
            snapshot = manager.create_snapshot(rootfs)
            
            # No changes made
            layer = manager.capture_diff(rootfs, snapshot, "RUN true")
            
            assert layer is None
    
    def test_filesystem_diff_is_empty(self):
        """Test FilesystemDiff.is_empty() method."""
        empty_diff = FilesystemDiff(added=[], modified=[], deleted=[])
        assert empty_diff.is_empty()
        
        non_empty_diff = FilesystemDiff(added=[Path("file.txt")], modified=[], deleted=[])
        assert not non_empty_diff.is_empty()
    
    def test_filesystem_diff_total_changes(self):
        """Test FilesystemDiff.total_changes() method."""
        diff = FilesystemDiff(
            added=[Path("a.txt"), Path("b.txt")],
            modified=[Path("c.txt")],
            deleted=[Path("d.txt")]
        )
        assert diff.total_changes() == 4
    
    def test_filesystem_diff_get_changed_files(self):
        """Test FilesystemDiff.get_changed_files() method."""
        diff = FilesystemDiff(
            added=[Path("a.txt")],
            modified=[Path("b.txt")],
            deleted=[Path("c.txt")]
        )
        changed = diff.get_changed_files()
        assert len(changed) == 2
        assert Path("a.txt") in changed
        assert Path("b.txt") in changed
        assert Path("c.txt") not in changed  # Deleted files not in changed


class TestCaptureDiff:
    """Tests for the main capture_diff method."""
    
    def test_capture_diff_with_changes(self):
        """Test capturing diff with filesystem changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir)
            (rootfs / "existing.txt").write_text("existing")
            
            manager = LayerDiffManager()
            before_snapshot = manager.create_snapshot(rootfs)
            
            # Make changes
            (rootfs / "new.txt").write_text("new")
            
            layer = manager.capture_diff(rootfs, before_snapshot, "RUN touch new.txt")
            
            assert layer is not None
            assert layer.digest.startswith("sha256:")
            assert layer.content_path.exists()
    
    def test_capture_diff_error_handling(self):
        """Test error handling in capture_diff."""
        manager = LayerDiffManager()
        
        # Create a valid snapshot
        with tempfile.TemporaryDirectory() as tmpdir:
            rootfs = Path(tmpdir)
            snapshot = manager.create_snapshot(rootfs)
        
        # Try to capture diff with nonexistent rootfs
        with pytest.raises(FilesystemDiffError):
            manager.capture_diff(Path("/nonexistent"), snapshot, "RUN test")


class TestFileEntry:
    """Tests for FileEntry model."""
    
    def test_file_entry_equality(self):
        """Test FileEntry equality comparison."""
        entry1 = FileEntry(
            path=Path("file.txt"),
            size=100,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        
        entry2 = FileEntry(
            path=Path("file.txt"),
            size=100,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        
        assert entry1 == entry2
    
    def test_file_entry_is_modified(self):
        """Test FileEntry.is_modified() method."""
        entry1 = FileEntry(
            path=Path("file.txt"),
            size=100,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        
        entry2 = FileEntry(
            path=Path("file.txt"),
            size=200,  # Different size
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        
        assert entry1.is_modified(entry2)
    
    def test_file_entry_symlink_modified(self):
        """Test FileEntry.is_modified() for symlinks."""
        entry1 = FileEntry(
            path=Path("link.txt"),
            size=0,
            mtime=1234567890.0,
            mode=0o777,
            is_dir=False,
            is_symlink=True,
            link_target="target1.txt"
        )
        
        entry2 = FileEntry(
            path=Path("link.txt"),
            size=0,
            mtime=1234567890.0,
            mode=0o777,
            is_dir=False,
            is_symlink=True,
            link_target="target2.txt"  # Different target
        )
        
        assert entry1.is_modified(entry2)


class TestSnapshot:
    """Tests for Snapshot model."""
    
    def test_snapshot_add_file(self):
        """Test adding files to snapshot."""
        snapshot = Snapshot(timestamp=datetime.now())
        
        entry = FileEntry(
            path=Path("file.txt"),
            size=100,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        
        snapshot.add_file(entry)
        
        assert len(snapshot.files) == 1
        assert "file.txt" in snapshot.files
    
    def test_snapshot_get_file(self):
        """Test getting file from snapshot."""
        snapshot = Snapshot(timestamp=datetime.now())
        
        entry = FileEntry(
            path=Path("file.txt"),
            size=100,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        
        snapshot.add_file(entry)
        
        retrieved = snapshot.get_file(Path("file.txt"))
        assert retrieved == entry
    
    def test_snapshot_compare(self):
        """Test Snapshot.compare() method."""
        snapshot1 = Snapshot(timestamp=datetime.now())
        snapshot2 = Snapshot(timestamp=datetime.now())
        
        # Add file to first snapshot
        entry1 = FileEntry(
            path=Path("file1.txt"),
            size=100,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        snapshot1.add_file(entry1)
        
        # Add different file to second snapshot
        entry2 = FileEntry(
            path=Path("file2.txt"),
            size=200,
            mtime=1234567891.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        snapshot2.add_file(entry2)
        
        diff = snapshot1.compare(snapshot2)
        
        assert len(diff.added) == 1
        assert len(diff.deleted) == 1
        assert Path("file2.txt") in diff.added
        assert Path("file1.txt") in diff.deleted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
