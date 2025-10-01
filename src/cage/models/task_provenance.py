"""
Task provenance model for Cage.

This module provides the TaskProvenance model for task provenance tracking.
"""


from pydantic import BaseModel

from .task_commit import TaskCommit


class TaskProvenance(BaseModel):
    """Task provenance tracking."""

    branch_from: str = ""
    work_branch: str = ""
    commits: list[TaskCommit] = []
    blobs_indexed: list[str] = []
