"""Tests for build isolation models."""

import pytest
from pathlib import Path
from datetime import datetime
from derpy.build.models import (
    ImageReference,
    FileEntry,
    Snapshot,
    FilesystemDiff,
    ExecutionResult,
)


class TestImageReference:
    """Tests for ImageReference model."""
    
    def test_parse_simple_image(self):
        """Test parsing simple image reference."""
        ref = ImageReference.parse("ubuntu")
        assert ref.registry == "docker.io"
        assert ref.repository == "library/ubuntu"
        assert ref.tag == "latest"
        assert ref.digest is None
    
    def test_parse_image_with_tag(self):
        """Test parsing image reference with tag."""
        ref = ImageReference.parse("ubuntu:22.04")
        assert ref.registry == "docker.io"
        assert ref.repository == "library/ubuntu"
        assert ref.tag == "22.04"
        assert ref.digest is None
    
    def test_parse_image_with_registry(self):
        """Test parsing image reference with registry."""
        ref = ImageReference.parse("ghcr.io/org/app:v1.0")
        assert ref.registry == "ghcr.io"
        assert ref.repository == "org/app"
        assert ref.tag == "v1.0"
        assert ref.digest is None
    
    def test_parse_image_with_digest(self):
        """Test parsing image reference with digest."""
        ref = ImageReference.parse("ubuntu@sha256:abc123")
        assert ref.registry == "docker.io"
        assert ref.repository == "library/ubuntu"
        assert ref.tag == "latest"
        assert ref.digest == "sha256:abc123"
    
    def test_parse_image_with_tag_and_digest(self):
        """Test parsing image reference with both tag and digest."""
        ref = ImageReference.parse("ubuntu:22.04@sha256:abc123")
        assert ref.registry == "docker.io"
        assert ref.repository == "library/ubuntu"
        assert ref.tag == "22.04"
        assert ref.digest == "sha256:abc123"
    
    def test_parse_localhost_registry(self):
        """Test parsing image with localhost registry."""
        ref = ImageReference.parse("localhost:5000/myapp:latest")
        assert ref.registry == "localhost:5000"
        assert ref.repository == "myapp"
        assert ref.tag == "latest"
    
    def test_parse_non_official_image(self):
        """Test parsing non-official Docker Hub image."""
        ref = ImageReference.parse("myuser/myapp:v1")
        assert ref.registry == "docker.io"
        assert ref.repository == "myuser/myapp"
        assert ref.tag == "v1"
    
    def test_parse_empty_reference(self):
        """Test parsing empty reference raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ImageReference.parse("")
    
    def test_parse_invalid_digest(self):
        """Test parsing invalid digest format raises error."""
        with pytest.raises(ValueError, match="Invalid digest format"):
            ImageReference.parse("ubuntu@md5:abc123")
    
    def test_parse_invalid_tag(self):
        """Test parsing invalid tag format raises error."""
        with pytest.raises(ValueError, match="Invalid tag format"):
            ImageReference.parse("ubuntu:invalid tag!")
    
    def test_to_string_simple(self):
        """Test converting simple reference to string."""
        ref = ImageReference(
            registry="docker.io",
            repository="library/ubuntu",
            tag="latest"
        )
        assert ref.to_string() == "ubuntu:latest"
    
    def test_to_string_with_tag(self):
        """Test converting reference with tag to string."""
        ref = ImageReference(
            registry="docker.io",
            repository="library/ubuntu",
            tag="22.04"
        )
        assert ref.to_string() == "ubuntu:22.04"
    
    def test_to_string_with_registry(self):
        """Test converting reference with registry to string."""
        ref = ImageReference(
            registry="ghcr.io",
            repository="org/app",
            tag="v1.0"
        )
        assert ref.to_string() == "ghcr.io/org/app:v1.0"
    
    def test_to_string_with_digest(self):
        """Test converting reference with digest to string."""
        ref = ImageReference(
            registry="docker.io",
            repository="library/ubuntu",
            tag="latest",
            digest="sha256:abc123"
        )
        assert ref.to_string() == "ubuntu@sha256:abc123"
    
    def test_to_string_include_registry(self):
        """Test converting reference with include_registry flag."""
        ref = ImageReference(
            registry="docker.io",
            repository="library/ubuntu",
            tag="latest"
        )
        assert ref.to_string(include_registry=True) == "docker.io/library/ubuntu:latest"
    
    def test_str_representation(self):
        """Test string representation."""
        ref = ImageReference.parse("ubuntu:22.04")
        assert str(ref) == "ubuntu:22.04"


class TestFileEntry:
    """Tests for FileEntry model."""
    
    def test_create_file_entry(self):
        """Test creating a file entry."""
        entry = FileEntry(
            path=Path("/test/file.txt"),
            size=1024,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        assert entry.path == Path("/test/file.txt")
        assert entry.size == 1024
        assert entry.mtime == 1234567890.0
        assert entry.mode == 0o644
        assert not entry.is_dir
        assert not entry.is_symlink
    
    def test_file_entry_equality(self):
        """Test file entry equality comparison."""
        entry1 = FileEntry(
            path=Path("/test/file.txt"),
            size=1024,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        entry2 = FileEntry(
            path=Path("/test/file.txt"),
            size=1024,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        assert entry1 == entry2
    
    def test_file_entry_inequality(self):
        """Test file entry inequality."""
        entry1 = FileEntry(
            path=Path("/test/file.txt"),
            size=1024,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        entry2 = FileEntry(
            path=Path("/test/file.txt"),
            size=2048,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        assert entry1 != entry2
    
    def test_is_modified_same_file(self):
        """Test is_modified with identical files."""
        entry1 = FileEntry(
            path=Path("/test/file.txt"),
            size=1024,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        entry2 = FileEntry(
            path=Path("/test/file.txt"),
            size=1024,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        assert not entry1.is_modified(entry2)
    
    def test_is_modified_different_size(self):
        """Test is_modified with different size."""
        entry1 = FileEntry(
            path=Path("/test/file.txt"),
            size=1024,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        entry2 = FileEntry(
            path=Path("/test/file.txt"),
            size=2048,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        assert entry1.is_modified(entry2)
    
    def test_is_modified_different_mtime(self):
        """Test is_modified with different mtime."""
        entry1 = FileEntry(
            path=Path("/test/file.txt"),
            size=1024,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        entry2 = FileEntry(
            path=Path("/test/file.txt"),
            size=1024,
            mtime=9876543210.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        assert entry1.is_modified(entry2)
    
    def test_is_modified_different_type(self):
        """Test is_modified with different file type."""
        entry1 = FileEntry(
            path=Path("/test/file.txt"),
            size=1024,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        entry2 = FileEntry(
            path=Path("/test/file.txt"),
            size=1024,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=True,
            is_symlink=False
        )
        assert entry1.is_modified(entry2)
    
    def test_is_modified_symlink(self):
        """Test is_modified with symlinks."""
        entry1 = FileEntry(
            path=Path("/test/link"),
            size=0,
            mtime=1234567890.0,
            mode=0o777,
            is_dir=False,
            is_symlink=True,
            link_target="/target1"
        )
        entry2 = FileEntry(
            path=Path("/test/link"),
            size=0,
            mtime=1234567890.0,
            mode=0o777,
            is_dir=False,
            is_symlink=True,
            link_target="/target2"
        )
        assert entry1.is_modified(entry2)
    
    def test_is_modified_different_path(self):
        """Test is_modified with different paths."""
        entry1 = FileEntry(
            path=Path("/test/file1.txt"),
            size=1024,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        entry2 = FileEntry(
            path=Path("/test/file2.txt"),
            size=1024,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        assert not entry1.is_modified(entry2)


class TestSnapshot:
    """Tests for Snapshot model."""
    
    def test_create_snapshot(self):
        """Test creating a snapshot."""
        timestamp = datetime.now()
        snapshot = Snapshot(timestamp=timestamp)
        assert snapshot.timestamp == timestamp
        assert len(snapshot.files) == 0
    
    def test_add_file(self):
        """Test adding file to snapshot."""
        snapshot = Snapshot(timestamp=datetime.now())
        entry = FileEntry(
            path=Path("/test/file.txt"),
            size=1024,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        snapshot.add_file(entry)
        assert len(snapshot.files) == 1
        assert "/test/file.txt" in snapshot.files
    
    def test_get_file(self):
        """Test getting file from snapshot."""
        snapshot = Snapshot(timestamp=datetime.now())
        entry = FileEntry(
            path=Path("/test/file.txt"),
            size=1024,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        snapshot.add_file(entry)
        retrieved = snapshot.get_file(Path("/test/file.txt"))
        assert retrieved == entry
    
    def test_get_file_not_found(self):
        """Test getting non-existent file returns None."""
        snapshot = Snapshot(timestamp=datetime.now())
        retrieved = snapshot.get_file(Path("/nonexistent.txt"))
        assert retrieved is None
    
    def test_compare_no_changes(self):
        """Test comparing identical snapshots."""
        snapshot1 = Snapshot(timestamp=datetime.now())
        entry = FileEntry(
            path=Path("/test/file.txt"),
            size=1024,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        snapshot1.add_file(entry)
        
        snapshot2 = Snapshot(timestamp=datetime.now())
        snapshot2.add_file(entry)
        
        diff = snapshot1.compare(snapshot2)
        assert diff.is_empty()
    
    def test_compare_added_files(self):
        """Test comparing snapshots with added files."""
        snapshot1 = Snapshot(timestamp=datetime.now())
        
        snapshot2 = Snapshot(timestamp=datetime.now())
        entry = FileEntry(
            path=Path("/test/new.txt"),
            size=1024,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        snapshot2.add_file(entry)
        
        diff = snapshot1.compare(snapshot2)
        assert len(diff.added) == 1
        assert Path("/test/new.txt") in diff.added
        assert len(diff.modified) == 0
        assert len(diff.deleted) == 0
    
    def test_compare_deleted_files(self):
        """Test comparing snapshots with deleted files."""
        snapshot1 = Snapshot(timestamp=datetime.now())
        entry = FileEntry(
            path=Path("/test/old.txt"),
            size=1024,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        snapshot1.add_file(entry)
        
        snapshot2 = Snapshot(timestamp=datetime.now())
        
        diff = snapshot1.compare(snapshot2)
        assert len(diff.added) == 0
        assert len(diff.modified) == 0
        assert len(diff.deleted) == 1
        assert Path("/test/old.txt") in diff.deleted
    
    def test_compare_modified_files(self):
        """Test comparing snapshots with modified files."""
        snapshot1 = Snapshot(timestamp=datetime.now())
        entry1 = FileEntry(
            path=Path("/test/file.txt"),
            size=1024,
            mtime=1234567890.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        snapshot1.add_file(entry1)
        
        snapshot2 = Snapshot(timestamp=datetime.now())
        entry2 = FileEntry(
            path=Path("/test/file.txt"),
            size=2048,
            mtime=9876543210.0,
            mode=0o644,
            is_dir=False,
            is_symlink=False
        )
        snapshot2.add_file(entry2)
        
        diff = snapshot1.compare(snapshot2)
        assert len(diff.added) == 0
        assert len(diff.modified) == 1
        assert Path("/test/file.txt") in diff.modified
        assert len(diff.deleted) == 0


class TestFilesystemDiff:
    """Tests for FilesystemDiff model."""
    
    def test_create_empty_diff(self):
        """Test creating empty diff."""
        diff = FilesystemDiff()
        assert diff.is_empty()
        assert len(diff.added) == 0
        assert len(diff.modified) == 0
        assert len(diff.deleted) == 0
    
    def test_create_diff_with_changes(self):
        """Test creating diff with changes."""
        diff = FilesystemDiff(
            added=[Path("/new.txt")],
            modified=[Path("/changed.txt")],
            deleted=[Path("/removed.txt")]
        )
        assert not diff.is_empty()
        assert len(diff.added) == 1
        assert len(diff.modified) == 1
        assert len(diff.deleted) == 1
    
    def test_get_changed_files(self):
        """Test getting changed files."""
        diff = FilesystemDiff(
            added=[Path("/new.txt")],
            modified=[Path("/changed.txt")],
            deleted=[Path("/removed.txt")]
        )
        changed = diff.get_changed_files()
        assert len(changed) == 2
        assert Path("/new.txt") in changed
        assert Path("/changed.txt") in changed
        assert Path("/removed.txt") not in changed
    
    def test_total_changes(self):
        """Test total changes count."""
        diff = FilesystemDiff(
            added=[Path("/new1.txt"), Path("/new2.txt")],
            modified=[Path("/changed.txt")],
            deleted=[Path("/removed.txt")]
        )
        assert diff.total_changes() == 4
    
    def test_str_representation(self):
        """Test string representation."""
        diff = FilesystemDiff(
            added=[Path("/new.txt")],
            modified=[Path("/changed.txt")],
            deleted=[Path("/removed.txt")]
        )
        str_repr = str(diff)
        assert "added=1" in str_repr
        assert "modified=1" in str_repr
        assert "deleted=1" in str_repr


class TestExecutionResult:
    """Tests for ExecutionResult model."""
    
    def test_create_success_result(self):
        """Test creating successful execution result."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Success output",
            stderr="",
            duration=1.5,
            command="echo test"
        )
        assert result.is_success()
        assert not result.is_failure()
        assert result.exit_code == 0
        assert result.stdout == "Success output"
        assert result.duration == 1.5
    
    def test_create_failure_result(self):
        """Test creating failed execution result."""
        result = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error message",
            duration=0.5,
            command="false"
        )
        assert not result.is_success()
        assert result.is_failure()
        assert result.exit_code == 1
        assert result.stderr == "Error message"
    
    def test_get_output_stdout_only(self):
        """Test getting output with stdout only."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Output",
            stderr="",
            duration=1.0
        )
        assert result.get_output() == "Output"
    
    def test_get_output_stderr_only(self):
        """Test getting output with stderr only."""
        result = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error",
            duration=1.0
        )
        assert result.get_output() == "Error"
    
    def test_get_output_both(self):
        """Test getting output with both stdout and stderr."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Output",
            stderr="Warning",
            duration=1.0
        )
        output = result.get_output()
        assert "Output" in output
        assert "Warning" in output
    
    def test_str_representation_success(self):
        """Test string representation for success."""
        result = ExecutionResult(
            exit_code=0,
            stdout="",
            stderr="",
            duration=1.23
        )
        str_repr = str(result)
        assert "SUCCESS" in str_repr
        assert "1.23" in str_repr
    
    def test_str_representation_failure(self):
        """Test string representation for failure."""
        result = ExecutionResult(
            exit_code=127,
            stdout="",
            stderr="",
            duration=0.5
        )
        str_repr = str(result)
        assert "FAILED" in str_repr
        assert "127" in str_repr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
