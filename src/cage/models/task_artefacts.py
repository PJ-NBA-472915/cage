"""
Task artefacts model for Cage.

This module provides the TaskArtefacts model for task artefacts and outputs.
"""

from typing import List, Dict, Any
from pydantic import BaseModel


class TaskArtefacts(BaseModel):
    """Task artefacts and outputs."""
    run_id: str = ""
    logs: List[str] = []
    reports: List[str] = []
    diff_bundles: List[str] = []
    external: List[Dict[str, Any]] = []
