"""
Unit tests for Editor Tool functionality.
"""

import hashlib
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock

import pytest

from src.cage.editor_tool import (
    EditorTool, FileOperation, OperationType, SelectorMode,
    FileOperationResult, FileLock, FileLockManager
)


class TestFileOperation:
    """Test FileOperation data model."""
    
    def test_file_operation_creation(self):
        """Test creating FileOperation."""
        operation = FileOperation(
            operation=OperationType.GET,
            path="test.py",
            selector={"mode": "region", "start": 1, "end": 10},
            payload={"content": "test"},
            intent="Test operation",
            dry_run=True,
            author="test-user",
            correlation_id="test-123"
        )
        
        assert operation.operation == OperationType.GET
        assert operation.path == "test.py"
        assert operation.selector == {"mode": "region", "start": 1, "end": 10}
        assert operation.payload == {"content": "test"}
        assert operation.intent == "Test operation"
        assert operation.dry_run is True
        assert operation.author == "test-user"
        assert operation.correlation_id == "test-123"
    
    def test_file_operation_defaults(self):
        """Test FileOperation with default values."""
        operation = FileOperation(
            operation=OperationType.GET,
            path="test.py"
        )
        
        assert operation.operation == OperationType.GET
        assert operation.path == "test.py"
        assert operation.selector is None
        assert operation.payload is None
        assert operation.intent == ""
        assert operation.dry_run is False
        assert operation.author == ""
        assert operation.correlation_id == ""


class TestFileOperationResult:
    """Test FileOperationResult data model."""
    
    def test_file_operation_result_creation(self):
        """Test creating FileOperationResult."""
        result = FileOperationResult(
            ok=True,
            file="test.py",
            operation="GET",
            lock_id="lock-123",
            pre_hash="abc123",
            post_hash="def456",
            diff="test diff",
            warnings=["warning1"],
            conflicts=["conflict1"],
            error="test error"
        )
        
        assert result.ok is True
        assert result.file == "test.py"
        assert result.operation == "GET"
        assert result.lock_id == "lock-123"
        assert result.pre_hash == "abc123"
        assert result.post_hash == "def456"
        assert result.diff == "test diff"
        assert result.warnings == ["warning1"]
        assert result.conflicts == ["conflict1"]
        assert result.error == "test error"
    
    def test_file_operation_result_post_init(self):
        """Test FileOperationResult post-init with None lists."""
        result = FileOperationResult(
            ok=True,
            file="test.py",
            operation="GET"
        )
        
        assert result.warnings == []
        assert result.conflicts == []


class TestFileLock:
    """Test FileLock data model."""
    
    def test_file_lock_creation(self):
        """Test creating FileLock."""
        lock = FileLock(
            file_path="test.py",
            lock_id="lock-123",
            agent="test-agent",
            started_at="2025-09-08T10:00:00",
            expires_at="2025-09-08T10:05:00",
            ranges=[{"start": 1, "end": 10}],
            description="Test lock"
        )
        
        assert lock.file_path == "test.py"
        assert lock.lock_id == "lock-123"
        assert lock.agent == "test-agent"
        assert lock.started_at == "2025-09-08T10:00:00"
        assert lock.expires_at == "2025-09-08T10:05:00"
        assert len(lock.ranges) == 1
        assert lock.ranges[0]["start"] == 1
        assert lock.ranges[0]["end"] == 10
        assert lock.description == "Test lock"


