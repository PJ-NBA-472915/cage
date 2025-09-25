"""
Task provenance model for Cage.

This module provides the TaskProvenance model for task provenance tracking.
"""

from typing import List
from pydantic import BaseModel
from .task_commit import TaskCommit


class TaskProvenance(BaseModel):
    """Task provenance tracking."""
    branch_from: str = ""
    work_branch: str = ""
    commits: List[TaskCommit] = []
    blobs_indexed: List[str] = []
