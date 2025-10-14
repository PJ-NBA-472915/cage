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
from typing import Dict, Optional
from uuid import UUID

from src.cage.models import TaskManager
from src.cage.tools.crew_tool import ModularCrewTool
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

    def __init__(self, runs_db: Optional[Dict[UUID, Run]] = None):
        self._active_runs: Dict[UUID, Run] = {}
        self._cancelled_runs: set = set()
        self.runs_db = runs_db if runs_db is not None else {}

        # Configure repository path from environment
        repo_path_str = os.getenv("REPO_PATH", "/work/repo")
        self.repo_path = Path(repo_path_str)
        logger.info(f"RunEngine initialized with repo_path: {self.repo_path}")

        # Initialize TaskManager for task tracking
        tasks_dir = self.repo_path / "tasks"
        self.task_manager = TaskManager(tasks_dir=tasks_dir)
        logger.info(f"TaskManager initialized with tasks_dir: {tasks_dir}")

        # Initialize ModularCrewTool with EditorTool integration
        self.crew_tool = ModularCrewTool(
            repo_path=self.repo_path, task_manager=self.task_manager
        )
        logger.info("ModularCrewTool initialized with EditorTool integration")

    async def execute_agent_run(
        self, run: Run, agent_id: UUID, agent_role: str, task: TaskSpec
    ) -> Run:
        """Execute a single agent run using ModularCrewTool."""
        logger.info(
            f"Starting agent run {run.id} for agent {agent_id} with role {agent_role}"
        )

        try:
            # Update state to running
            run.status = RunState.RUNNING.value
            run.started_at = datetime.utcnow()
            self._active_runs[run.id] = run

            # Check for cancellation
            if run.id in self._cancelled_runs:
                run.status = RunState.CANCELLED.value
                run.finished_at = datetime.utcnow()
                self._cancelled_runs.discard(run.id)
                return run

            # Execute agent through ModularCrewTool
            task_input = f"Task: {task.title}\nDescription: {task.description}\nAcceptance Criteria:\n"
            for idx, criterion in enumerate(task.acceptance, 1):
                task_input += f"{idx}. {criterion}\n"

            logger.info(f"Executing agent {agent_role} with task: {task.title}")
            result = self.crew_tool.test_agent(agent_role, task_input)

            # Update run with execution results
            if result.get("success", False):
                run.status = RunState.SUCCEEDED.value
                run.result_summary = result.get("output", f"Task '{task.title}' completed successfully")
                run.artefacts = result.get("artefacts", [])
                logger.info(f"Agent run {run.id} completed successfully")
            else:
                run.status = RunState.FAILED.value
                run.result_summary = f"Task failed: {result.get('error', 'Unknown error')}"
                logger.error(f"Agent run {run.id} failed: {result.get('error')}")

            run.finished_at = datetime.utcnow()

        except Exception as e:
            logger.error(f"Agent run {run.id} failed with exception: {str(e)}")
            run.status = RunState.FAILED.value
            run.finished_at = datetime.utcnow()
            run.result_summary = f"Task failed: {str(e)}"

        finally:
            if run.id in self._active_runs:
                del self._active_runs[run.id]
            # Update runs_db with final run state
            if self.runs_db is not None:
                self.runs_db[run.id] = run

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


# Global run engine instance (will be initialized by router with runs_db)
run_engine = None
