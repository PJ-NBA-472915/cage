"""
Unit tests for TaskManager class.
"""

import json
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

from manager.task_manager import TaskManager, TaskValidationResult


class TestTaskManager:
    """Test TaskManager functionality."""

    @pytest.fixture
    def temp_tasks_dir(self):
        """Create a temporary tasks directory for testing."""
        temp_dir = tempfile.mkdtemp()
        tasks_dir = os.path.join(temp_dir, "tasks")
        os.makedirs(tasks_dir)
        
        # Create a basic schema file
        schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "title": {"type": "string"},
                "status": {"type": "string"}
            },
            "required": ["id", "title", "status"]
        }
        
        with open(os.path.join(tasks_dir, "_schema.json"), "w") as f:
            json.dump(schema, f)
        
        # Create a status file
        status = {"active_tasks": [], "recently_completed": []}
        with open(os.path.join(tasks_dir, "_status.json"), "w") as f:
            json.dump(status, f)
        
        yield temp_dir
        
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def task_manager(self, temp_tasks_dir):
        """Create a TaskManager instance pointing to temp directory."""
        return TaskManager(temp_tasks_dir)

    @pytest.fixture
    def sample_tasks(self):
        """Sample task data for testing."""
        return [
            {
                "id": "test-task-1",
                "title": "Test Task 1",
                "status": "in-progress",
                "progress_percent": 50,
                "updated_at": "2025-08-24 10:00",
                "changelog": [
                    {"timestamp": "2025-08-24 10:00", "text": "Task started"}
                ],
                "todo": [
                    {"text": "Step 1", "checked": True},
                    {"text": "Step 2", "checked": False}
                ]
            },
            {
                "id": "test-task-2",
                "title": "Test Task 2",
                "status": "done",
                "progress_percent": 100,
                "updated_at": "2025-08-24 09:00",
                "changelog": [
                    {"timestamp": "2025-08-24 09:00", "text": "Task completed"}
                ],
                "todo": [
                    {"text": "Step 1", "checked": True},
                    {"text": "Step 2", "checked": True}
                ]
            },
            {
                "id": "test-task-3",
                "title": "Test Task 3",
                "status": "planned",
                "progress_percent": 0,
                "updated_at": "2025-08-24 08:00",
                "changelog": [
                    {"timestamp": "2025-08-24 08:00", "text": "Task planned"}
                ],
                "todo": [
                    {"text": "Step 1", "checked": False},
                    {"text": "Step 2", "checked": False}
                ]
            }
        ]

    def test_task_manager_initialization(self, task_manager, temp_tasks_dir):
        """Test TaskManager initialization with custom repo root."""
        assert task_manager.repo_root == temp_tasks_dir
        assert task_manager.tasks_dir == os.path.join(temp_tasks_dir, "tasks")
        assert task_manager.schema_path == os.path.join(temp_tasks_dir, "tasks", "_schema.json")
        assert task_manager.status_path == os.path.join(temp_tasks_dir, "tasks", "_status.json")

    def test_task_manager_initialization_default(self):
        """Test TaskManager initialization with default repo root."""
        with patch('os.path.abspath') as mock_abspath, \
             patch('os.path.dirname') as mock_dirname:
            
            mock_dirname.side_effect = ["/path/to/manager", "/path/to/repo"]
            mock_abspath.return_value = "/path/to/repo"
            
            tm = TaskManager()
            assert tm.repo_root == "/path/to/repo"

    def test_load_schema(self, task_manager):
        """Test loading schema from file."""
        schema = task_manager.load_schema()
        assert isinstance(schema, dict)
        assert "type" in schema
        assert "properties" in schema
        assert "required" in schema

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
        assert all(path.endswith('.json') for path in paths)
        assert not any('_schema.json' in path for path in paths)
        assert not any('_status.json' in path for path in paths)

    def test_load_tasks(self, task_manager, sample_tasks, temp_tasks_dir):
        """Test loading tasks from files."""
        tasks_dir = os.path.join(temp_tasks_dir, "tasks")
        
        # Create sample task files
        for i, task in enumerate(sample_tasks):
            task_file = os.path.join(tasks_dir, f"task_{i}.json")
            with open(task_file, "w") as f:
                json.dump(task, f)
        
        tasks = task_manager.load_tasks()
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
        assert all(result.valid for result in results)
        assert all(len(result.errors) == 0 for result in results)

    def test_validate_tasks_invalid(self, task_manager, temp_tasks_dir):
        """Test task validation with invalid tasks."""
        tasks_dir = os.path.join(temp_tasks_dir, "tasks")
        
        # Create an invalid task file (missing required fields)
        invalid_task = {"id": "invalid-task"}
        task_file = os.path.join(tasks_dir, "invalid_task.json")
        with open(task_file, "w") as f:
            json.dump(invalid_task, f)
        
        results = task_manager.validate_tasks()
        assert len(results) == 1
        assert not results[0].valid
        assert len(results[0].errors) > 0
        assert "title" in str(results[0].errors[0])  # Missing required field

    def test_format_error(self, task_manager):
        """Test error formatting."""
        class MockError:
            def __init__(self, path, message):
                self.path = path
                self.message = message
        
        # Test with path
        error = MockError(["properties", "title"], "is required")
        formatted = task_manager._format_error(error)
        assert formatted == "properties/title: is required"
        
        # Test without path
        error = MockError([], "is required")
        formatted = task_manager._format_error(error)
        assert formatted == "<root>: is required"

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
        assert completed_tasks[0]["title"] == "Test Task 2"
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
            "id": "test-task",
            "title": "Test Task",
            "status": "in-progress",
            "updated_at": "2025-08-24 10:00",
            "changelog": [],
            "todo": []
        }
        
        task_file = os.path.join(tasks_dir, "task.json")
        with open(task_file, "w") as f:
            json.dump(task, f)
        
        status = task_manager.generate_status()
        active_tasks = status["active_tasks"]
        assert len(active_tasks) == 1
        assert active_tasks[0]["latest_work"] == ""

    def test_generate_status_missing_fields(self, task_manager, temp_tasks_dir):
        """Test status generation with tasks missing optional fields."""
        tasks_dir = os.path.join(temp_tasks_dir, "tasks")
        
        # Create task with minimal fields
        task = {
            "id": "test-task",
            "title": "Test Task",
            "status": "in-progress"
        }
        
        task_file = os.path.join(tasks_dir, "task.json")
        with open(task_file, "w") as f:
            json.dump(task, f)
        
        status = task_manager.generate_status()
        active_tasks = status["active_tasks"]
        assert len(active_tasks) == 1
        assert active_tasks[0]["progress_percent"] == 0
        assert active_tasks[0]["updated_at"] == ""
        assert active_tasks[0]["latest_work"] == ""
        assert active_tasks[0]["remaining_todo"] == []

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
        
        # Test writing to custom path
        custom_path = os.path.join(temp_tasks_dir, "custom_status.json")
        output_path = task_manager.write_status(custom_path)
        assert output_path == custom_path
        assert os.path.exists(custom_path)

    def test_task_validation_result(self):
        """Test TaskValidationResult dataclass."""
        result = TaskValidationResult(
            path="/path/to/task.json",
            valid=True,
            errors=[]
        )
        
        assert result.path == "/path/to/task.json"
        assert result.valid is True
        assert result.errors == []
        
        # Test with errors
        result_with_errors = TaskValidationResult(
            path="/path/to/invalid.json",
            valid=False,
            errors=["title: is required", "status: is required"]
        )
        
        assert result_with_errors.path == "/path/to/invalid.json"
        assert result_with_errors.valid is False
        assert len(result_with_errors.errors) == 2
