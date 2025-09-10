"""
Pytest configuration and shared fixtures for Cage tests.
"""

import json
import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

# Add src to path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from src.cage.task_models import TaskManager, TaskFile
from src.cage.editor_tool import EditorTool, FileLockManager
from src.api.main import app


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_tasks_dir(temp_dir):
    """Create a temporary tasks directory with required files."""
    tasks_dir = os.path.join(temp_dir, "tasks")
    os.makedirs(tasks_dir)
    
    # Create schema file
    schema = {
        "type": "object",
        "additionalProperties": True,
        "properties": {
            "id": {"type": "string"},
            "title": {"type": "string"},
            "owner": {"type": "string"},
            "status": {"type": "string", "enum": ["planned", "in-progress", "blocked", "review", "done", "abandoned"]},
            "created_at": {"type": "string"},
            "updated_at": {"type": "string"},
            "progress_percent": {"type": "integer", "minimum": 0, "maximum": 100},
            "tags": {"type": "array", "items": {"type": "string"}},
            "summary": {"type": "string"},
            "success_criteria": {"type": "array", "items": {"type": "object"}},
            "acceptance_checks": {"type": "array", "items": {"type": "object"}},
            "subtasks": {"type": "array", "items": {"type": "string"}},
            "todo": {"type": "array", "items": {"type": "object"}},
            "changelog": {"type": "array", "items": {"type": "object"}},
            "decisions": {"type": "array", "items": {"type": "string"}},
            "lessons_learned": {"type": "array", "items": {"type": "string"}},
            "issues_risks": {"type": "array", "items": {"type": "string"}},
            "next_steps": {"type": "array", "items": {"type": "string"}},
            "references": {"type": "array", "items": {"type": "string"}},
            "prompts": {"type": "array", "items": {"type": "object"}},
            "locks": {"type": "array", "items": {"type": "object"}},
            "migration": {"type": "object"},
            "metadata": {"type": "object"}
        },
        "required": ["id", "title", "owner", "status", "created_at", "updated_at", "progress_percent"]
    }
    
    with open(os.path.join(tasks_dir, "_schema.json"), "w") as f:
        json.dump(schema, f)
    
    # Create status file
    status = {"active_tasks": [], "recently_completed": []}
    with open(os.path.join(tasks_dir, "_status.json"), "w") as f:
        json.dump(status, f)
    
    return temp_dir


@pytest.fixture
def task_manager(temp_tasks_dir):
    """Create a TaskManager instance for testing."""
    return TaskManager(os.path.join(temp_tasks_dir, "tasks"))


@pytest.fixture
def cli_task_manager_patch(temp_tasks_dir):
    """Create a patch for CLI task manager to use temporary directory."""
    tasks_dir = os.path.join(temp_tasks_dir, "tasks")
    return patch('src.cli.main.task_manager', TaskManager(tasks_dir))


@pytest.fixture
def editor_tool(temp_dir):
    """Create an EditorTool instance for testing."""
    return EditorTool(Path(temp_dir))


@pytest.fixture
def file_lock_manager():
    """Create a FileLockManager instance for testing."""
    return FileLockManager()


@pytest.fixture
def sample_task_data():
    """Sample task data for testing."""
    return {
        "id": "2025-09-10-test-task",
        "title": "Test Task",
        "owner": "test-user",
        "status": "in-progress",
        "created_at": "2025-09-10T10:00:00",
        "updated_at": "2025-09-10T10:00:00",
        "progress_percent": 50,
        "tags": ["test", "example"],
        "summary": "A test task for unit testing",
        "success_criteria": [
            {"text": "Task is completed", "checked": False},
            {"text": "Tests pass", "checked": True}
        ],
        "acceptance_checks": [
            {"text": "Code is reviewed", "checked": False},
            {"text": "Documentation is updated", "checked": False}
        ],
        "subtasks": [
            "Set up test environment",
            "Write test cases",
            "Run tests"
        ],
        "todo": [
            {
                "text": "Set up test environment",
                "status": "done",
                "date_started": "2025-09-10T10:00:00",
                "date_stopped": "2025-09-10T10:30:00"
            },
            {
                "text": "Write test cases",
                "status": "not-started",
                "date_started": "2025-09-10T10:30:00",
                "date_stopped": None
            },
            {
                "text": "Run tests",
                "status": "not-started",
                "date_started": None,
                "date_stopped": None
            }
        ],
        "changelog": [
            {
                "timestamp": "2025-09-10T10:00:00",
                "text": "Task created"
            },
            {
                "timestamp": "2025-09-10T10:30:00",
                "text": "Completed test environment setup"
            }
        ],
        "decisions": [
            "Use pytest for testing framework",
            "Follow TDD approach"
        ],
        "lessons_learned": [],
        "issues_risks": [],
        "next_steps": [
            "Complete test case writing",
            "Execute test suite"
        ],
        "references": [],
        "prompts": [],
        "locks": [],
        "migration": {
            "migrated": False,
            "source_path": None,
            "method": None,
            "migrated_at": None
        },
        "metadata": {}
    }


