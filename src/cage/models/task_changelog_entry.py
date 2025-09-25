"""
Task changelog entry model for Cage.

This module provides the TaskChangelogEntry model for changelog entries with optional lock information.
"""

from typing import Optional
from pydantic import BaseModel


class TaskChangelogEntry(BaseModel):
    """Changelog entry with optional lock information."""
    timestamp: str
    text: str
    lock_id: Optional[str] = None
    file_path: Optional[str] = None