class TestFileLockManager:
    """Test FileLockManager functionality."""
    
    def test_file_lock_manager_initialization(self):
        """Test FileLockManager initialization."""
        manager = FileLockManager(lock_ttl=600)
        
        assert manager.lock_ttl == 600
        assert len(manager.locks) == 0
    
    def test_acquire_lock_success(self, file_lock_manager):
        """Test successful lock acquisition."""
        lock_id = file_lock_manager.acquire_lock(
            file_path="test.py",
            agent="test-agent",
            ranges=[{"start": 1, "end": 10}],
            description="Test lock"
        )
        
        assert lock_id is not None
        assert lock_id.startswith("lock:file:test.py:")
        assert "test.py" in file_lock_manager.locks
    
    def test_acquire_lock_conflict(self, file_lock_manager):
        """Test lock acquisition when file is already locked."""
        # Acquire first lock
        lock_id1 = file_lock_manager.acquire_lock(
            file_path="test.py",
            agent="agent1",
            ranges=[{"start": 1, "end": 10}],
            description="First lock"
        )
        
        assert lock_id1 is not None
        
        # Try to acquire second lock (should fail)
        lock_id2 = file_lock_manager.acquire_lock(
            file_path="test.py",
            agent="agent2",
            ranges=[{"start": 5, "end": 15}],
            description="Second lock"
        )
        
        assert lock_id2 is None
    
    def test_release_lock_success(self, file_lock_manager):
        """Test successful lock release."""
        lock_id = file_lock_manager.acquire_lock(
            file_path="test.py",
            agent="test-agent",
            ranges=[{"start": 1, "end": 10}],
            description="Test lock"
        )
        
        assert lock_id is not None
        
        # Release lock
        success = file_lock_manager.release_lock(lock_id)
        assert success is True
        assert "test.py" not in file_lock_manager.locks
    
    def test_release_lock_not_found(self, file_lock_manager):
        """Test releasing non-existent lock."""
        success = file_lock_manager.release_lock("nonexistent-lock")
        assert success is False
    
    def test_is_locked(self, file_lock_manager):
        """Test checking if file is locked."""
        # Initially not locked
        assert not file_lock_manager.is_locked("test.py")
        
        # Acquire lock
        lock_id = file_lock_manager.acquire_lock(
            file_path="test.py",
            agent="test-agent",
            ranges=[{"start": 1, "end": 10}],
            description="Test lock"
        )
        
        # Should be locked
        assert file_lock_manager.is_locked("test.py")
        
        # Release lock
        file_lock_manager.release_lock(lock_id)
        
        # Should not be locked
        assert not file_lock_manager.is_locked("test.py")
    
    def test_get_lock(self, file_lock_manager):
        """Test getting current lock for file."""
        # Initially no lock
        assert file_lock_manager.get_lock("test.py") is None
        
        # Acquire lock
        lock_id = file_lock_manager.acquire_lock(
            file_path="test.py",
            agent="test-agent",
            ranges=[{"start": 1, "end": 10}],
            description="Test lock"
        )
        
        # Should have lock
        lock = file_lock_manager.get_lock("test.py")
        assert lock is not None
        assert lock.lock_id == lock_id
        assert lock.agent == "test-agent"
    
    def test_lock_expiration(self, file_lock_manager):
        """Test lock expiration."""
        # Set very short TTL
        file_lock_manager.lock_ttl = 1
        
        lock_id = file_lock_manager.acquire_lock(
            file_path="test.py",
            agent="test-agent",
            ranges=[{"start": 1, "end": 10}],
            description="Test lock"
        )
        
        assert lock_id is not None
        
        # Wait for expiration
        import time
        time.sleep(2)
        
        # Lock should be expired
        assert not file_lock_manager.is_locked("test.py")
        assert file_lock_manager.get_lock("test.py") is None
    
    def test_cleanup_expired_locks(self, file_lock_manager):
        """Test cleanup of expired locks."""
        # Set very short TTL
        file_lock_manager.lock_ttl = 1
        
        lock_id = file_lock_manager.acquire_lock(
            file_path="test.py",
            agent="test-agent",
            ranges=[{"start": 1, "end": 10}],
            description="Test lock"
        )
        
        assert lock_id is not None
        assert "test.py" in file_lock_manager.locks
        
        # Wait for expiration
        import time
        time.sleep(2)
        
        # Cleanup expired locks
        file_lock_manager.cleanup_expired_locks()
        
        # Lock should be removed
        assert "test.py" not in file_lock_manager.locks


