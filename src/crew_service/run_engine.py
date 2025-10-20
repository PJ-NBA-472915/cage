"""
Run engine and state machine for CrewAI service.

Manages task execution and state transitions.
"""

import logging
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
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

    def __init__(self, runs_db: dict[UUID, Run] | None = None):
        self._active_runs: dict[UUID, Run] = {}
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
                run.result_summary = result.get(
                    "output", f"Task '{task.title}' completed successfully"
                )
                run.artefacts = result.get("artefacts", [])
                logger.info(f"Agent run {run.id} completed successfully")
            else:
                run.status = RunState.FAILED.value
                run.result_summary = (
                    f"Task failed: {result.get('error', 'Unknown error')}"
                )
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
        """Execute a crew run using ModularCrewTool with full workflow."""
        logger.info(
            f"Starting crew run {run.id} for crew {crew_id} with strategy {strategy}"
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

            # Create a task ID for tracking this crew execution
            # Format: YYYY-MM-DD-slug (matching TaskFile pattern requirement)
            from datetime import datetime as dt

            date_prefix = dt.now().strftime("%Y-%m-%d")
            title_slug = task.title.lower().replace(" ", "-")[:30]
            task_id = f"{date_prefix}-{title_slug}"
            logger.info(f"Creating task {task_id} for crew run tracking")

            # Create task data for TaskManager
            task_data = {
                "id": task_id,
                "title": task.title,
                "summary": task.description,
                "success_criteria": [
                    {"text": criterion, "checked": False}
                    for criterion in task.acceptance
                ],
                "acceptance_checks": [
                    {"text": criterion, "checked": False}
                    for criterion in task.acceptance
                ],
                "status": "in-progress",
                "owner": "crew",
                "created_at": dt.now().isoformat(),
                "updated_at": dt.now().isoformat(),
                "progress_percent": 0,
                "tags": ["crew-execution", str(crew_id)],
                "todo": [],
                "changelog": [
                    {
                        "timestamp": dt.now().isoformat(),
                        "text": f"Crew execution started for run {run.id}",
                    }
                ],
                "decisions": [],
                "lessons_learned": [],
                "issues_risks": [],
                "next_steps": [],
                "references": [],
                "prompts": [],
                "locks": [],
                "migration": {
                    "migrated": False,
                    "source_path": None,
                    "method": None,
                    "migrated_at": None,
                },
                "plan": {
                    "title": "",
                    "assumptions": [],
                    "steps": [],
                    "commit_message": "",
                },
                "provenance": {
                    "branch_from": "",
                    "work_branch": "",
                    "commits": [],
                    "blobs_indexed": [],
                },
                "artefacts": {
                    "run_id": str(run.id),
                    "logs": [],
                    "reports": [],
                    "diff_bundles": [],
                    "external": [],
                },
                "metadata": {},
            }

            # Create task in TaskManager
            created_task = self.task_manager.create_task(task_data)
            if not created_task:
                raise ValueError(f"Failed to create task {task_id}")

            logger.info(f"Task {task_id} created successfully")

            # Phase 1: Create plan
            logger.info(f"Phase 1: Creating plan for task {task_id}")
            plan_result = self.crew_tool.create_plan(task_id, {"strategy": strategy})

            if plan_result.get("status") != "success":
                raise ValueError(f"Plan creation failed: {plan_result.get('error')}")

            run_id_from_plan = plan_result.get("run_id")
            logger.info(f"Plan created successfully with run_id: {run_id_from_plan}")

            # Check for cancellation after planning
            if run.id in self._cancelled_runs:
                run.status = RunState.CANCELLED.value
                run.finished_at = datetime.utcnow()
                self._cancelled_runs.discard(run.id)
                return run

            # Phase 2: Apply plan (implement → review → commit)
            logger.info(f"Phase 2: Applying plan for task {task_id}")
            apply_result = self.crew_tool.apply_plan(task_id, run_id_from_plan)

            if apply_result.get("status") != "success":
                raise ValueError(
                    f"Plan application failed: {apply_result.get('error')}"
                )

            logger.info("Plan applied successfully")

            # Update run with execution results
            run.status = RunState.SUCCEEDED.value
            run.finished_at = datetime.utcnow()
            run.result_summary = f"Crew task '{task.title}' completed successfully. Plan: {run_id_from_plan}"
            run.artefacts = [
                f".cage/runs/{run_id_from_plan}/plan.json",
                f".cage/runs/{run_id_from_plan}/status.json",
            ]

            logger.info(f"Crew run {run.id} completed successfully")

        except Exception as e:
            logger.error(f"Crew run {run.id} failed with exception: {str(e)}")
            run.status = RunState.FAILED.value
            run.finished_at = datetime.utcnow()
            run.result_summary = f"Crew task failed: {str(e)}"

        finally:
            if run.id in self._active_runs:
                del self._active_runs[run.id]
            # Update runs_db with final run state
            if self.runs_db is not None:
                self.runs_db[run.id] = run

        return run

    async def cancel_run(self, run_id: UUID) -> bool:
        """Cancel an active run."""
        logger.info(f"Cancelling run {run_id}")

        if run_id in self._active_runs:
            self._cancelled_runs.add(run_id)
            return True

        return False

    def get_active_runs(self) -> dict[UUID, Run]:
        """Get all currently active runs."""
        return self._active_runs.copy()

    def is_run_active(self, run_id: UUID) -> bool:
        """Check if a run is currently active."""
        return run_id in self._active_runs


# Global run engine instance (will be initialized by router with runs_db)
run_engine = None
