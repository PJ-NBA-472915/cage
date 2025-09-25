"""
Task migration model for Cage.

This module provides the TaskMigration model for migration tracking information.
"""

from typing import Optional
from pydantic import BaseModel, Field


class TaskMigration(BaseModel):
    """Migration tracking information."""
    migrated: bool
    source_path: Optional[str] = None
    method: Optional[str] = Field(None, pattern="^(script|manual)$")
    migrated_at: Optional[str] = None
