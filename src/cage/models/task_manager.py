"""
Task manager for Cage.

This module provides the TaskManager class for task file management operations.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union

import jsonschema

from .task_commit import TaskCommit
from .task_file import TaskFile
from .task_provenance import TaskProvenance
from .task_todo_item import TaskTodoItem


class TaskManager:
    """Task file management operations."""

    def __init__(self, tasks_dir: Union[str, Path] = Path("tasks")):
        self.tasks_dir = Path(tasks_dir)
        self.repo_root = self.tasks_dir.parent
        self.tasks_dir.mkdir(exist_ok=True)
        self.schema_path = self.tasks_dir / "_schema.json"
        self.status_path = self.tasks_dir / "_status.json"

        # Copy schema file from main cage repository if it doesn't exist
        self._ensure_schema_file()

    def _ensure_schema_file(self):
        """Ensure schema file exists by copying from main cage repository if needed."""
        if not self.schema_path.exists():
            # Try to find the main cage repository schema file
            # Look for it relative to the current working directory or in common locations
            possible_schema_paths = [
                Path("tasks/_schema.json"),  # Main cage repository
                Path("/app/tasks/_schema.json"),  # Docker container path
                Path.cwd() / "tasks" / "_schema.json",  # Current working directory
            ]

            for schema_path in possible_schema_paths:
                if schema_path.exists():
                    try:
                        import shutil

                        shutil.copy2(schema_path, self.schema_path)
                        print(
                            f"Copied schema file from {schema_path} to {self.schema_path}"
                        )
                        return
                    except Exception as e:
                        print(f"Failed to copy schema file from {schema_path}: {e}")
                        continue

            print(
                "Warning: Could not find schema file to copy. Task validation may fail."
            )

    def load_schema(self) -> dict[str, Any]:
        """Load the JSON schema for validation."""
        if self.schema_path.exists():
            with open(self.schema_path) as f:
                return json.load(f)
        else:
            raise FileNotFoundError("Task schema not found")

    def validate_task(self, task_data: dict[str, Any]) -> tuple[bool, str]:
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
            with open(task_path) as f:
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
            task_dict = task.model_dump()
            with open(task_path, "w") as f:
                json.dump(task_dict, f, indent=2)
            print(f"Successfully saved task {task.id} to {task_path}")
            return True
        except Exception as e:
            print(f"Error saving task {task.id} to {task_path}: {e}")
            import traceback

            traceback.print_exc()
            return False

    def create_task(self, task_data: dict[str, Any]) -> Optional[TaskFile]:
        """Create a new task from data."""
        try:
            # Set timestamps if not provided
            now = datetime.now().isoformat()
            if "created_at" not in task_data:
                task_data["created_at"] = now
            if "updated_at" not in task_data:
                task_data["updated_at"] = now

            task = TaskFile(**task_data)
            if self.save_task(task):
                return task
            return None
        except ValueError as e:
            print(f"Error creating task: {e}")
            return None

    def update_task(self, task_id: str, updates: dict[str, Any]) -> Optional[TaskFile]:
        """Update an existing task."""
        task = self.load_task(task_id)
        if not task:
            return None

        # Convert existing task to dict and merge with updates
        task_data = task.model_dump()
        task_data.update(updates)

        # Update timestamp
        task_data["updated_at"] = datetime.now().isoformat()

        # Reconstruct TaskFile from updated data to ensure proper validation
        try:
            updated_task = TaskFile(**task_data)
            if self.save_task(updated_task):
                return updated_task
            return None
        except ValueError as e:
            print(f"Error updating task {task_id}: {e}")
            return None

    def list_tasks(self) -> list[dict[str, Any]]:
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

                tasks.append(
                    {
                        "id": task.id,
                        "title": task.title,
                        "status": task.status,
                        "progress_percent": task.progress_percent,
                        "updated_at": task.updated_at,
                        "summary": task.summary,
                        "latest_work": latest_work,
                    }
                )

        return sorted(tasks, key=lambda x: x["updated_at"], reverse=True)

    def rebuild_status(self) -> dict[str, Any]:
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
            "recently_completed": recently_completed,
        }

        status_path = self.tasks_dir / "_status.json"
        try:
            with open(status_path, "w") as f:
                json.dump(status_data, f, indent=2)
            return status_data
        except Exception as e:
            print(f"Error saving status: {e}")
            return {}

    def update_task_provenance(
        self, task_id: str, commit_info: dict[str, Any]
    ) -> Optional[TaskFile]:
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
            deletions=commit_info.get("deletions", 0),
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

    def validate_tasks(self) -> list[dict[str, Any]]:
        """Validate all tasks in the tasks directory."""
        results = []
        for task_file in self.list_task_paths():
            task_id = task_file.stem
            try:
                with open(task_file) as f:
                    task_data = json.load(f)
                is_valid, error_msg = self.validate_task(task_data)
                if is_valid:
                    results.append({"task_id": task_id, "status": "valid"})
                else:
                    results.append(
                        {"task_id": task_id, "status": "invalid", "error": error_msg}
                    )
            except Exception as e:
                results.append(
                    {"task_id": task_id, "status": "invalid", "error": str(e)}
                )
        return results

    def list_task_paths(self) -> list[Path]:
        """List all task file paths."""
        return [p for p in self.tasks_dir.glob("*.json") if not p.name.startswith("_")]

    def _format_error(self, error: jsonschema.ValidationError) -> str:
        """Format a validation error message."""
        path_str = ".".join(str(p) for p in error.path) if error.path else "<root>"
        return f"Validation error at {path_str}: {error.message}"

    def generate_status(self) -> dict[str, Any]:
        """Generate status dictionary from tasks."""
        return self.rebuild_status()

    def write_status(self) -> Optional[Path]:
        """Write the status file and return its path."""
        status_data = self.rebuild_status()
        status_path = self.tasks_dir / "_status.json"
        try:
            with open(status_path, "w") as f:
                json.dump(status_data, f, indent=2)
            return status_path
        except Exception:
            return None

    def _calculate_progress_percent(self, todo_items: list[TaskTodoItem]) -> int:
        """Calculate progress percentage from todo items."""
        if not todo_items:
            return 0
        completed = sum(1 for item in todo_items if item.status == "done")
        total = len(todo_items)
        return int((completed / total) * 100) if total > 0 else 0
