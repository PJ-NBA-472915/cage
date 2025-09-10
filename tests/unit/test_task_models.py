"""
Unit tests for Task Manager data models and functionality.
"""

import json
import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

from src.cage.task_models import (
    TaskFile, TaskCriteria, TaskTodoItem, TaskChangelogEntry,
    TaskPrompt, TaskLock, TaskMigration, TaskManager
)


class TestTaskFile:
    """Test TaskFile data model."""
    
    def test_task_file_creation(self, sample_task_data):
        """Test creating a TaskFile from valid data."""
        task = TaskFile(**sample_task_data)
        
        assert task.id == "2025-09-10-test-task"
        assert task.title == "Test Task"
        assert task.owner == "test-user"
        assert task.status == "in-progress"
        assert task.progress_percent == 50
        assert len(task.tags) == 2
        assert "test" in task.tags
        assert "example" in task.tags
    
    def test_task_file_validation(self):
        """Test TaskFile validation with invalid data."""
        with pytest.raises(ValueError):
            TaskFile(
                id="invalid-id",  # Invalid format
                title="Test Task",
                owner="test-user",
                status="invalid-status",  # Invalid status
                created_at="2025-09-08T10:00:00",
                updated_at="2025-09-08T10:00:00",
                progress_percent=150  # Invalid progress
            )
    
    def test_task_file_defaults(self):
        """Test TaskFile with minimal required fields."""
        task = TaskFile(
            id="2025-09-08-minimal-task",
            title="Minimal Task",
            owner="test-user",
            status="planned",
            created_at="2025-09-08T10:00:00",
            updated_at="2025-09-08T10:00:00",
            progress_percent=0
        )
        
        assert task.tags == []
        assert task.summary == ""
        assert task.success_criteria == []
        assert task.acceptance_checks == []
        assert task.subtasks == []
        assert task.todo == []
        assert task.changelog == []
        assert task.decisions == []
        assert task.lessons_learned == []
        assert task.issues_risks == []
        assert task.next_steps == []
        assert task.references == []
        assert task.prompts == []
        assert task.locks == []
        assert task.migration.migrated is False
        assert task.metadata == {}
    
    def test_task_file_serialization(self, sample_task_data):
        """Test TaskFile serialization to dict."""
        task = TaskFile(**sample_task_data)
        task_dict = task.model_dump()
        
        assert isinstance(task_dict, dict)
        assert task_dict["id"] == task.id
        assert task_dict["title"] == task.title
        assert task_dict["status"] == task.status
    
    def test_task_file_deserialization(self, sample_task_data):
        """Test TaskFile deserialization from dict."""
        task = TaskFile.model_validate(sample_task_data)
        
        assert isinstance(task, TaskFile)
        assert task.id == sample_task_data["id"]
        assert task.title == sample_task_data["title"]


class TestTaskCriteria:
    """Test TaskCriteria data model."""
    
    def test_task_criteria_creation(self):
        """Test creating TaskCriteria."""
        criteria = TaskCriteria(text="Test criteria", checked=True)
        
        assert criteria.text == "Test criteria"
        assert criteria.checked is True
    
    def test_task_criteria_defaults(self):
        """Test TaskCriteria with default values."""
        criteria = TaskCriteria(text="Test criteria")
        
        assert criteria.text == "Test criteria"
        assert criteria.checked is False


class TestTaskTodoItem:
    """Test TaskTodoItem data model."""
    
    def test_todo_item_creation(self):
        """Test creating TaskTodoItem."""
        todo = TaskTodoItem(
            text="Test todo",
            status="not-started",
            date_started="2025-09-08T10:00:00",
            date_stopped=None
        )
        
        assert todo.text == "Test todo"
        assert todo.status == "not-started"
        assert todo.date_started == "2025-09-08T10:00:00"
        assert todo.date_stopped is None
    
    def test_todo_item_validation(self):
        """Test TaskTodoItem validation with invalid status."""
        with pytest.raises(ValueError):
            TaskTodoItem(
                text="Test todo",
                status="invalid-status",
                date_started=None,
                date_stopped=None
            )
    
    def test_todo_item_defaults(self):
        """Test TaskTodoItem with default values."""
        todo = TaskTodoItem(text="Test todo", status="not-started")
        
        assert todo.text == "Test todo"
        assert todo.status == "not-started"
        assert todo.date_started is None
        assert todo.date_stopped is None


