"""
Task file data models and validation for Cage.

This module provides Pydantic models for task file validation and manipulation.
"""

import json
import jsonschema
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator


class TaskCriteria(BaseModel):
    """Success criteria or acceptance check item."""
    text: str
    checked: bool = False


class TaskTodoItem(BaseModel):
    """Todo item with status and timing."""
    text: str
    status: str = Field(..., pattern="^(not-started|done|blocked|failed)$")
    date_started: Optional[str] = None
    date_stopped: Optional[str] = None


class TaskChangelogEntry(BaseModel):
    """Changelog entry with optional lock information."""
    timestamp: str
    text: str
    lock_id: Optional[str] = None
    file_path: Optional[str] = None


class TaskPrompt(BaseModel):
    """User prompt entry for audit trail."""
    timestamp: str
    text: str
    context: str


class TaskLock(BaseModel):
    """File lock for multi-agent collaboration."""
    id: str
    file_path: str
    ranges: List[Dict[str, int]] = Field(..., min_items=1)
    description: str
    agent: str
    started_at: str
    completed_at: Optional[str] = None
    status: str = Field(..., pattern="^(active|released|aborted|stale)$")


class TaskMigration(BaseModel):
    """Migration tracking information."""
    migrated: bool
    source_path: Optional[str] = None
    method: Optional[str] = Field(None, pattern="^(script|manual)$")
    migrated_at: Optional[str] = None


class TaskPlan(BaseModel):
    """Task execution plan."""
    title: str = ""
    assumptions: List[str] = []
    steps: List[Dict[str, Any]] = []
    commit_message: str = ""


class TaskCommit(BaseModel):
    """Git commit information."""
    sha: str
    title: str
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0


class TaskProvenance(BaseModel):
    """Task provenance tracking."""
    branch_from: str = ""
    work_branch: str = ""
    commits: List[TaskCommit] = []
    blobs_indexed: List[str] = []


class TaskArtefacts(BaseModel):
    """Task artefacts and outputs."""
    run_id: str = ""
    logs: List[str] = []
    reports: List[str] = []
    diff_bundles: List[str] = []
    external: List[Dict[str, Any]] = []


class TaskFile(BaseModel):
    """Complete task file model."""
    id: str = Field(..., pattern="^\\d{4}-\\d{2}-\\d{2}-[a-z0-9-]+$")
    title: str = Field(..., min_length=1)
    owner: str = Field(..., min_length=1)
    status: str = Field(..., pattern="^(planned|in-progress|blocked|review|done|abandoned)$")
    created_at: str
    updated_at: str
    progress_percent: int = Field(..., ge=0, le=100)
    tags: List[str] = []
    summary: str = ""
    success_criteria: List[TaskCriteria] = []
    acceptance_checks: List[TaskCriteria] = []
    subtasks: List[str] = []
    todo: List[TaskTodoItem] = []
    changelog: List[TaskChangelogEntry] = []
    decisions: List[str] = []
    lessons_learned: List[str] = []
    issues_risks: List[str] = []
    next_steps: List[str] = []
    references: List[str] = []
    prompts: List[TaskPrompt] = []
    locks: List[TaskLock] = []
    migration: TaskMigration = TaskMigration(migrated=False)
    plan: TaskPlan = TaskPlan()
    provenance: TaskProvenance = TaskProvenance()
    artefacts: TaskArtefacts = TaskArtefacts()
    metadata: Dict[str, Any] = {}

    @field_validator('progress_percent')
    @classmethod
    def calculate_progress(cls, v, info):
        """Calculate progress from todo items if not explicitly set."""
        if info.data and 'todo' in info.data and info.data['todo']:
            todo_items = info.data['todo']
            if todo_items:
                completed = sum(1 for item in todo_items if item.status == 'done')
                total = len(todo_items)
                return int((completed / total) * 100) if total > 0 else 0
        return v

    @model_validator(mode='after')
    def validate_timestamps(self):
        """Validate timestamp formats."""
        for field in ['created_at', 'updated_at']:
            value = getattr(self, field)
            if value:
                try:
                    datetime.fromisoformat(value)
                except ValueError:
                    raise ValueError(f"Invalid timestamp format for {field}")
        return self

    class Config:
        extra = "forbid"


