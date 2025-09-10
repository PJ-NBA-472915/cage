"""
Integration tests for Cage system components.
"""

import json
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.cage.task_models import TaskManager
from src.cage.editor_tool import EditorTool


class TestTaskEditorIntegration:
    """Test integration between Task Manager and Editor Tool."""
    
    def test_task_with_file_operations(self, temp_tasks_dir, temp_dir):
        """Test task creation with file operations."""
        # Initialize components
        task_manager = TaskManager(temp_tasks_dir)
        editor_tool = EditorTool(Path(temp_dir), task_manager=task_manager)
        
        # Create a task
        task_data = {
            "id": "2025-09-08-integration-test",
            "title": "Integration Test Task",
            "owner": "test-user",
            "status": "in-progress",
            "created_at": "2025-09-08T10:00:00",
            "updated_at": "2025-09-08T10:00:00",
            "progress_percent": 0,
            "tags": ["integration", "test"],
            "summary": "Test task with file operations",
            "success_criteria": [],
            "acceptance_checks": [],
            "subtasks": [],
            "todo": [],
            "changelog": [],
            "decisions": [],
            "lessons_learned": [],
            "issues_risks": [],
            "next_steps": [],
            "references": [],
            "prompts": [],
            "locks": [],
            "migration": {"migrated": False, "source_path": None, "method": None, "migrated_at": None},
            "metadata": {}
        }
        
        # Save task
        task_manager.save_task(task_data)
        
        # Perform file operations with task correlation
        from src.cage.editor_tool import FileOperation, OperationType
        
        # Create a file
        create_operation = FileOperation(
            operation=OperationType.INSERT,
            path="test_integration.py",
            payload={"content": "print('Hello from integration test!')\n"},
            intent="Create test file for integration",
            author="test-user",
            correlation_id="task-2025-09-08-integration-test-create"
        )
        
        result = editor_tool.execute_operation(create_operation)
        assert result.ok is True
        
        # Update the file
        update_operation = FileOperation(
            operation=OperationType.UPDATE,
            path="test_integration.py",
            payload={"content": "print('Updated integration test!')\n"},
            intent="Update test file",
            author="test-user",
            correlation_id="task-2025-09-08-integration-test-update"
        )
        
        result = editor_tool.execute_operation(update_operation)
        assert result.ok is True
        
        # Verify file exists and has correct content
        file_path = Path(temp_dir) / "test_integration.py"
        assert file_path.exists()
        assert file_path.read_text() == "print('Updated integration test!')\n"
        
        # Load task and verify changelog was updated
        loaded_task = task_manager.load_task("2025-09-08-integration-test")
        assert loaded_task is not None
        assert len(loaded_task["changelog"]) >= 2  # At least 2 file operations logged
    
    def test_file_operations_with_task_locks(self, temp_tasks_dir, temp_dir):
        """Test file operations with task-based locking."""
        # Initialize components
        task_manager = TaskManager(temp_tasks_dir)
        editor_tool = EditorTool(Path(temp_dir), task_manager=task_manager)
        
        # Create a task
        task_data = {
            "id": "2025-09-08-lock-test",
            "title": "Lock Test Task",
            "owner": "test-user",
            "status": "in-progress",
            "created_at": "2025-09-08T10:00:00",
            "updated_at": "2025-09-08T10:00:00",
            "progress_percent": 0,
            "tags": ["integration", "test", "locking"],
            "summary": "Test file operations with locking",
            "success_criteria": [],
            "acceptance_checks": [],
            "subtasks": [],
            "todo": [],
            "changelog": [],
            "decisions": [],
            "lessons_learned": [],
            "issues_risks": [],
            "next_steps": [],
            "references": [],
            "prompts": [],
            "locks": [],
            "migration": {"migrated": False, "source_path": None, "method": None, "migrated_at": None},
            "metadata": {}
        }
        
        task_manager.save_task(task_data)
        
        # Create a file
        from src.cage.editor_tool import FileOperation, OperationType
        
        create_operation = FileOperation(
            operation=OperationType.INSERT,
            path="lock_test.py",
            payload={"content": "print('Lock test file')\n"},
            intent="Create file for lock testing",
            author="test-user",
            correlation_id="task-2025-09-08-lock-test-create"
        )
        
        result = editor_tool.execute_operation(create_operation)
        assert result.ok is True
        assert result.lock_id is not None
        
        # Verify lock was acquired and released
        assert not editor_tool.lock_manager.is_locked("lock_test.py")
        
        # Load task and verify operation was logged
        loaded_task = task_manager.load_task("2025-09-08-lock-test")
        assert loaded_task is not None
        assert len(loaded_task["changelog"]) >= 1