class TestTaskChangelogEntry:
    """Test TaskChangelogEntry data model."""
    
    def test_changelog_entry_creation(self):
        """Test creating TaskChangelogEntry."""
        entry = TaskChangelogEntry(
            timestamp="2025-09-08T10:00:00",
            text="Test changelog entry",
            lock_id="lock-123",
            file_path="test.py"
        )
        
        assert entry.timestamp == "2025-09-08T10:00:00"
        assert entry.text == "Test changelog entry"
        assert entry.lock_id == "lock-123"
        assert entry.file_path == "test.py"
    
    def test_changelog_entry_optional_fields(self):
        """Test TaskChangelogEntry with optional fields."""
        entry = TaskChangelogEntry(
            timestamp="2025-09-08T10:00:00",
            text="Test changelog entry"
        )
        
        assert entry.timestamp == "2025-09-08T10:00:00"
        assert entry.text == "Test changelog entry"
        assert entry.lock_id is None
        assert entry.file_path is None


class TestTaskPrompt:
    """Test TaskPrompt data model."""
    
    def test_task_prompt_creation(self):
        """Test creating TaskPrompt."""
        prompt = TaskPrompt(
            timestamp="2025-09-08T10:00:00",
            text="Test prompt",
            context="Test context"
        )
        
        assert prompt.timestamp == "2025-09-08T10:00:00"
        assert prompt.text == "Test prompt"
        assert prompt.context == "Test context"


class TestTaskLock:
    """Test TaskLock data model."""
    
    def test_task_lock_creation(self):
        """Test creating TaskLock."""
        lock = TaskLock(
            id="lock-123",
            file_path="test.py",
            status="active",
            agent="test-agent",
            started_at="2025-09-08T10:00:00",
            ranges=[{"start": 1, "end": 10}],
            description="Test lock"
        )
        
        assert lock.file_path == "test.py"
        assert lock.id == "lock-123"
        assert lock.agent == "test-agent"
        assert lock.started_at == "2025-09-08T10:00:00"
        assert len(lock.ranges) == 1
        assert lock.ranges[0]["start"] == 1
        assert lock.ranges[0]["end"] == 10
        assert lock.description == "Test lock"


class TestTaskMigration:
    """Test TaskMigration data model."""
    
    def test_task_migration_creation(self):
        """Test creating TaskMigration."""
        migration = TaskMigration(
            migrated=True,
            source_path="old_task.md",
            method="manual",
            migrated_at="2025-09-08T10:00:00"
        )
        
        assert migration.migrated is True
        assert migration.source_path == "old_task.md"
        assert migration.method == "manual"
        assert migration.migrated_at == "2025-09-08T10:00:00"
    
    def test_task_migration_defaults(self):
        """Test TaskMigration with default values."""
        migration = TaskMigration(migrated=False)
        
        assert migration.migrated is False
        assert migration.source_path is None
        assert migration.method is None
        assert migration.migrated_at is None