@pytest.fixture
def sample_tasks(sample_task_data):
    """Multiple sample tasks for testing."""
    tasks = []
    
    # Task 1: In progress
    task1 = sample_task_data.copy()
    task1["id"] = "2025-09-10-task-1"
    task1["title"] = "Task 1"
    task1["status"] = "in-progress"
    task1["progress_percent"] = 50
    tasks.append(task1)
    
    # Task 2: Completed
    task2 = sample_task_data.copy()
    task2["id"] = "2025-09-10-task-2"
    task2["title"] = "Task 2"
    task2["status"] = "done"
    task2["progress_percent"] = 100
    task2["updated_at"] = "2025-09-10T09:00:00"
    task2["todo"] = [
        {
            "text": "Complete task",
            "status": "done",
            "date_started": "2025-09-10T08:00:00",
            "date_stopped": "2025-09-10T09:00:00"
        }
    ]
    tasks.append(task2)
    
    # Task 3: Planned
    task3 = sample_task_data.copy()
    task3["id"] = "2025-09-10-task-3"
    task3["title"] = "Task 3"
    task3["status"] = "planned"
    task3["progress_percent"] = 0
    task3["updated_at"] = "2025-09-10T08:00:00"
    task3["todo"] = [
        {
            "text": "Start task",
            "status": "not-started",
            "date_started": None,
            "date_stopped": None
        }
    ]
    tasks.append(task3)
    
    return tasks


@pytest.fixture
def test_file_content():
    """Sample file content for Editor Tool testing."""
    return """#!/usr/bin/env python3
\"\"\"
Sample Python file for testing.
\"\"\"

import os
import sys
from pathlib import Path

def hello_world():
    \"\"\"Print hello world message.\"\"\"
    print("Hello, World!")

def calculate_sum(a, b):
    \"\"\"Calculate sum of two numbers.\"\"\"
    return a + b

class Calculator:
    \"\"\"Simple calculator class.\"\"\"
    
    def __init__(self):
        self.history = []
    
    def add(self, a, b):
        \"\"\"Add two numbers.\"\"\"
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
    
    def multiply(self, a, b):
        \"\"\"Multiply two numbers.\"\"\"
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result

if __name__ == "__main__":
    hello_world()
    calc = Calculator()
    print(calc.add(2, 3))
    print(calc.multiply(4, 5))
"""


@pytest.fixture
def test_file(editor_tool, test_file_content):
    """Create a test file for Editor Tool testing."""
    test_file_path = editor_tool.repo_path / "test_file.py"
    test_file_path.write_text(test_file_content)
    return "test_file.py"


@pytest.fixture
def api_client():
    """Create a test client for API testing."""
    return TestClient(app)


@pytest.fixture
def mock_pod_token():
    """Mock POD_TOKEN for API testing."""
    with patch.dict(os.environ, {"POD_TOKEN": "test-token-123"}):
        yield "test-token-123"


@pytest.fixture
def mock_repo_path(temp_dir):
    """Mock repository path for API testing."""
    with patch.dict(os.environ, {"REPO_PATH": temp_dir}):
        yield temp_dir


@pytest.fixture
def auth_headers(mock_pod_token):
    """Authentication headers for API requests."""
    return {"Authorization": f"Bearer {mock_pod_token}"}


@pytest.fixture
def sample_file_operation():
    """Sample file operation for testing."""
    return {
        "operation": "GET",
        "path": "test_file.py",
        "selector": {"mode": "region", "start": 1, "end": 10},
        "payload": None,
        "intent": "Test operation",
        "dry_run": False,
        "author": "test-user",
        "correlation_id": "test-operation-123"
    }


@pytest.fixture
def sample_insert_operation():
    """Sample INSERT operation for testing."""
    return {
        "operation": "INSERT",
        "path": "new_file.py",
        "selector": None,
        "payload": {"content": "# New Python file\nprint('Hello, World!')\n"},
        "intent": "Create new file",
        "dry_run": False,
        "author": "test-user",
        "correlation_id": "test-insert-123"
    }


@pytest.fixture
def sample_update_operation():
    """Sample UPDATE operation for testing."""
    return {
        "operation": "UPDATE",
        "path": "test_file.py",
        "selector": {"mode": "region", "start": 5, "end": 5},
        "payload": {"content": "# Updated comment\n"},
        "intent": "Update comment",
        "dry_run": False,
        "author": "test-user",
        "correlation_id": "test-update-123"
    }


@pytest.fixture
def sample_delete_operation():
    """Sample DELETE operation for testing."""
    return {
        "operation": "DELETE",
        "path": "test_file.py",
        "selector": {"mode": "region", "start": 1, "end": 3},
        "payload": None,
        "intent": "Delete header comments",
        "dry_run": False,
        "author": "test-user",
        "correlation_id": "test-delete-123"
    }


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment before each test."""
    # Set test environment variables
    os.environ["POD_TOKEN"] = "test-token-123"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    yield
    
    # Clean up after each test
    # Remove any test-specific environment variables if needed
    pass


@pytest.fixture
def mock_task_manager():
    """Mock TaskManager for testing."""
    mock = Mock(spec=TaskManager)
    mock.load_task.return_value = None
    mock.save_task.return_value = None
    return mock


@pytest.fixture
def mock_file_lock():
    """Mock file lock for testing."""
    return {
        "file_path": "test_file.py",
        "lock_id": "lock:file:test_file.py:1234567890",
        "agent": "test-agent",
        "started_at": "2025-09-08T10:00:00",
        "expires_at": "2025-09-08T10:05:00",
        "ranges": [{"start": 1, "end": 10}],
        "description": "Test lock"
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom settings."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "api: mark test as an API test"
    )
    config.addinivalue_line(
        "markers", "cli: mark test as a CLI test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "api" in str(item.fspath):
            item.add_marker(pytest.mark.api)
        elif "cli" in str(item.fspath):
            item.add_marker(pytest.mark.cli)
        
        # Mark slow tests
        if "slow" in item.name or "performance" in item.name:
            item.add_marker(pytest.mark.slow)

