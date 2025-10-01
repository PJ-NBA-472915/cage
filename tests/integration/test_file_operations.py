"""
Integration tests for file operations.
Tests that require file system operations and external dependencies.
"""

import os
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestFileOperations:
    """Integration tests for file operations."""

    @pytest.fixture  # type: ignore[misc]
    def temp_dir(self) -> Generator[Path, None, None]:
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.mark.smoke  # type: ignore[misc]
    def test_create_and_read_file(self, temp_dir: Path) -> None:
        """Test creating and reading a file."""
        test_file = temp_dir / "test.txt"
        content = "Hello, World!"

        # Create file
        test_file.write_text(content)
        assert test_file.exists()

        # Read file
        read_content = test_file.read_text()
        assert read_content == content

    def test_file_permissions(self, temp_dir: Path) -> None:
        """Test file permissions."""
        test_file = temp_dir / "permissions_test.txt"
        test_file.write_text("test")

        # Check if file is readable
        assert os.access(test_file, os.R_OK)

        # Check if file is writable
        assert os.access(test_file, os.W_OK)

    @pytest.mark.slow  # type: ignore[misc]
    def test_large_file_operations(self, temp_dir: Path) -> None:
        """Test operations with large files."""
        large_file = temp_dir / "large.txt"
        large_content = "x" * 1000000  # 1MB of data

        # Write large file
        large_file.write_text(large_content)
        assert large_file.exists()
        assert large_file.stat().st_size == 1000000

        # Read large file
        read_content = large_file.read_text()
        assert len(read_content) == 1000000

    def test_directory_operations(self, temp_dir: Path) -> None:
        """Test directory creation and listing."""
        subdir = temp_dir / "subdir"
        subdir.mkdir()

        assert subdir.exists()
        assert subdir.is_dir()

        # Create files in subdirectory
        (subdir / "file1.txt").write_text("file1")
        (subdir / "file2.txt").write_text("file2")

        # List files
        files = list(subdir.iterdir())
        assert len(files) == 2
        assert any(f.name == "file1.txt" for f in files)
        assert any(f.name == "file2.txt" for f in files)

    @pytest.mark.parametrize("file_count", [1, 5, 10, 100])  # type: ignore[misc]
    def test_multiple_file_creation(self, temp_dir: Path, file_count: int) -> None:
        """Test creating multiple files."""
        for i in range(file_count):
            test_file = temp_dir / f"file_{i}.txt"
            test_file.write_text(f"content_{i}")
            assert test_file.exists()

        # Verify all files exist
        files = list(temp_dir.glob("file_*.txt"))
        assert len(files) == file_count