class TestTaskManager:
    """Test TaskManager functionality."""
    
    def test_task_manager_initialization(self, temp_tasks_dir):
        """Test TaskManager initialization."""
        tasks_dir = os.path.join(temp_tasks_dir, "tasks")
        manager = TaskManager(tasks_dir)
        
        assert manager.tasks_dir == Path(tasks_dir)
        assert manager.repo_root == Path(tasks_dir).parent
        assert manager.schema_path == Path(tasks_dir) / "_schema.json"
        assert manager.status_path == Path(tasks_dir) / "_status.json"
    
    def test_task_manager_initialization_default(self):
        """Test TaskManager initialization with default repo root."""
        manager = TaskManager()
        assert manager.tasks_dir == Path("tasks")
        assert manager.repo_root == Path(".")
    
    def test_load_schema(self, task_manager):
        """Test loading schema from file."""
        schema = task_manager.load_schema()
        
        assert isinstance(schema, dict)
        assert "type" in schema
        assert "properties" in schema
        assert "required" in schema
        assert schema["type"] == "object"
    
    def test_list_task_paths(self, task_manager, sample_tasks, temp_tasks_dir):
        """Test listing task file paths."""
        tasks_dir = os.path.join(temp_tasks_dir, "tasks")
        
        # Create sample task files
        for i, task in enumerate(sample_tasks):
            task_file = os.path.join(tasks_dir, f"task_{i}.json")
            with open(task_file, "w") as f:
                json.dump(task, f)
        
        paths = task_manager.list_task_paths()
        
        assert len(paths) == 3
        assert all(str(path).endswith('.json') for path in paths)
        assert not any('_schema.json' in str(path) for path in paths)
        assert not any('_status.json' in str(path) for path in paths)
    
    def test_list_tasks(self, task_manager, sample_tasks, temp_tasks_dir):
        """Test loading tasks from files."""
        tasks_dir = os.path.join(temp_tasks_dir, "tasks")
        
        # Create sample task files
        for i, task in enumerate(sample_tasks):
            task_file = os.path.join(tasks_dir, f"task_{i}.json")
            with open(task_file, "w") as f:
                json.dump(task, f)
        
        tasks = task_manager.list_tasks()
        
        assert len(tasks) == 3
        assert all(isinstance(task, dict) for task in tasks)
        assert all("id" in task for task in tasks)
        assert all("title" in task for task in tasks)
        assert all("status" in task for task in tasks)
    
    def test_validate_tasks_valid(self, task_manager, sample_tasks, temp_tasks_dir):
        """Test task validation with valid tasks."""
        tasks_dir = os.path.join(temp_tasks_dir, "tasks")
        
        # Create sample task files
        for i, task in enumerate(sample_tasks):
            task_file = os.path.join(tasks_dir, f"task_{i}.json")
            with open(task_file, "w") as f:
                json.dump(task, f)
        
        results = task_manager.validate_tasks()
        
        assert len(results) == 3
        assert all(result["status"] == "valid" for result in results)
    
    def test_validate_tasks_invalid(self, task_manager, temp_tasks_dir):
        """Test task validation with invalid tasks."""
        tasks_dir = os.path.join(temp_tasks_dir, "tasks")
        
        # Create an invalid task file (missing required fields)
        invalid_task = {"id": "2025-09-10-invalid-task"}
        task_file = os.path.join(tasks_dir, "invalid_task.json")
        with open(task_file, "w") as f:
            json.dump(invalid_task, f)
        
        results = task_manager.validate_tasks()
        
        assert len(results) == 1
        assert results[0]["status"] == "invalid"
        assert "error" in results[0]
        assert "title" in results[0]["error"]  # Missing required field
    
    def test_format_error(self, task_manager):
        """Test error formatting."""
        class MockError:
            def __init__(self, path, message):
                self.path = path
                self.message = message
        
        # Test with path
        error = MockError(["properties", "title"], "is required")
        formatted = task_manager._format_error(error)
        assert formatted == "Validation error at properties.title: is required"
        
        # Test without path
        error = MockError([], "is required")
        formatted = task_manager._format_error(error)
        assert formatted == "Validation error at <root>: is required"
    
    def test_generate_status(self, task_manager, sample_tasks, temp_tasks_dir):
        """Test status generation."""
        tasks_dir = os.path.join(temp_tasks_dir, "tasks")
        
        # Create sample task files
        for i, task in enumerate(sample_tasks):
            task_file = os.path.join(tasks_dir, f"task_{i}.json")
            with open(task_file, "w") as f:
                json.dump(task, f)
        
        status = task_manager.generate_status()
        
        # Check structure
        assert "active_tasks" in status
        assert "recently_completed" in status
        
        # Check active tasks (in-progress and planned)
        active_tasks = status["active_tasks"]
        assert len(active_tasks) == 2
        assert all(task["status"] in ["in-progress", "planned"] for task in active_tasks)
        
        # Check completed tasks
        completed_tasks = status["recently_completed"]
        assert len(completed_tasks) == 1
        assert completed_tasks[0]["title"] == "Task 2"
        assert "done_on" in completed_tasks[0]
        assert "summary" in completed_tasks[0]
        
        # Check sorting (most recent first)
        active_dates = [task["updated_at"] for task in active_tasks]
        assert active_dates == sorted(active_dates, reverse=True)
    
    def test_generate_status_empty_changelog(self, task_manager, temp_tasks_dir):
        """Test status generation with tasks that have empty changelog."""
        tasks_dir = os.path.join(temp_tasks_dir, "tasks")
        
        # Create task with empty changelog
        task = {
            "id": "2025-09-10-test-task",
            "title": "Test Task",
            "owner": "test-user",
            "status": "in-progress",
            "created_at": "2025-09-08T10:00:00",
            "updated_at": "2025-09-08T10:00:00",
            "progress_percent": 0,
            "changelog": [],
            "todo": []
        }
        
        task_file = os.path.join(tasks_dir, "2025-09-10-test-task.json")
        with open(task_file, "w") as f:
            json.dump(task, f)
        
        status = task_manager.generate_status()
        active_tasks = status["active_tasks"]
        assert len(active_tasks) == 1
        assert active_tasks[0]["latest_work"] == ""
    
    def test_write_status(self, task_manager, sample_tasks, temp_tasks_dir):
        """Test writing status to file."""
        tasks_dir = os.path.join(temp_tasks_dir, "tasks")
        
        # Create sample task files
        for i, task in enumerate(sample_tasks):
            task_file = os.path.join(tasks_dir, f"task_{i}.json")
            with open(task_file, "w") as f:
                json.dump(task, f)
        
        # Test writing to default path
        output_path = task_manager.write_status()
        assert output_path == task_manager.status_path
        
        # Verify file was written
        assert os.path.exists(output_path)
        with open(output_path, "r") as f:
            written_status = json.load(f)
        
        assert "active_tasks" in written_status
        assert "recently_completed" in written_status
        
        # Test writing to default path (no custom path support)
        output_path = task_manager.write_status()
        assert output_path == task_manager.status_path
        assert os.path.exists(output_path)
    
    def test_load_task(self, task_manager, sample_task_data, temp_tasks_dir):
        """Test loading a single task."""
        tasks_dir = os.path.join(temp_tasks_dir, "tasks")
        task_file = os.path.join(tasks_dir, "test_task.json")
        
        with open(task_file, "w") as f:
            json.dump(sample_task_data, f)
        
        task = task_manager.load_task("test_task")
        
        assert task is not None
        assert task.id == sample_task_data["id"]
        assert task.title == sample_task_data["title"]
    
    def test_load_task_not_found(self, task_manager):
        """Test loading a non-existent task."""
        task = task_manager.load_task("nonexistent_task")
        assert task is None
    
    def test_save_task(self, task_manager, sample_task_data, temp_tasks_dir):
        """Test saving a task."""
        task_id = "2025-09-10-test-save-task"
        sample_task_data["id"] = task_id
        
        # Save task
        task = TaskFile(**sample_task_data)
        task_manager.save_task(task)
        
        # Verify task was saved
        task_file = os.path.join(temp_tasks_dir, "tasks", f"{task_id}.json")
        assert os.path.exists(task_file)
        
        with open(task_file, "r") as f:
            saved_task = json.load(f)
        
        assert saved_task["id"] == task_id
        assert saved_task["title"] == sample_task_data["title"]
    
    def test_calculate_progress_percent(self, task_manager):
        """Test progress calculation from todo items."""
        # Test with no todo items
        progress = task_manager._calculate_progress_percent([])
        assert progress == 0
        
        # Test with all not-started
        todo_items = [
            TaskTodoItem(text="Todo item", status="not-started"),
            TaskTodoItem(text="Todo item", status="not-started"),
            TaskTodoItem(text="Todo item", status="not-started"),
        ]
        progress = task_manager._calculate_progress_percent(todo_items)
        assert progress == 0
        
        # Test with mixed statuses
        todo_items = [
            TaskTodoItem(text="Todo item", status="done"),
            TaskTodoItem(text="Todo item", status="not-started"),
            TaskTodoItem(text="Todo item", status="not-started"),
        ]
        progress = task_manager._calculate_progress_percent(todo_items)
        assert progress == 33  # 1 out of 3 done
        
        # Test with all done
        todo_items = [
            TaskTodoItem(text="Todo item", status="done"),
            TaskTodoItem(text="Todo item", status="done"),
            TaskTodoItem(text="Todo item", status="done"),
        ]
        progress = task_manager._calculate_progress_percent(todo_items)
        assert progress == 100

