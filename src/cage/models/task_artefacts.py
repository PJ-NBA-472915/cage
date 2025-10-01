"""
Task artefacts model for Cage.

This module provides the TaskArtefacts model for task artefacts and outputs.
"""

from typing import Any

from pydantic import BaseModel


class TaskArtefacts(BaseModel):
    """Task artefacts and outputs."""

    run_id: str = ""
    logs: list[str] = []
    reports: list[str] = []
    diff_bundles: list[str] = []
    external: list[dict[str, Any]] = []