class TaskManager:
    """Task file management operations."""
    
    def __init__(self, tasks_dir: Union[str, Path] = Path("tasks")):
        self.tasks_dir = Path(tasks_dir)
        self.repo_root = self.tasks_dir.parent
        self.tasks_dir.mkdir(exist_ok=True)
        self.schema_path = self.tasks_dir / "_schema.json"
        self.status_path = self.tasks_dir / "_status.json"
    
    def load_schema(self) -> Dict[str, Any]:
        """Load the JSON schema for validation."""
        if self.schema_path.exists():
            with open(self.schema_path, 'r') as f:
                return json.load(f)
        else:
            raise FileNotFoundError("Task schema not found")
    
    def validate_task(self, task_data: Dict[str, Any]) -> tuple[bool, str]:
        """Validate task data against schema."""
        try:
            schema = self.load_schema()
            jsonschema.validate(task_data, schema)
            return True, ""
        except (jsonschema.ValidationError, FileNotFoundError) as e:
            print(f"Validation error: {e}")
            return False, str(e)
    
    def load_task(self, task_id: str) -> Optional[TaskFile]:
        """Load a task file by ID."""
        task_path = self.tasks_dir / f"{task_id}.json"
        if not task_path.exists():
            return None
        
        try:
            with open(task_path, 'r') as f:
                task_data = json.load(f)
            
            is_valid, _ = self.validate_task(task_data)
            if is_valid:
                return TaskFile(**task_data)
            else:
                return None
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error loading task {task_id}: {e}")
            return None
    
    def save_task(self, task: TaskFile) -> bool:
        """Save a task file."""
        task_path = self.tasks_dir / f"{task.id}.json"
        try:
            with open(task_path, 'w') as f:
                json.dump(task.model_dump(), f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving task {task.id}: {e}")
            return False
    
    def create_task(self, task_data: Dict[str, Any]) -> Optional[TaskFile]:
        """Create a new task from data."""
        try:
            # Set timestamps if not provided
            now = datetime.now().isoformat()
            if 'created_at' not in task_data:
                task_data['created_at'] = now
            if 'updated_at' not in task_data:
                task_data['updated_at'] = now
            
            task = TaskFile(**task_data)
            if self.save_task(task):
                return task
            return None
        except ValueError as e:
            print(f"Error creating task: {e}")
            return None
    
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> Optional[TaskFile]:
        """Update an existing task."""
        task = self.load_task(task_id)
        if not task:
            return None
        
        # Update fields
        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        # Update timestamp
        task.updated_at = datetime.now().isoformat()
        
        if self.save_task(task):
            return task
        return None
    
    def list_tasks(self) -> List[Dict[str, Any]]:
        """List all task files."""
        tasks = []
        for task_file in self.tasks_dir.glob("*.json"):
            if task_file.name.startswith("_"):  # Skip schema and status files
                continue
            
            task_id = task_file.stem
            task = self.load_task(task_id)
            if task:
                # Get latest changelog entry
                latest_work = ""
                if task.changelog:
                    latest_work = task.changelog[-1].text
                
                tasks.append({
                    "id": task.id,
                    "title": task.title,
                    "status": task.status,
                    "progress_percent": task.progress_percent,
                    "updated_at": task.updated_at,
                    "summary": task.summary,
                    "latest_work": latest_work
                })
        
        return sorted(tasks, key=lambda x: x["updated_at"], reverse=True)
    
    def rebuild_status(self) -> Dict[str, Any]:
        """Rebuild the _status.json file from all tasks."""
        tasks = self.list_tasks()
        
        active_tasks = []
        recently_completed = []
        
        for task in tasks:
            if task["status"] in ["planned", "in-progress", "blocked", "review"]:
                active_tasks.append(task)
            elif task["status"] == "done":
                task["done_on"] = task["updated_at"]
                recently_completed.append(task)
        
        # Limit recently completed to 3 most recent
        recently_completed = recently_completed[:3]
        
        status_data = {
            "active_tasks": active_tasks,
            "recently_completed": recently_completed
        }
        
        status_path = self.tasks_dir / "_status.json"
        try:
            with open(status_path, 'w') as f:
                json.dump(status_data, f, indent=2)
            return status_data
        except Exception as e:
            print(f"Error saving status: {e}")
            return {}
    
    def update_task_provenance(self, task_id: str, commit_info: Dict[str, Any]) -> Optional[TaskFile]:
        """Update task provenance with commit information."""
        task = self.load_task(task_id)
        if not task:
            return None
        
        # Create commit object
        commit = TaskCommit(
            sha=commit_info.get("sha", ""),
            title=commit_info.get("title", ""),
            files_changed=commit_info.get("files_changed", 0),
            insertions=commit_info.get("insertions", 0),
            deletions=commit_info.get("deletions", 0)
        )
        
        # Add to provenance commits
        task.provenance.commits.insert(0, commit)  # Insert at beginning
        
        # Update timestamp
        task.updated_at = datetime.now().isoformat()
        
        if self.save_task(task):
            return task
        return None
    
    def get_task_provenance(self, task_id: str) -> Optional[TaskProvenance]:
        """Get task provenance information."""
        task = self.load_task(task_id)
        if task:
            return task.provenance
        return None

    def validate_tasks(self) -> List[Dict[str, Any]]:
        """Validate all tasks in the tasks directory."""
        results = []
        for task_file in self.list_task_paths():
            task_id = task_file.stem
            try:
                with open(task_file, 'r') as f:
                    task_data = json.load(f)
                is_valid, error_msg = self.validate_task(task_data)
                if is_valid:
                    results.append({"task_id": task_id, "status": "valid"})
                else:
                    results.append({"task_id": task_id, "status": "invalid", "error": error_msg})
            except Exception as e:
                results.append({"task_id": task_id, "status": "invalid", "error": str(e)})
        return results

    def list_task_paths(self) -> List[Path]:
        """List all task file paths."""
        return [p for p in self.tasks_dir.glob("*.json") if not p.name.startswith("_")]

    def _format_error(self, error: jsonschema.ValidationError) -> str:
        """Format a validation error message."""
        path_str = '.'.join(str(p) for p in error.path) if error.path else '<root>'
        return f"Validation error at {path_str}: {error.message}"

    def generate_status(self) -> Dict[str, Any]:
        """Generate status dictionary from tasks."""
        return self.rebuild_status()

    def write_status(self) -> Optional[Path]:
        """Write the status file and return its path."""
        status_data = self.rebuild_status()
        status_path = self.tasks_dir / "_status.json"
        try:
            with open(status_path, 'w') as f:
                json.dump(status_data, f, indent=2)
            return status_path
        except Exception:
            return None

    def _calculate_progress_percent(self, todo_items: List[TaskTodoItem]) -> int:
        """Calculate progress percentage from todo items."""
        if not todo_items:
            return 0
        completed = sum(1 for item in todo_items if item.status == 'done')
        total = len(todo_items)
        return int((completed / total) * 100) if total > 0 else 0
