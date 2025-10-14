"""
Run engine and state machine for CrewAI service.

Manages task execution and state transitions.
"""

import asyncio
import logging
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict
from uuid import UUID

from src.models.crewai import Run, TaskSpec

logger = logging.getLogger(__name__)


class RunState(Enum):
    """Run state enumeration."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunEngine:
    """Engine for managing task execution and state transitions."""

    def __init__(self):
        self._active_runs: Dict[UUID, Run] = {}
        self._cancelled_runs: set = set()

        # Configure repository path from environment
        repo_path_str = os.getenv("REPO_PATH", "/work/repo")
        self.repo_path = Path(repo_path_str)
        logger.info(f"RunEngine initialized with repo_path: {self.repo_path}")

    async def execute_agent_run(self, run: Run, agent_id: UUID, task: TaskSpec) -> Run:
        """Execute a single agent run."""
        logger.info(f"Starting agent run {run.id} for agent {agent_id}")

        try:
            # Update state to running
            run.status = RunState.RUNNING.value
            run.started_at = datetime.utcnow()
            self._active_runs[run.id] = run

            # Simulate agent execution
            await asyncio.sleep(1)  # Simulate work

            # Check for cancellation
            if run.id in self._cancelled_runs:
                run.status = RunState.CANCELLED.value
                run.finished_at = datetime.utcnow()
                self._cancelled_runs.discard(run.id)
                return run

            # Simulate successful completion
            run.status = RunState.SUCCEEDED.value
            run.finished_at = datetime.utcnow()
            run.result_summary = f"Task '{task.title}' completed successfully"
            run.artefacts = [f"artefact_{run.id}_output.txt"]

            logger.info(f"Agent run {run.id} completed successfully")

        except Exception as e:
            logger.error(f"Agent run {run.id} failed: {str(e)}")
            run.status = RunState.FAILED.value
            run.finished_at = datetime.utcnow()
            run.result_summary = f"Task failed: {str(e)}"

        finally:
            if run.id in self._active_runs:
                del self._active_runs[run.id]

        return run

    async def execute_crew_run(
        self,
        run: Run,
        crew_id: UUID,
        task: TaskSpec,
        strategy: str = "impl_then_verify",
    ) -> Run:
        """Execute a crew run with specified strategy."""
        logger.info(
            f"Starting crew run {run.id} for crew {crew_id} with strategy {strategy}"
        )

        try:
            # Update state to running
            run.status = RunState.RUNNING.value
            run.started_at = datetime.utcnow()
            self._active_runs[run.id] = run

            # Simulate crew execution based on strategy
            if strategy == "impl_then_verify":
                # Simulate implementation phase
                await asyncio.sleep(1)

                # Check for cancellation
                if run.id in self._cancelled_runs:
                    run.status = RunState.CANCELLED.value
                    run.finished_at = datetime.utcnow()
                    self._cancelled_runs.discard(run.id)
                    return run

                # Simulate verification phase
                await asyncio.sleep(1)

            # Check for cancellation again
            if run.id in self._cancelled_runs:
                run.status = RunState.CANCELLED.value
                run.finished_at = datetime.utcnow()
                self._cancelled_runs.discard(run.id)
                return run

            # Simulate successful completion
            run.status = RunState.SUCCEEDED.value
            run.finished_at = datetime.utcnow()
            run.result_summary = (
                f"Crew task '{task.title}' completed using strategy '{strategy}'"
            )
            run.artefacts = [
                f"artefact_{run.id}_implementation.txt",
                f"artefact_{run.id}_verification.txt",
                f"artefact_{run.id}_summary.txt",
            ]

            logger.info(f"Crew run {run.id} completed successfully")

        except Exception as e:
            logger.error(f"Crew run {run.id} failed: {str(e)}")
            run.status = RunState.FAILED.value
            run.finished_at = datetime.utcnow()
            run.result_summary = f"Crew task failed: {str(e)}"

        finally:
            if run.id in self._active_runs:
                del self._active_runs[run.id]

        return run

    async def cancel_run(self, run_id: UUID) -> bool:
        """Cancel an active run."""
        logger.info(f"Cancelling run {run_id}")

        if run_id in self._active_runs:
            self._cancelled_runs.add(run_id)
            return True

        return False

    def get_active_runs(self) -> Dict[UUID, Run]:
        """Get all currently active runs."""
        return self._active_runs.copy()

    def is_run_active(self, run_id: UUID) -> bool:
        """Check if a run is currently active."""
        return run_id in self._active_runs


# Global run engine instance
run_engine = RunEngine()
