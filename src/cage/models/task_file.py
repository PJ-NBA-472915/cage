"""
Task file model for Cage.

This module provides the TaskFile model for complete task file data.
"""

from datetime import datetime
from typing import Dict, List, Any
from pydantic import BaseModel, Field, field_validator, model_validator

from .task_criteria import TaskCriteria
from .task_todo_item import TaskTodoItem
from .task_changelog_entry import TaskChangelogEntry
from .task_prompt import TaskPrompt
from .task_lock import TaskLock
from .task_migration import TaskMigration
from .task_plan import TaskPlan
from .task_provenance import TaskProvenance
from .task_artefacts import TaskArtefacts


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
