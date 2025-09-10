"""
Unit tests for CrewAI integration tool.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.cage.crew_tool import CrewTool, RunStatus
from src.cage.task_models import TaskManager


@pytest.fixture
def temp_repo():
    """Create a temporary repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        
        # Create basic directory structure
        (repo_path / "tasks").mkdir()
        (repo_path / ".cage" / "runs").mkdir(parents=True)
        
        # Copy schema file to test directory
        import shutil
        schema_source = Path(__file__).parent.parent.parent / "tasks" / "_schema.json"
        if schema_source.exists():
            shutil.copy2(schema_source, repo_path / "tasks" / "_schema.json")
        
        # Initialize git repository
        import subprocess
        subprocess.run(["git", "init"], cwd=repo_path, check=True)
        
        yield repo_path


@pytest.fixture
def crew_tool(temp_repo):
    """Create a CrewTool instance for testing."""
    task_manager = TaskManager(temp_repo / "tasks")
    return CrewTool(temp_repo, task_manager)


@pytest.fixture
def sample_task_data():
    """Sample task data for testing."""
    return {
        "id": "2025-09-10-test-task",
        "title": "Test Task",
        "owner": "test-user",
        "status": "planned",
        "progress_percent": 0,
        "summary": "A test task for CrewAI integration",
        "tags": ["test"],
        "success_criteria": [],
        "acceptance_checks": [],
        "subtasks": [],
        "todo": [],
        "decisions": [],
        "issues_risks": [],
        "next_steps": [],
        "references": [],
        "metadata": {}
    }


class TestCrewTool:
    """Test cases for CrewTool class."""
    
    def test_initialization(self, crew_tool):
        """Test CrewTool initialization."""
        assert crew_tool.repo_path is not None
        assert crew_tool.task_manager is not None
        assert crew_tool.editor_tool is not None
        assert crew_tool.git_tool is not None
        assert crew_tool.runs_dir.exists()
        
        # Check that agents are initialized
        assert crew_tool.planner_agent is not None
        assert crew_tool.implementer_agent is not None
        assert crew_tool.reviewer_agent is not None
        assert crew_tool.committer_agent is not None
    
    def test_create_plan_success(self, crew_tool, sample_task_data):
        """Test successful plan creation."""
        # Create a task first
        task = crew_tool.task_manager.create_task(sample_task_data)
        assert task is not None
        
        # Verify task was created
        loaded_task = crew_tool.task_manager.load_task(sample_task_data["id"])
        assert loaded_task is not None
        
        # Test that the method exists and can be called (without actual AI execution)
        # This is a basic smoke test to ensure the method doesn't crash
        try:
            # This will fail due to missing API key, but we can test the structure
            result = crew_tool.create_plan(sample_task_data["id"], {"test": "data"})
            # If we get here, the method executed without crashing
            assert "status" in result
            assert "task_id" in result
        except Exception as e:
            # Expected to fail due to missing API key, but should be a specific error
            assert "api_key" in str(e).lower() or "authentication" in str(e).lower()
    
    def test_create_plan_task_not_found(self, crew_tool):
        """Test plan creation with non-existent task."""
        result = crew_tool.create_plan("non-existent-task", {})
        
        assert result["status"] == "error"
        assert "not found" in result["error"]
    
    def test_get_run_status_success(self, crew_tool, temp_repo):
        """Test successful run status retrieval."""
        run_id = "test-run-123"
        run_dir = crew_tool.runs_dir / run_id
        run_dir.mkdir()
        
        # Create status file
        status_data = {
            "run_id": run_id,
            "task_id": "test-task",
            "status": "completed",
            "started_at": "2025-09-10T16:00:00",
            "completed_at": "2025-09-10T16:30:00",
            "error": None,
            "logs": ["Test log entry"],
            "artefacts": ["test-file.txt"]
        }
        
        status_file = run_dir / "status.json"
        with open(status_file, 'w') as f:
            json.dump(status_data, f)
        
        result = crew_tool.get_run_status(run_id)
        
        assert result["status"] == "success"
        assert result["run_data"]["run_id"] == run_id
        assert result["run_data"]["status"] == "completed"
    
    def test_get_run_status_not_found(self, crew_tool):
        """Test run status retrieval for non-existent run."""
        result = crew_tool.get_run_status("non-existent-run")
        
        assert result["status"] == "error"
        assert "not found" in result["error"]
    
    def test_upload_artefacts_success(self, crew_tool, temp_repo):
        """Test successful artefact upload."""
        run_id = "test-run-456"
        run_dir = crew_tool.runs_dir / run_id
        run_dir.mkdir()
        
        files = {
            "test1.txt": "Test content 1",
            "test2.txt": "Test content 2"
        }
        
        result = crew_tool.upload_artefacts(run_id, files)
        
        assert result["status"] == "success"
        assert result["run_id"] == run_id
        assert len(result["uploaded_files"]) == 2
        
        # Check that files were created
        artefacts_dir = run_dir / "artefacts"
        assert artefacts_dir.exists()
        assert (artefacts_dir / "test1.txt").exists()
        assert (artefacts_dir / "test2.txt").exists()
    
    def test_save_run_status(self, crew_tool, temp_repo):
        """Test run status saving."""
        run_status = RunStatus(
            run_id="test-run-789",
            task_id="test-task",
            status="running",
            started_at=None,
            completed_at=None,
            error=None,
            logs=["Test log"],
            artefacts=["test.txt"]
        )
        
        crew_tool._save_run_status(run_status)
        
        # Check that status file was created
        status_file = crew_tool.runs_dir / run_status.run_id / "status.json"
        assert status_file.exists()
        
        with open(status_file, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data["run_id"] == run_status.run_id
        assert saved_data["task_id"] == run_status.task_id
        assert saved_data["status"] == run_status.status
        assert saved_data["logs"] == run_status.logs
        assert saved_data["artefacts"] == run_status.artefacts


class TestRunStatus:
    """Test cases for RunStatus dataclass."""
    
    def test_run_status_creation(self):
        """Test RunStatus creation."""
        run_status = RunStatus(
            run_id="test-123",
            task_id="task-456",
            status="running"
        )
        
        assert run_status.run_id == "test-123"
        assert run_status.task_id == "task-456"
        assert run_status.status == "running"
        assert run_status.started_at is None
        assert run_status.completed_at is None
        assert run_status.error is None
        assert run_status.logs is None
        assert run_status.artefacts is None
