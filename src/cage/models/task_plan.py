"""
Task plan model for Cage.

This module provides the TaskPlan model for task execution plans.
"""

from typing import Any

from pydantic import BaseModel


class TaskPlan(BaseModel):
    """Task execution plan."""

    title: str = ""
    assumptions: list[str] = []
    steps: list[dict[str, Any]] = []
    commit_message: str = ""
