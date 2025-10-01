"""
Task todo item model for Cage.

This module provides the TaskTodoItem model for todo items with status and timing.
"""

from typing import Optional

from pydantic import BaseModel, Field


class TaskTodoItem(BaseModel):
    """Todo item with status and timing."""

    text: str
    status: str = Field(..., pattern="^(not-started|done|blocked|failed)$")
    date_started: Optional[str] = None
    date_stopped: Optional[str] = None
