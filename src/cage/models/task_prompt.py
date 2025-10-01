"""
Task prompt model for Cage.

This module provides the TaskPrompt model for user prompt entries in the audit trail.
"""

from pydantic import BaseModel


class TaskPrompt(BaseModel):
    """User prompt entry for audit trail."""

    timestamp: str
    text: str
    context: str