class TestEditorTool:
    """Test EditorTool functionality."""
    
    def test_editor_tool_initialization(self, temp_dir):
        """Test EditorTool initialization."""
        editor = EditorTool(Path(temp_dir))
        
        assert editor.repo_path == Path(temp_dir)
        assert isinstance(editor.lock_manager, FileLockManager)
        assert editor.task_manager is None
    
    def test_editor_tool_with_custom_lock_manager(self, temp_dir):
        """Test EditorTool with custom lock manager."""
        lock_manager = FileLockManager(lock_ttl=600)
        editor = EditorTool(Path(temp_dir), lock_manager=lock_manager)
        
        assert editor.lock_manager == lock_manager
        assert editor.lock_manager.lock_ttl == 600
    
    def test_get_file_path(self, editor_tool):
        """Test getting absolute file path from relative path."""
        file_path = editor_tool._get_file_path("test.py")
        
        assert file_path == editor_tool.repo_path / "test.py"
    
    def test_read_file_success(self, editor_tool, test_file):
        """Test successful file reading."""
        content, content_hash = editor_tool._read_file(editor_tool.repo_path / test_file)
        
        assert isinstance(content, str)
        assert len(content) > 0
        assert isinstance(content_hash, str)
        assert len(content_hash) == 64  # SHA256 hash length
        assert "#!/usr/bin/env python3" in content
    
    def test_read_file_not_found(self, editor_tool):
        """Test reading non-existent file."""
        with pytest.raises(FileNotFoundError):
            editor_tool._read_file(editor_tool.repo_path / "nonexistent.py")
    
    def test_write_file_success(self, editor_tool):
        """Test successful file writing."""
        content = "print('Hello, World!')"
        file_path = editor_tool.repo_path / "test_write.py"
        
        content_hash = editor_tool._write_file(file_path, content)
        
        assert isinstance(content_hash, str)
        assert len(content_hash) == 64
        assert file_path.exists()
        assert file_path.read_text() == content
    
    def test_write_file_create_directory(self, editor_tool):
        """Test file writing with directory creation."""
        content = "print('Hello, World!')"
        file_path = editor_tool.repo_path / "subdir" / "test.py"
        
        content_hash = editor_tool._write_file(file_path, content)
        
        assert file_path.exists()
        assert file_path.read_text() == content
        assert content_hash == hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def test_calculate_file_hash(self, editor_tool, test_file):
        """Test file hash calculation."""
        file_path = editor_tool.repo_path / test_file
        content_hash = editor_tool._calculate_file_hash(file_path)
        
        assert isinstance(content_hash, str)
        assert len(content_hash) == 64
        
        # Verify hash matches content
        with open(file_path, 'rb') as f:
            expected_hash = hashlib.sha256(f.read()).hexdigest()
        assert content_hash == expected_hash
    
    def test_calculate_file_hash_not_found(self, editor_tool):
        """Test hash calculation for non-existent file."""
        content_hash = editor_tool._calculate_file_hash(editor_tool.repo_path / "nonexistent.py")
        assert content_hash == ""
    
    def test_apply_region_selector(self, editor_tool, test_file_content):
        """Test region selector application."""
        selector = {"mode": "region", "start": 2, "end": 5}
        selected_content, start, end = editor_tool._apply_region_selector(test_file_content, selector)
        
        lines = test_file_content.splitlines(keepends=True)
        expected_content = ''.join(lines[1:4])  # Lines 2-4 (0-based indexing)
        
        assert selected_content == expected_content
        assert start > 0
        assert end > start
    
    def test_apply_region_selector_end_of_file(self, editor_tool, test_file_content):
        """Test region selector with end of file."""
        selector = {"mode": "region", "start": 5, "end": -1}
        selected_content, start, end = editor_tool._apply_region_selector(test_file_content, selector)
        
        lines = test_file_content.splitlines(keepends=True)
        expected_content = ''.join(lines[4:])  # Lines 5 to end
        
        assert selected_content == expected_content
    
    def test_apply_regex_selector(self, editor_tool, test_file_content):
        """Test regex selector application."""
        selector = {"mode": "regex", "pattern": r"def \w+", "flags": 0}
        selected_content, start, end = editor_tool._apply_regex_selector(test_file_content, selector)
        
        assert "def hello_world" in selected_content
        assert "def calculate_sum" in selected_content
        assert start >= 0
        assert end > start
    
    def test_apply_regex_selector_no_matches(self, editor_tool, test_file_content):
        """Test regex selector with no matches."""
        selector = {"mode": "regex", "pattern": r"nonexistent_function", "flags": 0}
        selected_content, start, end = editor_tool._apply_regex_selector(test_file_content, selector)
        
        assert selected_content == ""
        assert start == 0
        assert end == 0
    
    def test_apply_regex_selector_invalid_pattern(self, editor_tool, test_file_content):
        """Test regex selector with invalid pattern."""
        selector = {"mode": "regex", "pattern": r"[invalid", "flags": 0}
        
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            editor_tool._apply_regex_selector(test_file_content, selector)
    
    def test_apply_selector_region(self, editor_tool, test_file_content):
        """Test selector application with region mode."""
        selector = {"mode": "region", "start": 1, "end": 3}
        selected_content, start, end = editor_tool._apply_selector(test_file_content, selector)
        
        assert selected_content is not None
        assert start >= 0
        assert end > start
    
    def test_apply_selector_regex(self, editor_tool, test_file_content):
        """Test selector application with regex mode."""
        selector = {"mode": "regex", "pattern": r"def \w+", "flags": 0}
        selected_content, start, end = editor_tool._apply_selector(test_file_content, selector)
        
        assert selected_content is not None
        assert start >= 0
        assert end > start
    
    def test_apply_selector_invalid_mode(self, editor_tool, test_file_content):
        """Test selector application with invalid mode."""
        selector = {"mode": "invalid", "start": 1, "end": 3}
        
        with pytest.raises(ValueError, match="Unsupported selector mode"):
            editor_tool._apply_selector(test_file_content, selector)
    
    def test_generate_diff(self, editor_tool):
        """Test diff generation."""
        old_content = "line1\nline2\nline3\n"
        new_content = "line1\nmodified line2\nline3\n"
        
        diff = editor_tool._generate_diff(old_content, new_content, start_line=1)
        
        assert isinstance(diff, str)
        assert "@@" in diff
        assert "-line2" in diff
        assert "+modified line2" in diff
    
    def test_get_file_operation_success(self, editor_tool, test_file):
        """Test successful GET operation."""
        operation = FileOperation(
            operation=OperationType.GET,
            path=test_file,
            author="test-user",
            correlation_id="test-get"
        )
        
        result = editor_tool.get_file(operation)
        
        assert result.ok is True
        assert result.file == test_file
        assert result.operation == "GET"
        assert result.pre_hash is not None
        assert result.diff is not None
        assert "#!/usr/bin/env python3" in result.diff
    
    def test_get_file_operation_with_selector(self, editor_tool, test_file):
        """Test GET operation with selector."""
        operation = FileOperation(
            operation=OperationType.GET,
            path=test_file,
            selector={"mode": "region", "start": 1, "end": 5},
            author="test-user",
            correlation_id="test-get-selector"
        )
        
        result = editor_tool.get_file(operation)
        
        assert result.ok is True
        assert result.file == test_file
        assert result.operation == "GET"
        assert result.diff is not None
        # Should only contain first 5 lines
        lines = result.diff.splitlines()
        assert len(lines) <= 5
    
    def test_get_file_operation_not_found(self, editor_tool):
        """Test GET operation on non-existent file."""
        operation = FileOperation(
            operation=OperationType.GET,
            path="nonexistent.py",
            author="test-user",
            correlation_id="test-get-not-found"
        )
        
        result = editor_tool.get_file(operation)
        
        assert result.ok is False
        assert result.file == "nonexistent.py"
        assert result.operation == "GET"
        assert "File not found" in result.error
    
    def test_insert_file_operation_new_file(self, editor_tool):
        """Test INSERT operation creating new file."""
        operation = FileOperation(
            operation=OperationType.INSERT,
            path="new_file.py",
            payload={"content": "print('Hello, World!')\n"},
            author="test-user",
            correlation_id="test-insert-new"
        )
        
        result = editor_tool.insert_file(operation)
        
        assert result.ok is True
        assert result.file == "new_file.py"
        assert result.operation == "INSERT"
        assert result.post_hash is not None
        assert result.diff is not None
        
        # Verify file was created
        file_path = editor_tool.repo_path / "new_file.py"
        assert file_path.exists()
        assert file_path.read_text() == "print('Hello, World!')\n"
    
    def test_insert_file_operation_existing_file(self, editor_tool, test_file):
        """Test INSERT operation on existing file."""
        operation = FileOperation(
            operation=OperationType.INSERT,
            path=test_file,
            payload={"content": "# New comment\n"},
            author="test-user",
            correlation_id="test-insert-existing"
        )
        
        result = editor_tool.insert_file(operation)
        
        assert result.ok is True
        assert result.file == test_file
        assert result.operation == "INSERT"
        assert result.pre_hash is not None
        assert result.post_hash is not None
        assert result.diff is not None
        
        # Verify content was appended
        file_path = editor_tool.repo_path / test_file
        content = file_path.read_text()
        assert "# New comment" in content
    
    def test_insert_file_operation_with_selector(self, editor_tool, test_file):
        """Test INSERT operation with selector."""
        operation = FileOperation(
            operation=OperationType.INSERT,
            path=test_file,
            selector={"mode": "region", "start": 3, "end": 3},
            payload={"content": "# Inserted comment\n"},
            author="test-user",
            correlation_id="test-insert-selector"
        )
        
        result = editor_tool.insert_file(operation)
        
        assert result.ok is True
        assert result.file == test_file
        assert result.operation == "INSERT"
    
    def test_insert_file_operation_no_content(self, editor_tool, test_file):
        """Test INSERT operation without content."""
        operation = FileOperation(
            operation=OperationType.INSERT,
            path=test_file,
            payload={},
            author="test-user",
            correlation_id="test-insert-no-content"
        )
        
        result = editor_tool.insert_file(operation)
        
        assert result.ok is False
        assert "Content required" in result.error
    
    def test_update_file_operation_success(self, editor_tool, test_file):
        """Test successful UPDATE operation."""
        operation = FileOperation(
            operation=OperationType.UPDATE,
            path=test_file,
            selector={"mode": "region", "start": 1, "end": 3},
            payload={"content": "# Updated header\n# New comment\n"},
            author="test-user",
            correlation_id="test-update"
        )
        
        result = editor_tool.update_file(operation)
        
        assert result.ok is True
        assert result.file == test_file
        assert result.operation == "UPDATE"
        assert result.pre_hash is not None
        assert result.post_hash is not None
        assert result.diff is not None
    
    def test_update_file_operation_not_found(self, editor_tool):
        """Test UPDATE operation on non-existent file."""
        operation = FileOperation(
            operation=OperationType.UPDATE,
            path="nonexistent.py",
            payload={"content": "print('Hello')\n"},
            author="test-user",
            correlation_id="test-update-not-found"
        )
        
        result = editor_tool.update_file(operation)
        
        assert result.ok is False
        assert "File not found" in result.error
    
    def test_update_file_operation_stale_preimage(self, editor_tool, test_file):
        """Test UPDATE operation with stale preimage."""
        # First, get the current hash
        get_operation = FileOperation(
            operation=OperationType.GET,
            path=test_file,
            author="test-user",
            correlation_id="test-get-hash"
        )
        get_result = editor_tool.get_file(get_operation)
        current_hash = get_result.pre_hash
        
        # Modify file externally
        file_path = editor_tool.repo_path / test_file
        original_content = file_path.read_text()
        file_path.write_text(original_content + "# External change\n")
        
        # Try to update with old hash
        operation = FileOperation(
            operation=OperationType.UPDATE,
            path=test_file,
            payload={"content": "print('Updated')\n", "pre_hash": current_hash},
            author="test-user",
            correlation_id="test-update-stale"
        )
        
        result = editor_tool.update_file(operation)
        
        assert result.ok is False
        assert "Stale preimage detected" in result.error
    
    def test_delete_file_operation_region(self, editor_tool, test_file):
        """Test DELETE operation on specific region."""
        operation = FileOperation(
            operation=OperationType.DELETE,
            path=test_file,
            selector={"mode": "region", "start": 1, "end": 3},
            author="test-user",
            correlation_id="test-delete-region"
        )
        
        result = editor_tool.delete_file(operation)
        
        assert result.ok is True
        assert result.file == test_file
        assert result.operation == "DELETE"
        assert result.pre_hash is not None
        assert result.post_hash is not None
        assert result.diff is not None
    
    def test_delete_file_operation_entire_file(self, editor_tool, test_file):
        """Test DELETE operation on entire file."""
        operation = FileOperation(
            operation=OperationType.DELETE,
            path=test_file,
            author="test-user",
            correlation_id="test-delete-file"
        )
        
        result = editor_tool.delete_file(operation)
        
        assert result.ok is True
        assert result.file == test_file
        assert result.operation == "DELETE"
        assert result.post_hash == ""
        
        # Verify file was deleted
        file_path = editor_tool.repo_path / test_file
        assert not file_path.exists()
    
    def test_delete_file_operation_not_found(self, editor_tool):
        """Test DELETE operation on non-existent file."""
        operation = FileOperation(
            operation=OperationType.DELETE,
            path="nonexistent.py",
            author="test-user",
            correlation_id="test-delete-not-found"
        )
        
        result = editor_tool.delete_file(operation)
        
        assert result.ok is False
        assert "File not found" in result.error
    
    def test_execute_operation_get(self, editor_tool, test_file):
        """Test execute_operation with GET."""
        operation = FileOperation(
            operation=OperationType.GET,
            path=test_file,
            author="test-user",
            correlation_id="test-execute-get"
        )
        
        result = editor_tool.execute_operation(operation)
        
        assert result.ok is True
        assert result.file == test_file
        assert result.operation == "GET"
    
    def test_execute_operation_insert(self, editor_tool):
        """Test execute_operation with INSERT."""
        operation = FileOperation(
            operation=OperationType.INSERT,
            path="new_file.py",
            payload={"content": "print('Hello')\n"},
            author="test-user",
            correlation_id="test-execute-insert"
        )
        
        result = editor_tool.execute_operation(operation)
        
        assert result.ok is True
        assert result.file == "new_file.py"
        assert result.operation == "INSERT"
    
    def test_execute_operation_update(self, editor_tool, test_file):
        """Test execute_operation with UPDATE."""
        operation = FileOperation(
            operation=OperationType.UPDATE,
            path=test_file,
            payload={"content": "print('Updated')\n"},
            author="test-user",
            correlation_id="test-execute-update"
        )
        
        result = editor_tool.execute_operation(operation)
        
        assert result.ok is True
        assert result.file == test_file
        assert result.operation == "UPDATE"
    
    def test_execute_operation_delete(self, editor_tool, test_file):
        """Test execute_operation with DELETE."""
        operation = FileOperation(
            operation=OperationType.DELETE,
            path=test_file,
            author="test-user",
            correlation_id="test-execute-delete"
        )
        
        result = editor_tool.execute_operation(operation)
        
        assert result.ok is True
        assert result.file == test_file
        assert result.operation == "DELETE"
    
    def test_execute_operation_dry_run(self, editor_tool, test_file):
        """Test execute_operation in dry run mode."""
        operation = FileOperation(
            operation=OperationType.UPDATE,
            path=test_file,
            payload={"content": "print('Updated')\n"},
            dry_run=True,
            author="test-user",
            correlation_id="test-execute-dry-run"
        )
        
        # Get original content
        original_content = (editor_tool.repo_path / test_file).read_text()
        
        result = editor_tool.execute_operation(operation)
        
        assert result.ok is True
        assert result.file == test_file
        assert result.operation == "UPDATE"
        
        # Verify file was not actually modified
        current_content = (editor_tool.repo_path / test_file).read_text()
        assert current_content == original_content
    
    def test_execute_operation_locking(self, editor_tool, test_file):
        """Test execute_operation with file locking."""
        operation = FileOperation(
            operation=OperationType.UPDATE,
            path=test_file,
            payload={"content": "print('Updated')\n"},
            author="test-user",
            correlation_id="test-execute-locking"
        )
        
        result = editor_tool.execute_operation(operation)
        
        assert result.ok is True
        assert result.lock_id is not None
        assert result.lock_id.startswith("lock:file:")
    
    def test_execute_operation_invalid_type(self, editor_tool, test_file):
        """Test execute_operation with invalid operation type."""
        operation = FileOperation(
            operation="INVALID",  # This should cause an error
            path=test_file,
            author="test-user",
            correlation_id="test-execute-invalid"
        )
        
        # This should raise an exception during operation creation
        with pytest.raises(ValueError):
            OperationType("INVALID")
    
    def test_cleanup_expired_locks(self, editor_tool):
        """Test cleanup of expired locks."""
        editor_tool.cleanup_expired_locks()
        # Should not raise any exceptions
    
    @patch('src.cage.editor_tool.logger')
    def test_log_operation_with_task_manager(self, mock_logger, editor_tool, mock_task_manager, test_file):
        """Test operation logging with task manager."""
        editor_tool.task_manager = mock_task_manager
        
        operation = FileOperation(
            operation=OperationType.GET,
            path=test_file,
            correlation_id="task-123-get",
            author="test-user"
        )
        
        result = FileOperationResult(
            ok=True,
            file=test_file,
            operation="GET",
            pre_hash="abc123"
        )
        
        editor_tool._log_operation(operation, result)
        
        # Verify task manager was called
        mock_task_manager.load_task.assert_called_once_with("123")
    
    @patch('src.cage.editor_tool.logger')
    def test_log_operation_without_task_manager(self, mock_logger, editor_tool, test_file):
        """Test operation logging without task manager."""
        editor_tool.task_manager = None
        
        operation = FileOperation(
            operation=OperationType.GET,
            path=test_file,
            correlation_id="task-123-get",
            author="test-user"
        )
        
        result = FileOperationResult(
            ok=True,
            file=test_file,
            operation="GET",
            pre_hash="abc123"
        )
        
        # Should not raise any exceptions
        editor_tool._log_operation(operation, result)
    
    @patch('src.cage.editor_tool.logger')
    def test_log_operation_without_correlation_id(self, mock_logger, editor_tool, mock_task_manager, test_file):
        """Test operation logging without correlation ID."""
        editor_tool.task_manager = mock_task_manager
        
        operation = FileOperation(
            operation=OperationType.GET,
            path=test_file,
            correlation_id="",
            author="test-user"
        )
        
        result = FileOperationResult(
            ok=True,
            file=test_file,
            operation="GET",
            pre_hash="abc123"
        )
        
        editor_tool._log_operation(operation, result)
        
        # Task manager should not be called
        mock_task_manager.load_task.assert_not_called()

