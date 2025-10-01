"""
Task criteria model for Cage.

This module provides the TaskCriteria model for success criteria or acceptance check items.
"""

from pydantic import BaseModel


class TaskCriteria(BaseModel):
    """Success criteria or acceptance check item."""

    text: str
    checked: bool = False
