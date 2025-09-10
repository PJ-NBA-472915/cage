"""
API endpoint tests for Cage system.
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


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_check(self, api_client):
        """Test health check endpoint."""
        response = api_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "timestamp" in data


class TestTaskEndpoints:
    """Test task management endpoints."""
    
    def test_confirm_task_success(self, api_client, auth_headers, sample_task_data, mock_repo_path):
        """Test successful task confirmation."""
        with patch('src.api.main.task_manager') as mock_tm:
            mock_tm.load_task.return_value = None
            mock_tm.save_task.return_value = None
            
            response = api_client.post(
                "/tasks/confirm",
                json={
                    "task_id": "2025-09-08-test-task",
                    "status": "confirmed"
                },
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["task_id"] == "2025-09-08-test-task"
            assert data["action"] == "created"
    
    def test_confirm_task_unauthorized(self, api_client, sample_task_data):
        """Test task confirmation without authentication."""
        response = api_client.post(
            "/tasks/confirm",
            json={
                "task_id": "2025-09-08-test-task",
                "status": "confirmed"
            }
        )
        
        assert response.status_code == 401
    
    def test_confirm_task_invalid_token(self, api_client, sample_task_data):
        """Test task confirmation with invalid token."""
        response = api_client.post(
            "/tasks/confirm",
            json={
                "task_id": "2025-09-08-test-task",
                "status": "confirmed"
            },
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code == 401
    
    def test_get_task_success(self, api_client, auth_headers, sample_task_data, mock_repo_path):
        """Test successful task retrieval."""
        with patch('src.api.main.task_manager') as mock_tm:
            mock_tm.load_task.return_value = sample_task_data
            
            response = api_client.get(
                "/tasks/2025-09-08-test-task",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "2025-09-08-test-task"
            assert data["title"] == "Test Task"
            assert data["status"] == "in-progress"
    
    def test_get_task_not_found(self, api_client, auth_headers, mock_repo_path):
        """Test task retrieval for non-existent task."""
        with patch('src.api.main.task_manager') as mock_tm:
            mock_tm.load_task.return_value = None
            
            response = api_client.get(
                "/tasks/nonexistent-task",
                headers=auth_headers
            )
            
            assert response.status_code == 404
            data = response.json()
            assert data["detail"] == "Task not found"
    
    def test_update_task_success(self, api_client, auth_headers, sample_task_data, mock_repo_path):
        """Test successful task update."""
        with patch('src.api.main.task_manager') as mock_tm:
            mock_tm.load_task.return_value = sample_task_data
            mock_tm.save_task.return_value = None
            
            response = api_client.patch(
                "/tasks/2025-09-08-test-task",
                json={
                    "status": "done",
                    "progress_percent": 100,
                    "title": "Updated Task Title"
                },
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["task_id"] == "2025-09-08-test-task"
            assert "updated_fields" in data
    
    def test_update_task_not_found(self, api_client, auth_headers, mock_repo_path):
        """Test task update for non-existent task."""
        with patch('src.api.main.task_manager') as mock_tm:
            mock_tm.load_task.return_value = None
            
            response = api_client.patch(
                "/tasks/nonexistent-task",
                json={"status": "done"},
                headers=auth_headers
            )
            
            assert response.status_code == 404
            data = response.json()
            assert data["detail"] == "Task not found"
    
    def test_list_tasks_success(self, api_client, auth_headers, sample_tasks, mock_repo_path):
        """Test successful task listing."""
        with patch('src.api.main.task_manager') as mock_tm:
            mock_tm.load_tasks.return_value = sample_tasks
            
            response = api_client.get(
                "/tasks",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "tasks" in data
            assert len(data["tasks"]) == 3
            assert data["count"] == 3
    
    def test_list_tasks_with_status_filter(self, api_client, auth_headers, sample_tasks, mock_repo_path):
        """Test task listing with status filter."""
        with patch('src.api.main.task_manager') as mock_tm:
            # Filter to only in-progress tasks
            filtered_tasks = [task for task in sample_tasks if task["status"] == "in-progress"]
            mock_tm.load_tasks.return_value = filtered_tasks
            
            response = api_client.get(
                "/tasks?status=in-progress",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert len(data["tasks"]) == 1
            assert data["tasks"][0]["status"] == "in-progress"
    
    def test_rebuild_tracker_success(self, api_client, auth_headers, sample_tasks, mock_repo_path):
        """Test successful tracker rebuild."""
        with patch('src.api.main.task_manager') as mock_tm:
            mock_tm.load_tasks.return_value = sample_tasks
            mock_tm.generate_status.return_value = {
                "active_tasks": [task for task in sample_tasks if task["status"] != "done"],
                "recently_completed": [task for task in sample_tasks if task["status"] == "done"]
            }
            mock_tm.write_status.return_value = "/path/to/status.json"
            
            response = api_client.post(
                "/tracker/rebuild",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "active_tasks" in data
            assert "recently_completed" in data


class TestFileEndpoints:
    """Test file operation endpoints."""
    
    def test_edit_file_get_success(self, api_client, auth_headers, sample_file_operation, mock_repo_path, test_file):
        """Test successful file GET operation."""
        sample_file_operation["path"] = test_file
        
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
            
            response = api_client.post(
                "/files/edit",
                json=sample_file_operation,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["file"] == test_file
            assert data["operation"] == "GET"
            assert data["lock_id"] == "lock-123"
            assert data["pre_hash"] == "abc123"
            assert data["diff"] == "file content"
    
    def test_edit_file_insert_success(self, api_client, auth_headers, sample_insert_operation, mock_repo_path):
        """Test successful file INSERT operation."""
        with patch('src.api.main.editor_tool') as mock_editor:
            mock_editor.execute_operation.return_value = Mock(
                ok=True,
                file="new_file.py",
                operation="INSERT",
                lock_id="lock-123",
                pre_hash=None,
                post_hash="def456",
                diff="new file content",
                warnings=[],
                conflicts=[]
            )
            
            response = api_client.post(
                "/files/edit",
                json=sample_insert_operation,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["file"] == "new_file.py"
            assert data["operation"] == "INSERT"
            assert data["post_hash"] == "def456"
    
    def test_edit_file_update_success(self, api_client, auth_headers, sample_update_operation, mock_repo_path, test_file):
        """Test successful file UPDATE operation."""
        sample_update_operation["path"] = test_file
        
        with patch('src.api.main.editor_tool') as mock_editor:
            mock_editor.execute_operation.return_value = Mock(
                ok=True,
                file=test_file,
                operation="UPDATE",
                lock_id="lock-123",
                pre_hash="abc123",
                post_hash="def456",
                diff="@@ -1,1 +1,1 @@\n-old content\n+new content",
                warnings=[],
                conflicts=[]
            )
            
            response = api_client.post(
                "/files/edit",
                json=sample_update_operation,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["file"] == test_file
            assert data["operation"] == "UPDATE"
            assert data["pre_hash"] == "abc123"
            assert data["post_hash"] == "def456"
    
    def test_edit_file_delete_success(self, api_client, auth_headers, sample_delete_operation, mock_repo_path, test_file):
        """Test successful file DELETE operation."""
        sample_delete_operation["path"] = test_file
        
        with patch('src.api.main.editor_tool') as mock_editor:
            mock_editor.execute_operation.return_value = Mock(
                ok=True,
                file=test_file,
                operation="DELETE",
                lock_id="lock-123",
                pre_hash="abc123",
                post_hash="",
                diff="File deleted",
                warnings=[],
                conflicts=[]
            )
            
            response = api_client.post(
                "/files/edit",
                json=sample_delete_operation,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["file"] == test_file
            assert data["operation"] == "DELETE"
            assert data["post_hash"] == ""
    
    def test_edit_file_operation_failed(self, api_client, auth_headers, sample_file_operation, mock_repo_path):
        """Test file operation failure."""
        with patch('src.api.main.editor_tool') as mock_editor:
            mock_editor.execute_operation.return_value = Mock(
                ok=False,
                file="test.py",
                operation="GET",
                lock_id=None,
                pre_hash=None,
                post_hash=None,
                diff=None,
                warnings=[],
                conflicts=[],
                error="File not found"
            )
            
            response = api_client.post(
                "/files/edit",
                json=sample_file_operation,
                headers=auth_headers
            )
            
            assert response.status_code == 400
            data = response.json()
            assert data["detail"] == "File not found"
    
    def test_edit_file_invalid_operation(self, api_client, auth_headers, mock_repo_path):
        """Test file operation with invalid operation type."""
        operation = {
            "operation": "INVALID",
            "path": "test.py",
            "selector": {},
            "payload": {},
            "intent": "Test",
            "dry_run": False,
            "author": "test-user",
            "correlation_id": "test-123"
        }
        
        response = api_client.post(
            "/files/edit",
            json=operation,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid operation" in data["detail"]
    
    def test_edit_file_unauthorized(self, api_client, sample_file_operation):
        """Test file operation without authentication."""
        response = api_client.post(
            "/files/edit",
            json=sample_file_operation
        )
        
        assert response.status_code == 401
    
    def test_edit_file_invalid_token(self, api_client, sample_file_operation):
        """Test file operation with invalid token."""
        response = api_client.post(
            "/files/edit",
            json=sample_file_operation,
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code == 401
    
    def test_edit_file_server_error(self, api_client, auth_headers, sample_file_operation, mock_repo_path):
        """Test file operation with server error."""
        with patch('src.api.main.editor_tool') as mock_editor:
            mock_editor.execute_operation.side_effect = Exception("Server error")
            
            response = api_client.post(
                "/files/edit",
                json=sample_file_operation,
                headers=auth_headers
            )
            
            assert response.status_code == 500
            data = response.json()
            assert data["detail"] == "Server error"


class TestGitEndpoints:
    """Test Git operation endpoints."""
    
    def test_git_status_success(self, api_client, auth_headers, mock_repo_path):
        """Test successful Git status retrieval."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "On branch main\nnothing to commit, working tree clean"
            
            response = api_client.get(
                "/git/status",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "branch" in data
            assert "status" in data
    
    def test_git_status_error(self, api_client, auth_headers, mock_repo_path):
        """Test Git status with error."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "fatal: not a git repository"
            
            response = api_client.get(
                "/git/status",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert "error" in data
    
    def test_git_status_unauthorized(self, api_client):
        """Test Git status without authentication."""
        response = api_client.get("/git/status")
        assert response.status_code == 401


class TestCrewEndpoints:
    """Test CrewAI operation endpoints."""
    
    def test_crew_plan_success(self, api_client, auth_headers, mock_repo_path):
        """Test successful crew planning."""
        response = api_client.post(
            "/crew/plan",
            json={
                "task_id": "2025-09-08-test-task",
                "prompt": "Plan the implementation"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["task_id"] == "2025-09-08-test-task"
    
    def test_crew_apply_success(self, api_client, auth_headers, mock_repo_path):
        """Test successful crew application."""
        response = api_client.post(
            "/crew/apply",
            json={
                "task_id": "2025-09-08-test-task",
                "run_id": "run-123"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["task_id"] == "2025-09-08-test-task"
    
    def test_crew_runs_success(self, api_client, auth_headers, mock_repo_path):
        """Test successful crew run retrieval."""
        response = api_client.get(
            "/crew/runs/run-123",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["run_id"] == "run-123"
    
    def test_crew_artefacts_success(self, api_client, auth_headers, mock_repo_path):
        """Test successful artefact upload."""
        response = api_client.post(
            "/crew/runs/run-123/artefacts",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["run_id"] == "run-123"


class TestErrorHandling:
    """Test error handling across endpoints."""
    
    def test_missing_pod_token(self, api_client):
        """Test behavior when POD_TOKEN is not set."""
        with patch.dict(os.environ, {}, clear=True):
            response = api_client.get("/health")
            # Health endpoint should still work without auth
            assert response.status_code == 200
            
            response = api_client.get("/tasks")
            assert response.status_code == 500
            data = response.json()
            assert "POD_TOKEN not configured" in data["detail"]
    
    def test_invalid_json(self, api_client, auth_headers):
        """Test handling of invalid JSON."""
        response = api_client.post(
            "/tasks/confirm",
            data="invalid json",
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_missing_required_fields(self, api_client, auth_headers):
        """Test handling of missing required fields."""
        response = api_client.post(
            "/tasks/confirm",
            json={},  # Missing required fields
            headers=auth_headers
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

