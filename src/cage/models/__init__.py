"""
Task models for Cage.

This module provides all task-related data models and validation.
"""

from .task_criteria import TaskCriteria
from .task_todo_item import TaskTodoItem
from .task_changelog_entry import TaskChangelogEntry
from .task_prompt import TaskPrompt
from .task_lock import TaskLock
from .task_migration import TaskMigration
from .task_plan import TaskPlan
from .task_commit import TaskCommit
from .task_provenance import TaskProvenance
from .task_artefacts import TaskArtefacts
from .task_file import TaskFile
from .task_manager import TaskManager
from .file_editing_models import (
    FileContentResponse,
    FileCreateUpdateRequest,
    FileCreateUpdateResponse,
    CommitInfo,
    JsonPatchRequest,
    TextPatchRequest,
    LinePatchRequest,
    FileDeleteRequest,
    AuditEntry,
    AuditQueryParams,
    AuditResponse,
    FileOperationError
)

__all__ = [
    "TaskCriteria",
    "TaskTodoItem", 
    "TaskChangelogEntry",
    "TaskPrompt",
    "TaskLock",
    "TaskMigration",
    "TaskPlan",
    "TaskCommit",
    "TaskProvenance",
    "TaskArtefacts",
    "TaskFile",
    "TaskManager",
    "FileContentResponse",
    "FileCreateUpdateRequest",
    "FileCreateUpdateResponse",
    "CommitInfo",
    "JsonPatchRequest",
    "TextPatchRequest",
    "LinePatchRequest",
    "FileDeleteRequest",
    "AuditEntry",
    "AuditQueryParams",
    "AuditResponse",
    "FileOperationError",
]
