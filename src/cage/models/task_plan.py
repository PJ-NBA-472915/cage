"""
Task plan model for Cage.

This module provides the TaskPlan model for task execution plans.
"""

from typing import List, Dict, Any
from pydantic import BaseModel


class TaskPlan(BaseModel):
    """Task execution plan."""
    title: str = ""
    assumptions: List[str] = []
    steps: List[Dict[str, Any]] = []
    commit_message: str = ""
