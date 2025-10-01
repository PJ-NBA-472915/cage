"""
Task lock model for Cage.

This module provides the TaskLock model for file locks in multi-agent collaboration.
"""

from typing import Optional

from pydantic import BaseModel, Field


class TaskLock(BaseModel):
    """File lock for multi-agent collaboration."""

    id: str
    file_path: str
    ranges: list[dict[str, int]] = Field(..., min_items=1)
    description: str
    agent: str
    started_at: str
    completed_at: Optional[str] = None
    status: str = Field(..., pattern="^(active|released|aborted|stale)$")
