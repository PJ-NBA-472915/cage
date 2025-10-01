"""
Task commit model for Cage.

This module provides the TaskCommit model for git commit information.
"""

from pydantic import BaseModel


class TaskCommit(BaseModel):
    """Git commit information."""

    sha: str
    title: str
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0
