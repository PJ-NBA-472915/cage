"""
Task criteria model for Cage.

This module provides the TaskCriteria model for success criteria or acceptance check items.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class TaskCriteria(BaseModel):
    """Success criteria or acceptance check item."""

    text: str
    checked: bool = False
    verified_at: Optional[str] = None
    evidence: Optional[str] = None
    verified_by: Optional[str] = None

    @field_validator("verified_at")
    @classmethod
    def validate_verified_at(cls, value: Optional[str]) -> Optional[str]:
        """Ensure verified_at is ISO formatted when provided."""
        if value is None:
            return value
        try:
            datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("verified_at must be ISO formatted") from exc
        return value