class TestAPITaskIntegration:
    """Test API integration with Task Manager."""
    
    def test_api_task_workflow(self, api_client, auth_headers, mock_repo_path, sample_task_data):
        """Test complete API task workflow."""
        with patch('src.api.main.task_manager') as mock_tm:
            mock_tm.load_task.return_value = None
            mock_tm.save_task.return_value = None
            mock_tm.load_tasks.return_value = [sample_task_data]
            mock_tm.generate_status.return_value = {
                "active_tasks": [sample_task_data],
                "recently_completed": []
            }
            mock_tm.write_status.return_value = "/path/to/status.json"
            
            # Create task
            response = api_client.post(
                "/tasks/confirm",
                json={
                    "task_id": "2025-09-08-api-test",
                    "status": "confirmed"
                },
                headers=auth_headers
            )
            assert response.status_code == 200
            
            # List tasks
            response = api_client.get("/tasks", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert len(data["tasks"]) == 1
            
            # Get specific task
            mock_tm.load_task.return_value = sample_task_data
            response = api_client.get("/tasks/2025-09-08-api-test", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "2025-09-08-api-test"
            
            # Update task
            response = api_client.patch(
                "/tasks/2025-09-08-api-test",
                json={"status": "done", "progress_percent": 100},
                headers=auth_headers
            )
            assert response.status_code == 200
            
            # Rebuild tracker
            response = api_client.post("/tracker/rebuild", headers=auth_headers)
            assert response.status_code == 200
    
    def test_api_file_operations(self, api_client, auth_headers, mock_repo_path, test_file):
        """Test API file operations."""
        with patch('src.api.main.editor_tool') as mock_editor:
            mock_editor.execute_operation.return_value = Mock(
                ok=True,
                file=test_file,
                operation="GET",
                lock_id="lock-123",
                pre_hash="abc123",
                post_hash=None,
                diff="file content",
                warnings=[],
                conflicts=[]
            )
            
            # GET file
            response = api_client.post(
                "/files/edit",
                json={
                    "operation": "GET",
                    "path": test_file,
                    "selector": {"mode": "region", "start": 1, "end": 10},
                    "payload": None,
                    "intent": "Test GET operation",
                    "dry_run": False,
                    "author": "test-user",
                    "correlation_id": "test-123"
                },
                headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["file"] == test_file
            
            # INSERT file
            mock_editor.execute_operation.return_value = Mock(
                ok=True,
                file="new_file.py",
                operation="INSERT",
                lock_id="lock-456",
                pre_hash=None,
                post_hash="def456",
                diff="new file content",
                warnings=[],
                conflicts=[]
            )
            
            response = api_client.post(
                "/files/edit",
                json={
                    "operation": "INSERT",
                    "path": "new_file.py",
                    "selector": None,
                    "payload": {"content": "print('Hello!')\n"},
                    "intent": "Test INSERT operation",
                    "dry_run": False,
                    "author": "test-user",
                    "correlation_id": "test-456"
                },
                headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["file"] == "new_file.py"


class TestCLIAPIIntegration:
    """Test CLI and API integration."""
    
    def test_cli_api_consistency(self, temp_tasks_dir, temp_dir):
        """Test that CLI and API produce consistent results."""
        from src.cli.main import app as cli_app
        from typer.testing import CliRunner
        
        # Test CLI task creation
        runner = CliRunner()
        
        result = runner.invoke(cli_app, [
            "task-create",
            "2025-09-08-cli-api-test",
            "CLI API Test Task",
            "--owner", "test-user",
            "--summary", "Test CLI API consistency"
        ])
        assert result.exit_code == 0
        
        # Test CLI task listing
        result = runner.invoke(cli_app, ["task-list"])
        assert result.exit_code == 0
        assert "2025-09-08-cli-api-test" in result.output
        
        # Test CLI file operations
        from src.cli.editor_cli import main as editor_cli_main
        
        result = runner.invoke(editor_cli_main, [
            "insert",
            "cli_api_test.py",
            "--content", "print('CLI API test')\n",
            "--repo-path", temp_dir
        ])
        assert result.exit_code == 0
        
        result = runner.invoke(editor_cli_main, [
            "get",
            "cli_api_test.py",
            "--repo-path", temp_dir
        ])
        assert result.exit_code == 0
        assert "print('CLI API test')" in result.output


class TestSystemErrorHandling:
    """Test system-wide error handling."""
    
    def test_task_manager_error_propagation(self, temp_tasks_dir):
        """Test that Task Manager errors are properly handled."""
        task_manager = TaskManager(temp_tasks_dir)
        
        # Test with invalid task data
        invalid_task = {
            "id": "invalid-task",
            # Missing required fields
        }
        
        # This should not raise an exception, but validation should fail
        task_manager.save_task(invalid_task)
        
        # Verify task was saved (even if invalid)
        task_file = os.path.join(temp_tasks_dir, "tasks", "invalid-task.json")
        assert os.path.exists(task_file)
    
    def test_editor_tool_error_propagation(self, temp_dir):
        """Test that Editor Tool errors are properly handled."""
        editor_tool = EditorTool(Path(temp_dir))
        
        from src.cage.editor_tool import FileOperation, OperationType
        
        # Test with non-existent file
        operation = FileOperation(
            operation=OperationType.GET,
            path="nonexistent.py",
            author="test-user",
            correlation_id="test-error"
        )
        
        result = editor_tool.execute_operation(operation)
        assert result.ok is False
        assert "File not found" in result.error
    
    def test_api_error_propagation(self, api_client, auth_headers, mock_repo_path):
        """Test that API errors are properly handled."""
        # Test with invalid task data
        response = api_client.post(
            "/tasks/confirm",
            json={
                "task_id": "",  # Invalid empty ID
                "status": "confirmed"
            },
            headers=auth_headers
        )
        
        # Should handle validation error gracefully
        assert response.status_code in [200, 400, 422]
    
    def test_cli_error_propagation(self, temp_tasks_dir):
        """Test that CLI errors are properly handled."""
        from src.cli.main import app as cli_app
        from typer.testing import CliRunner
        
        runner = CliRunner()
        
        # Test with invalid task ID
        result = runner.invoke(cli_app, [
            "task-create",
            "invalid-id",  # Invalid format
            "Test Task",
            "--owner", "test-user"
        ])
        
        assert result.exit_code == 1
        assert "Error" in result.output


class TestSystemPerformance:
    """Test system performance characteristics."""
    
    def test_task_manager_performance(self, temp_tasks_dir, sample_tasks):
        """Test Task Manager performance with multiple tasks."""
        task_manager = TaskManager(temp_tasks_dir)
        
        # Create multiple tasks
        for i in range(10):
            task_data = sample_tasks[0].copy()
            task_data["id"] = f"2025-09-08-perf-test-{i}"
            task_data["title"] = f"Performance Test Task {i}"
            task_manager.save_task(task_data)
        
        # Test loading all tasks
        tasks = task_manager.load_tasks()
        assert len(tasks) == 10
        
        # Test status generation
        status = task_manager.generate_status()
        assert "active_tasks" in status
        assert "recently_completed" in status
    
    def test_editor_tool_performance(self, temp_dir):
        """Test Editor Tool performance with multiple operations."""
        editor_tool = EditorTool(Path(temp_dir))
        
        from src.cage.editor_tool import FileOperation, OperationType
        
        # Create multiple files
        for i in range(10):
            operation = FileOperation(
                operation=OperationType.INSERT,
                path=f"perf_test_{i}.py",
                payload={"content": f"print('Performance test {i}')\n"},
                author="test-user",
                correlation_id=f"test-perf-{i}"
            )
            
            result = editor_tool.execute_operation(operation)
            assert result.ok is True
        
        # Verify all files were created
        for i in range(10):
            file_path = Path(temp_dir) / f"perf_test_{i}.py"
            assert file_path.exists()
    
    def test_concurrent_operations(self, temp_tasks_dir, temp_dir):
        """Test system behavior under concurrent operations."""
        import threading
        import time
        
        task_manager = TaskManager(temp_tasks_dir)
        editor_tool = EditorTool(Path(temp_dir), task_manager=task_manager)
        
        results = []
        errors = []
        
        def create_task_and_file(task_id):
            try:
                # Create task
                task_data = {
                    "id": f"2025-09-08-concurrent-{task_id}",
                    "title": f"Concurrent Task {task_id}",
                    "owner": "test-user",
                    "status": "in-progress",
                    "created_at": "2025-09-08T10:00:00",
                    "updated_at": "2025-09-08T10:00:00",
                    "progress_percent": 0,
                    "tags": ["concurrent", "test"],
                    "summary": f"Concurrent test task {task_id}",
                    "success_criteria": [],
                    "acceptance_checks": [],
                    "subtasks": [],
                    "todo": [],
                    "changelog": [],
                    "decisions": [],
                    "lessons_learned": [],
                    "issues_risks": [],
                    "next_steps": [],
                    "references": [],
                    "prompts": [],
                    "locks": [],
                    "migration": {"migrated": False, "source_path": None, "method": None, "migrated_at": None},
                    "metadata": {}
                }
                
                task_manager.save_task(task_data)
                
                # Create file
                from src.cage.editor_tool import FileOperation, OperationType
                
                operation = FileOperation(
                    operation=OperationType.INSERT,
                    path=f"concurrent_{task_id}.py",
                    payload={"content": f"print('Concurrent test {task_id}')\n"},
                    intent=f"Create file for concurrent test {task_id}",
                    author="test-user",
                    correlation_id=f"task-2025-09-08-concurrent-{task_id}-create"
                )
                
                result = editor_tool.execute_operation(operation)
                results.append(result.ok)
                
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_task_and_file, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(results) == 5
        assert all(results)  # All operations should succeed
        assert len(errors) == 0  # No errors should occur
        
        # Verify files were created
        for i in range(5):
            file_path = Path(temp_dir) / f"concurrent_{i}.py"
            assert file_path.exists()
        
        # Verify tasks were created
        tasks = task_manager.load_tasks()
        assert len(tasks) == 5


class TestSystemDataConsistency:
    """Test system data consistency."""
    
    def test_task_data_consistency(self, temp_tasks_dir, sample_task_data):
        """Test that task data remains consistent across operations."""
        task_manager = TaskManager(temp_tasks_dir)
        
        # Save task
        task_manager.save_task(sample_task_data)
        
        # Load and verify
        loaded_task = task_manager.load_task(sample_task_data["id"])
        assert loaded_task is not None
        assert loaded_task["id"] == sample_task_data["id"]
        assert loaded_task["title"] == sample_task_data["title"]
        assert loaded_task["status"] == sample_task_data["status"]
        
        # Update task
        loaded_task["status"] = "done"
        loaded_task["progress_percent"] = 100
        task_manager.save_task(loaded_task)
        
        # Reload and verify update
        updated_task = task_manager.load_task(sample_task_data["id"])
        assert updated_task["status"] == "done"
        assert updated_task["progress_percent"] == 100
    
    def test_file_data_consistency(self, temp_dir, test_file_content):
        """Test that file data remains consistent across operations."""
        editor_tool = EditorTool(Path(temp_dir))
        
        # Create file
        from src.cage.editor_tool import FileOperation, OperationType
        
        create_operation = FileOperation(
            operation=OperationType.INSERT,
            path="consistency_test.py",
            payload={"content": test_file_content},
            author="test-user",
            correlation_id="test-consistency"
        )
        
        result = editor_tool.execute_operation(create_operation)
        assert result.ok is True
        
        # Read file and verify content
        read_operation = FileOperation(
            operation=OperationType.GET,
            path="consistency_test.py",
            author="test-user",
            correlation_id="test-consistency-read"
        )
        
        result = editor_tool.execute_operation(read_operation)
        assert result.ok is True
        assert result.diff == test_file_content
        
        # Update file
        update_operation = FileOperation(
            operation=OperationType.UPDATE,
            path="consistency_test.py",
            payload={"content": "print('Updated content')\n"},
            author="test-user",
            correlation_id="test-consistency-update"
        )
        
        result = editor_tool.execute_operation(update_operation)
        assert result.ok is True
        
        # Verify update
        result = editor_tool.execute_operation(read_operation)
        assert result.ok is True
        assert result.diff == "print('Updated content')\n"
    
    def test_cross_component_data_consistency(self, temp_tasks_dir, temp_dir):
        """Test data consistency across Task Manager and Editor Tool."""
        task_manager = TaskManager(temp_tasks_dir)
        editor_tool = EditorTool(Path(temp_dir), task_manager=task_manager)
        
        # Create task
        task_data = {
            "id": "2025-09-08-consistency-test",
            "title": "Consistency Test Task",
            "owner": "test-user",
            "status": "in-progress",
            "created_at": "2025-09-08T10:00:00",
            "updated_at": "2025-09-08T10:00:00",
            "progress_percent": 0,
            "tags": ["consistency", "test"],
            "summary": "Test cross-component consistency",
            "success_criteria": [],
            "acceptance_checks": [],
            "subtasks": [],
            "todo": [],
            "changelog": [],
            "decisions": [],
            "lessons_learned": [],
            "issues_risks": [],
            "next_steps": [],
            "references": [],
            "prompts": [],
            "locks": [],
            "migration": {"migrated": False, "source_path": None, "method": None, "migrated_at": None},
            "metadata": {}
        }
        
        task_manager.save_task(task_data)
        
        # Perform file operation with task correlation
        from src.cage.editor_tool import FileOperation, OperationType
        
        operation = FileOperation(
            operation=OperationType.INSERT,
            path="consistency_test.py",
            payload={"content": "print('Consistency test')\n"},
            intent="Test cross-component consistency",
            author="test-user",
            correlation_id="task-2025-09-08-consistency-test-file"
        )
        
        result = editor_tool.execute_operation(operation)
        assert result.ok is True
        
        # Verify task was updated with file operation
        loaded_task = task_manager.load_task("2025-09-08-consistency-test")
        assert loaded_task is not None
        assert len(loaded_task["changelog"]) >= 1
        
        # Verify file exists
        file_path = Path(temp_dir) / "consistency_test.py"
        assert file_path.exists()
        assert file_path.read_text() == "print('Consistency test')\n"

