"""
Modular CrewAI Integration Tool for Cage Pod

This module implements the CrewAI integration using the new modular agent system,
providing dynamic crew construction and individual agent testing capabilities.
"""

import json
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from crewai import Crew, Process, Task
from crewai.tools import BaseTool
from pydantic import BaseModel

from ..agents import AgentFactory, AgentRegistry, CrewBuilder
from ..agents.committer import CommitterAgent, committer_config
from ..agents.config import AgentConfigManager
from ..agents.implementer import ImplementerAgent, implementer_config
from ..agents.planner import PlannerAgent, planner_config
from ..agents.reviewer import ReviewerAgent, reviewer_config
from ..agents.verifier import VerifierAgent, verifier_config
from ..models import TaskFile, TaskManager
from .editor_tool import EditorTool, FileOperation, OperationType
from .git_tool import GitTool


@dataclass
class RunStatus:
    """Status of a crew run."""

    run_id: str
    task_id: str
    status: str  # pending, running, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    logs: list[str] = None
    artefacts: list[str] = None


class ModularCrewTool:
    """
    Modular CrewAI integration tool for Cage Pod.

    This class provides a modular approach to CrewAI integration, allowing
    for dynamic crew construction and individual agent testing.
    """

    def __init__(self, repo_path: Path, task_manager: TaskManager):
        self.repo_path = repo_path
        self.task_manager = task_manager
        self.editor_tool = EditorTool(repo_path, task_manager=task_manager)
        self.git_tool = GitTool(repo_path)
        self.runs_dir = repo_path / ".cage" / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)

        # Initialize comprehensive logging
        self.logger = logging.getLogger(__name__)
        self._setup_crewai_logging()

        # Initialize modular agent system
        self._setup_modular_agents()

    def _setup_crewai_logging(self):
        """Set up comprehensive logging for CrewAI operations."""
        from src.cage.utils.jsonl_logger import setup_jsonl_logger

        # Set up JSONL logger for crewai
        self.crewai_logger = setup_jsonl_logger("crewai", level=logging.DEBUG)

        self.logger.info("CrewAI JSONL logging initialized")

    def _setup_modular_agents(self):
        """Set up the modular agent system."""
        self.logger.info("Setting up modular agent system...")

        # Initialize agent registry
        self.agent_registry = AgentRegistry(logger=self.logger)

        # Initialize agent factory
        self.agent_factory = AgentFactory(self.agent_registry, logger=self.logger)

        # Initialize crew builder
        self.crew_builder = CrewBuilder(self.agent_factory, logger=self.logger)

        # Initialize configuration manager
        self.config_manager = AgentConfigManager(logger=self.logger)

        # Register default agents
        self._register_default_agents()

        self.logger.info("Modular agent system initialized successfully")

    def _register_default_agents(self):
        """Register the default agents in the registry."""
        # Register all default agents
        self.agent_registry.register_agent(PlannerAgent, planner_config, "planner")
        self.agent_registry.register_agent(
            ImplementerAgent, implementer_config, "implementer"
        )
        self.agent_registry.register_agent(ReviewerAgent, reviewer_config, "reviewer")
        self.agent_registry.register_agent(VerifierAgent, verifier_config, "verifier")
        self.agent_registry.register_agent(
            CommitterAgent, committer_config, "committer"
        )

        self.logger.info(f"Registered {len(self.agent_registry)} default agents")

    def _log_agent_activity(
        self, agent_name: str, activity: str, details: dict[str, Any] = None
    ):
        """Log agent activity with structured details."""
        log_data = {
            "agent": agent_name,
            "activity": activity,
            "timestamp": datetime.now().isoformat(),
            "details": details or {},
        }
        self.crewai_logger.info(f"Agent Activity: {json.dumps(log_data)}")

    def _log_crew_execution(
        self,
        crew_name: str,
        task_name: str,
        status: str,
        details: dict[str, Any] = None,
    ):
        """Log crew execution details."""
        log_data = {
            "crew": crew_name,
            "task": task_name,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "details": details or {},
        }
        self.crewai_logger.info(f"Crew Execution: {json.dumps(log_data)}")

    def test_agent(
        self, agent_name: str, test_input: str, task_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Test an individual agent in isolation.

        Args:
            agent_name: Name of the agent to test
            test_input: Input to test the agent with
            task_id: Optional task ID to reference in the plan

        Returns:
            Test results dictionary
        """
        self.logger.info(f"Testing individual agent: {agent_name}")

        try:
            # Create agent instance with repo_path
            agent = self.agent_factory.create_agent(
                agent_name, repo_path=self.repo_path
            )
            if not agent:
                return {
                    "success": False,
                    "error": f"Agent '{agent_name}' not found",
                    "agent_name": agent_name,
                }

            # Inject appropriate tools based on agent type
            if agent_name in ("implementer", "reviewer", "verifier"):
                agent.config.tools = [EditorToolWrapper(self.editor_tool)]
                self.logger.info(f"Injected EditorTool into {agent_name} agent")
            elif agent_name == "committer":
                agent.config.tools = [GitToolWrapper(self.git_tool)]
                self.logger.info(f"Injected GitTool into {agent_name} agent")
            elif agent_name == "planner":
                agent.config.tools = [EditorToolWrapper(self.editor_tool)]
                self.logger.info(f"Injected EditorTool into {agent_name} agent")
            else:
                self.logger.info(f"No tools needed for {agent_name} agent")

            # Reinitialize agent with tools
            agent.initialize()

            # Test the agent
            result = agent.test_agent(test_input, task_id)

            self._log_agent_activity(
                agent_name,
                "Individual Test",
                {"test_input": test_input, "success": result["success"]},
            )

            return result

        except Exception as e:
            error_msg = f"Error testing agent {agent_name}: {e}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg, "agent_name": agent_name}

    def create_plan(self, task_id: str, plan_data: dict[str, Any]) -> dict[str, Any]:
        """Create a detailed plan for task execution using the modular system."""
        self.logger.info(f"Starting plan creation for task {task_id}")
        self._log_agent_activity(
            "Planner",
            "Plan Creation Started",
            {"task_id": task_id, "plan_data": plan_data},
        )

        try:
            # Load the task
            self.logger.debug(f"Loading task {task_id}")
            task = self.task_manager.load_task(task_id)
            if not task:
                error_msg = f"Task {task_id} not found"
                self.logger.error(error_msg)
                self._log_agent_activity(
                    "Planner",
                    "Plan Creation Failed",
                    {"task_id": task_id, "error": error_msg},
                )
                raise ValueError(error_msg)

            # Create run ID
            run_id = str(uuid.uuid4())
            self.logger.info(f"Created run ID: {run_id}")

            # Create run directory
            run_dir = self.runs_dir / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created run directory: {run_dir}")

            # Create planner agent
            planner_agent = self.agent_factory.create_agent("planner")
            if not planner_agent:
                raise ValueError("Failed to create planner agent")

            # Create plan task
            plan_task = Task(
                description=planner_agent.create_plan_task(
                    task_title=task.title,
                    task_summary=task.summary,
                    success_criteria=[c.text for c in task.success_criteria],
                    acceptance_checks=[c.text for c in task.acceptance_checks],
                ),
                agent=planner_agent.get_agent(),
                expected_output="A detailed JSON plan with Cage-native API calls, validation steps, and rollback paths",
            )

            # Execute planning crew
            self.logger.info("Executing planning crew with planner agent")
            self._log_crew_execution(
                "Planning Crew",
                task.title,
                "Started",
                {"run_id": run_id, "task_id": task_id, "agents": ["planner"]},
            )

            planning_crew = (
                self.crew_builder.reset()
                .add_agent(planner_agent)
                .add_task(plan_task)
                .build()
            )
            result = planning_crew.kickoff()

            self.logger.info("Planning crew execution completed")
            self._log_crew_execution(
                "Planning Crew",
                task.title,
                "Completed",
                {"run_id": run_id, "result_type": type(result).__name__},
            )

            # Convert CrewOutput to serializable format
            plan_content = str(result.raw) if hasattr(result, "raw") else str(result)
            self.logger.debug(f"Plan content length: {len(plan_content)} characters")

            # Save plan to run directory
            plan_file = run_dir / "plan.json"
            plan_data_to_save = {
                "run_id": run_id,
                "task_id": task_id,
                "created_at": datetime.now().isoformat(),
                "plan": plan_content,
                "raw_plan_data": plan_data,
            }

            with open(plan_file, "w") as f:
                json.dump(plan_data_to_save, f, indent=2)

            self.logger.info(f"Plan saved to: {plan_file}")

            # Update task with plan
            task_data = task.model_dump()
            task_data["plan"] = {
                "run_id": run_id,
                "created_at": datetime.now().isoformat(),
                "plan": plan_content,
            }

            self.task_manager.update_task(task_id, task_data)
            self.logger.info(f"Task {task_id} updated with plan information")

            self._log_agent_activity(
                "Planner",
                "Plan Creation Completed",
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "plan_length": len(plan_content),
                    "plan_file": str(plan_file),
                },
            )

            self.logger.info(
                f"Successfully created plan for task {task_id}, run {run_id}"
            )

            return {
                "status": "success",
                "run_id": run_id,
                "task_id": task_id,
                "plan": plan_content,
            }

        except Exception as e:
            error_msg = f"Error creating plan for task {task_id}: {e}"
            self.logger.error(error_msg)
            self._log_agent_activity(
                "Planner",
                "Plan Creation Failed",
                {"task_id": task_id, "error": str(e), "error_type": type(e).__name__},
            )
            return {"status": "error", "error": str(e)}

    def apply_plan(self, task_id: str, run_id: Optional[str] = None) -> dict[str, Any]:
        """Execute a plan using the modular crew system with validation loops."""
        self.logger.info(f"Starting plan application for task {task_id}, run {run_id}")
        self._log_agent_activity(
            "Crew", "Plan Application Started", {"task_id": task_id, "run_id": run_id}
        )

        try:
            # Load the task
            self.logger.debug(f"Loading task {task_id}")
            task = self.task_manager.load_task(task_id)
            if not task:
                error_msg = f"Task {task_id} not found"
                self.logger.error(error_msg)
                self._log_agent_activity(
                    "Crew",
                    "Plan Application Failed",
                    {"task_id": task_id, "error": error_msg},
                )
                raise ValueError(error_msg)

            # Get run ID
            if not run_id:
                if hasattr(task, "plan") and task.plan:
                    run_id = task.plan.get("run_id")
                    self.logger.info(f"Using run_id from task plan: {run_id}")
                else:
                    error_msg = "No run_id provided and no plan found in task"
                    self.logger.error(error_msg)
                    self._log_agent_activity(
                        "Crew",
                        "Plan Application Failed",
                        {"task_id": task_id, "error": error_msg},
                    )
                    raise ValueError(error_msg)

            # Load plan
            run_dir = self.runs_dir / run_id
            plan_file = run_dir / "plan.json"

            if not plan_file.exists():
                error_msg = f"Plan file not found for run {run_id}"
                self.logger.error(error_msg)
                self._log_agent_activity(
                    "Crew",
                    "Plan Application Failed",
                    {"task_id": task_id, "run_id": run_id, "error": error_msg},
                )
                raise ValueError(error_msg)

            self.logger.info(f"Loading plan from: {plan_file}")
            with open(plan_file) as f:
                plan_data = json.load(f)
            self.logger.debug(
                f"Plan data loaded successfully, plan length: {len(plan_data.get('plan', ''))}"
            )

            # Create run status
            run_status = RunStatus(
                run_id=run_id,
                task_id=task_id,
                status="running",
                started_at=datetime.now(),
                logs=[],
                artefacts=[],
            )

            # Save initial run status
            self._save_run_status(run_status)
            self.logger.info(f"Run status created and saved for run {run_id}")

            # Prepare criteria mapping for validation
            criteria_map, criteria_order = self._prepare_criteria_map(task)
            total_criteria = len(criteria_order)

            # Create execution agents with tools
            implementer_agent = self.agent_factory.create_agent("implementer")
            reviewer_agent = self.agent_factory.create_agent("reviewer")
            verifier_agent = self.agent_factory.create_agent("verifier")
            committer_agent = self.agent_factory.create_agent("committer")

            implementer_agent.config.tools = [EditorToolWrapper(self.editor_tool)]
            reviewer_agent.config.tools = [EditorToolWrapper(self.editor_tool)]
            verifier_agent.config.tools = [EditorToolWrapper(self.editor_tool)]
            committer_agent.config.tools = [GitToolWrapper(self.git_tool)]

            implementer_agent.initialize()
            reviewer_agent.initialize()
            verifier_agent.initialize()
            committer_agent.initialize()

            def run_impl_review(
                implementation_description: str,
                review_description: str,
                iteration: int,
                stage: str,
            ) -> Any:
                """Run the implementation + review crew for a given iteration."""
                crew_name = f"{stage} Crew"
                self.logger.info(
                    f"Starting {stage.lower()} iteration {iteration} for run {run_id}"
                )
                self._log_crew_execution(
                    crew_name,
                    task.title,
                    "Started",
                    {
                        "run_id": run_id,
                        "task_id": task_id,
                        "iteration": iteration,
                        "stage": stage.lower(),
                        "agents": ["implementer", "reviewer"],
                    },
                )

                implement_task = Task(
                    description=implementation_description,
                    agent=implementer_agent.get_agent(),
                    expected_output="Confirmation of successful file operations using EditorTool and changes made",
                )
                review_task = Task(
                    description=review_description,
                    agent=reviewer_agent.get_agent(),
                    expected_output="Review report confirming EditorTool usage and file quality, with approval or specific issues found",
                )
                crew = (
                    self.crew_builder.reset()
                    .add_agent(implementer_agent)
                    .add_agent(reviewer_agent)
                    .add_task(implement_task)
                    .add_task(review_task)
                    .set_process(Process.sequential)
                    .set_verbose(True)
                    .build()
                )

                result = crew.kickoff()
                result_output = self._extract_result_output(result)
                self._log_crew_execution(
                    crew_name,
                    task.title,
                    "Completed",
                    {
                        "run_id": run_id,
                        "task_id": task_id,
                        "iteration": iteration,
                        "stage": stage.lower(),
                        "result_type": type(result).__name__,
                        "result_length": len(result_output),
                    },
                )
                run_status.logs.append(
                    f"{stage} iteration {iteration}: {result_output}"
                )
                return result

            def run_verification(iteration: int) -> Any:
                """Execute the verification crew for the current iteration."""
                crew_name = "Verification Crew"
                self.logger.info(
                    f"Starting verification iteration {iteration} for run {run_id}"
                )
                verify_task = Task(
                    description=verifier_agent.create_verification_task(
                        task.title,
                        [c.text for c in task.success_criteria],
                        [c.text for c in task.acceptance_checks],
                    ),
                    agent=verifier_agent.get_agent(),
                    expected_output="Detailed validation report with PASS/FAIL for each acceptance criterion",
                )
                self._log_crew_execution(
                    crew_name,
                    task.title,
                    "Started",
                    {
                        "run_id": run_id,
                        "task_id": task_id,
                        "iteration": iteration,
                        "agents": ["verifier"],
                    },
                )
                crew = (
                    self.crew_builder.reset()
                    .add_agent(verifier_agent)
                    .add_task(verify_task)
                    .set_process(Process.sequential)
                    .set_verbose(True)
                    .build()
                )
                result = crew.kickoff()
                result_output = self._extract_result_output(result)
                self._log_crew_execution(
                    crew_name,
                    task.title,
                    "Completed",
                    {
                        "run_id": run_id,
                        "task_id": task_id,
                        "iteration": iteration,
                        "result_type": type(result).__name__,
                        "result_length": len(result_output),
                    },
                )
                run_status.logs.append(
                    f"Verification iteration {iteration}: {result_output}"
                )
                return result

            # Initial implementation pass
            initial_impl_description = implementer_agent.create_implementation_task(
                task_title=task.title, plan_content=plan_data.get("plan", "")
            )
            initial_review_description = reviewer_agent.create_review_task(task.title)
            run_impl_review(
                initial_impl_description,
                initial_review_description,
                1,
                "Implementation",
            )

            verification_history: list[dict[str, Any]] = []
            validation: Optional[dict[str, Any]] = None
            max_iterations = 10
            verification_iteration = 1

            if total_criteria == 0:
                validation = {
                    "results": [],
                    "summary": {
                        "total": 0,
                        "PASS": 0,
                        "FAIL": 0,
                        "PARTIAL": 0,
                        "MISSING": 0,
                        "UNKNOWN": 0,
                    },
                    "all_passed": True,
                    "progress_percent": 100,
                    "failed_items": [],
                    "raw_output": "",
                    "unmatched": [],
                }
            else:
                while verification_iteration <= max_iterations:
                    verification_result = run_verification(verification_iteration)
                    verification_output = self._extract_result_output(
                        verification_result
                    )
                    validation = self._parse_verification_output(
                        verification_output, criteria_map, criteria_order
                    )
                    verification_history.append(
                        {
                            "iteration": verification_iteration,
                            "summary": validation["summary"],
                            "output": verification_output,
                        }
                    )

                    if validation["all_passed"]:
                        break

                    if verification_iteration == max_iterations:
                        break

                    remediation_description = self._create_remediation_task_description(
                        task.title,
                        validation["failed_items"],
                        verification_iteration + 1,
                    )
                    remediation_review_description = (
                        reviewer_agent.create_review_task(task.title)
                        + "\n\nAdditional Focus: Ensure the fixes address each failed criterion listed in the implementer instructions."
                    )
                    run_impl_review(
                        remediation_description,
                        remediation_review_description,
                        verification_iteration + 1,
                        "Remediation",
                    )
                    verification_iteration += 1

                if validation is None:
                    validation = {
                        "results": [],
                        "summary": {
                            "total": total_criteria,
                            "PASS": 0,
                            "FAIL": total_criteria,
                            "PARTIAL": 0,
                            "MISSING": total_criteria,
                            "UNKNOWN": 0,
                        },
                        "all_passed": False,
                        "progress_percent": 0,
                        "failed_items": [],
                        "raw_output": "",
                        "unmatched": [],
                    }

            verification_timestamp = datetime.now().isoformat()

            task_data = task.model_dump()
            result_lookup = {
                (item["source"], item["index"]): item for item in validation["results"]
            }

            for idx, criterion in enumerate(task_data.get("success_criteria", [])):
                match = result_lookup.get(("success_criteria", idx))
                criterion["checked"] = bool(match and match["status"] == "PASS")
                criterion["verified_at"] = verification_timestamp
                criterion["evidence"] = match.get("evidence") if match else None
                criterion["verified_by"] = "automated_test"

            for idx, criterion in enumerate(task_data.get("acceptance_checks", [])):
                match = result_lookup.get(("acceptance_checks", idx))
                criterion["checked"] = bool(match and match["status"] == "PASS")
                criterion["verified_at"] = verification_timestamp
                criterion["evidence"] = match.get("evidence") if match else None
                criterion["verified_by"] = "automated_test"

            task_data["progress_percent"] = validation["progress_percent"]

            commit_attempted = validation["all_passed"]
            commit_success = False
            commit_output: Optional[str] = None

            if commit_attempted:
                commit_task = Task(
                    description=committer_agent.create_commit_task(task.title),
                    agent=committer_agent.get_agent(),
                    expected_output="Confirmation of successful commit with commit SHA",
                )
                commit_crew = (
                    self.crew_builder.reset()
                    .add_agent(committer_agent)
                    .add_task(commit_task)
                    .set_process(Process.sequential)
                    .set_verbose(True)
                    .build()
                )
                self._log_crew_execution(
                    "Commit Crew",
                    task.title,
                    "Started",
                    {
                        "run_id": run_id,
                        "task_id": task_id,
                        "iteration": verification_iteration,
                    },
                )
                try:
                    commit_result = commit_crew.kickoff()
                    commit_output = self._extract_result_output(commit_result)
                    commit_success = True
                    self._log_crew_execution(
                        "Commit Crew",
                        task.title,
                        "Completed",
                        {
                            "run_id": run_id,
                            "task_id": task_id,
                            "iteration": verification_iteration,
                            "result_type": type(commit_result).__name__,
                            "result_length": len(commit_output or ""),
                        },
                    )
                    run_status.logs.append(f"Commit: {commit_output}")
                except Exception as commit_error:
                    commit_output = str(commit_error)
                    commit_success = False
                    self.logger.error(f"Commit failed for run {run_id}: {commit_error}")
                    self._log_crew_execution(
                        "Commit Crew",
                        task.title,
                        "Failed",
                        {
                            "run_id": run_id,
                            "task_id": task_id,
                            "iteration": verification_iteration,
                            "error": commit_output,
                        },
                    )
                    run_status.logs.append(f"Commit failed: {commit_output}")

            summary = validation["summary"]
            task_data["changelog"].append(
                {
                    "timestamp": verification_timestamp,
                    "text": (
                        f"Validation results for run {run_id}: "
                        f"{summary['PASS']}/{summary['total']} passed, "
                        f"{summary['PARTIAL']} partial, {summary['FAIL']} failed, "
                        f"{summary['MISSING']} missing."
                    ),
                }
            )

            task_data.setdefault("issues_risks", [])
            if not validation["all_passed"]:
                outstanding = (
                    ", ".join(item["text"] for item in validation["failed_items"])
                    or "No criteria output captured"
                )
                task_data["issues_risks"].append(
                    f"{verification_timestamp}: Validation failed ({summary['PASS']}/{summary['total']} passed). Outstanding: {outstanding}"
                )
            elif not commit_success:
                task_data["issues_risks"].append(
                    f"{verification_timestamp}: Validation passed but commit failed - manual intervention required."
                )

            if validation["all_passed"] and commit_success:
                task_data["status"] = "done"
            elif validation["all_passed"]:
                task_data["status"] = "review"
            else:
                task_data["status"] = "blocked"

            task_data.setdefault("metadata", {})
            task_data["metadata"]["verification"] = {
                "run_id": run_id,
                "verified_at": verification_timestamp,
                "iterations": len(verification_history) if total_criteria else 0,
                "summary": summary,
                "history": verification_history,
                "unmatched": validation.get("unmatched", []),
            }

            self.task_manager.update_task(task_id, task_data)
            self.logger.info(f"Task {task_id} updated with execution results")

            run_status.completed_at = datetime.now()
            if validation["all_passed"] and commit_success:
                run_status.status = "completed"
            elif validation["all_passed"]:
                run_status.status = "failed"
                run_status.error = "Commit failed after successful validation"
            else:
                run_status.status = "failed"
                run_status.error = "Acceptance validation failed"

            self._save_run_status(run_status)
            self.logger.info(
                f"Run status updated to {run_status.status} for run {run_id}"
            )

            response_status = "success"
            if not validation["all_passed"]:
                response_status = "validation_failed"
            elif not commit_success:
                response_status = "commit_failed"

            self._log_agent_activity(
                "Crew",
                "Plan Application Completed",
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "status": response_status,
                    "validation_summary": summary,
                    "commit_success": commit_success,
                },
            )

            return {
                "status": response_status,
                "run_id": run_id,
                "task_id": task_id,
                "validation": {
                    "summary": summary,
                    "all_passed": validation["all_passed"],
                    "failed": [item["text"] for item in validation["failed_items"]],
                    "progress_percent": validation["progress_percent"],
                    "iterations": len(verification_history) if total_criteria else 0,
                },
                "commit": {
                    "attempted": commit_attempted,
                    "succeeded": commit_success,
                    "output": commit_output,
                },
            }

        except Exception as e:
            error_msg = f"Error executing plan for task {task_id}: {e}"
            self.logger.error(error_msg)

            self._log_agent_activity(
                "Crew",
                "Plan Application Failed",
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )

            if "run_status" in locals():
                run_status.status = "failed"
                run_status.completed_at = datetime.now()
                run_status.error = str(e)
                self._save_run_status(run_status)
                self.logger.info(f"Run status updated to failed for run {run_id}")

            return {"status": "error", "error": str(e)}

    def create_custom_crew(
        self,
        agent_names: list[str],
        tasks: list[Task],
        process: Process = Process.sequential,
    ) -> Crew:
        """
        Create a custom crew with specified agents and tasks.

        Args:
            agent_names: List of agent names to include
            tasks: List of tasks for the crew
            process: Crew process type

        Returns:
            Built CrewAI crew
        """
        self.logger.info(f"Creating custom crew with agents: {agent_names}")

        # Create crew builder
        builder = self.crew_builder.reset()

        # Add agents
        for agent_name in agent_names:
            agent = self.agent_factory.create_agent(agent_name)
            if agent:
                # Inject appropriate tools
                if agent_name in ("implementer", "reviewer", "verifier"):
                    agent.config.tools = [EditorToolWrapper(self.editor_tool)]
                elif agent_name == "committer":
                    agent.config.tools = [GitToolWrapper(self.git_tool)]

                # Reinitialize with tools
                agent.initialize()
                builder.add_agent(agent)
            else:
                self.logger.warning(f"Failed to create agent: {agent_name}")

        # Add tasks
        for task in tasks:
            builder.add_task(task)

        # Set process and build
        crew = builder.set_process(process).set_verbose(True).build()

        self.logger.info(
            f"Custom crew created with {len(crew.agents)} agents and {len(crew.tasks)} tasks"
        )
        return crew

    def list_available_agents(self) -> list[dict[str, Any]]:
        """
        List all available agents and their information.

        Returns:
            List of agent information dictionaries
        """
        return self.agent_registry.list_all_agent_info()

    def get_agent_info(self, agent_name: str) -> Optional[dict[str, Any]]:
        """
        Get information about a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Agent information dictionary or None if not found
        """
        return self.agent_registry.get_agent_info(agent_name)

    def get_run_status(self, run_id: str) -> dict[str, Any]:
        """Get the status of a crew run."""
        try:
            run_file = self.runs_dir / run_id / "status.json"

            if not run_file.exists():
                return {"status": "error", "error": f"Run {run_id} not found"}

            with open(run_file) as f:
                status_data = json.load(f)

            return {"status": "success", "run_data": status_data}

        except Exception as e:
            self.logger.error(f"Error getting run status for {run_id}: {e}")
            return {"status": "error", "error": str(e)}

    def upload_artefacts(self, run_id: str, files: dict[str, str]) -> dict[str, Any]:
        """Upload artefacts to a run directory."""
        try:
            run_dir = self.runs_dir / run_id
            artefacts_dir = run_dir / "artefacts"
            artefacts_dir.mkdir(parents=True, exist_ok=True)

            uploaded_files = []

            for filename, content in files.items():
                file_path = artefacts_dir / filename
                with open(file_path, "w") as f:
                    f.write(content)
                uploaded_files.append(str(file_path.relative_to(self.repo_path)))

            # Update run status with artefacts
            run_file = run_dir / "status.json"
            if run_file.exists():
                with open(run_file) as f:
                    status_data = json.load(f)

                if "artefacts" not in status_data:
                    status_data["artefacts"] = []

                status_data["artefacts"].extend(uploaded_files)

                with open(run_file, "w") as f:
                    json.dump(status_data, f, indent=2)

            self.logger.info(
                f"Uploaded {len(uploaded_files)} artefacts to run {run_id}"
            )

            return {
                "status": "success",
                "run_id": run_id,
                "uploaded_files": uploaded_files,
            }

        except Exception as e:
            self.logger.error(f"Error uploading artefacts for run {run_id}: {e}")
            return {"status": "error", "error": str(e)}

    def _prepare_criteria_map(
        self, task: TaskFile
    ) -> tuple[dict[str, list[dict[str, Any]]], list[tuple[str, int]]]:
        """Prepare normalized mappings for success criteria and acceptance checks."""
        criteria_map: dict[str, list[dict[str, Any]]] = {}
        criteria_order: list[tuple[str, int]] = []

        for idx, criterion in enumerate(task.success_criteria or []):
            normalized = self._normalize_criterion_text(criterion.text)
            bucket = criteria_map.setdefault(normalized, [])
            occurrence = len(bucket)
            bucket.append(
                {
                    "text": criterion.text,
                    "source": "success_criteria",
                    "index": idx,
                    "occurrence": occurrence,
                }
            )
            criteria_order.append((normalized, occurrence))

        for idx, criterion in enumerate(task.acceptance_checks or []):
            normalized = self._normalize_criterion_text(criterion.text)
            bucket = criteria_map.setdefault(normalized, [])
            occurrence = len(bucket)
            bucket.append(
                {
                    "text": criterion.text,
                    "source": "acceptance_checks",
                    "index": idx,
                    "occurrence": occurrence,
                }
            )
            criteria_order.append((normalized, occurrence))

        return criteria_map, criteria_order

    def _parse_verification_output(
        self,
        output: str,
        criteria_map: dict[str, list[dict[str, Any]]],
        criteria_order: list[tuple[str, int]],
    ) -> dict[str, Any]:
        """Parse verifier output into structured validation results."""
        assigned: dict[tuple[str, int], dict[str, Any]] = {}
        summary_counts = {
            "PASS": 0,
            "FAIL": 0,
            "PARTIAL": 0,
            "MISSING": 0,
            "UNKNOWN": 0,
        }
        unmatched_blocks: list[dict[str, Any]] = []

        blocks = re.split(r"(?im)^CRITERION:\s*", output or "")
        for block in blocks[1:]:
            block = block.strip()
            if not block:
                continue

            lines = block.splitlines()
            criterion_text = lines[0].strip()
            status = "UNKNOWN"
            evidence_lines: list[str] = []
            file_lines: list[str] = []
            current_field = None

            for line in lines[1:]:
                stripped = line.strip()
                upper = stripped.upper()

                if upper.startswith("STATUS:"):
                    status = stripped.split(":", 1)[1].strip().upper()
                    current_field = "status"
                elif upper.startswith("EVIDENCE:"):
                    value = stripped.split(":", 1)[1].strip()
                    evidence_lines = [value] if value else []
                    current_field = "evidence"
                elif upper.startswith("FILE:"):
                    value = stripped.split(":", 1)[1].strip()
                    file_lines = [value] if value else []
                    current_field = "file"
                else:
                    if current_field == "evidence":
                        evidence_lines.append(stripped)
                    elif current_field == "file":
                        file_lines.append(stripped)

            normalized = self._normalize_criterion_text(criterion_text)
            status_normalized = (
                status if status in {"PASS", "FAIL", "PARTIAL"} else "UNKNOWN"
            )
            evidence_text = "\n".join([line for line in evidence_lines if line]) or None
            file_ref = "\n".join([line for line in file_lines if line]) or None

            entry_assigned = False
            for entry in criteria_map.get(normalized, []):
                entry_key = (normalized, entry["occurrence"])
                if entry_key not in assigned:
                    assigned[entry_key] = {
                        "text": entry["text"],
                        "source": entry["source"],
                        "index": entry["index"],
                        "occurrence": entry["occurrence"],
                        "normalized": normalized,
                        "status": status_normalized,
                        "evidence": evidence_text,
                        "file": file_ref,
                        "raw_status": status,
                    }
                    entry_assigned = True
                    break

            if not entry_assigned:
                unmatched_blocks.append(
                    {
                        "text": criterion_text,
                        "status": status_normalized,
                        "evidence": evidence_text,
                        "file": file_ref,
                    }
                )

        results: list[dict[str, Any]] = []
        for normalized, occurrence in criteria_order:
            entry_key = (normalized, occurrence)
            result_entry = assigned.get(entry_key)

            if not result_entry:
                lookup_entry = next(
                    (
                        candidate
                        for candidate in criteria_map.get(normalized, [])
                        if candidate["occurrence"] == occurrence
                    ),
                    None,
                )
                if not lookup_entry:
                    continue
                result_entry = {
                    "text": lookup_entry["text"],
                    "source": lookup_entry["source"],
                    "index": lookup_entry["index"],
                    "occurrence": lookup_entry["occurrence"],
                    "normalized": normalized,
                    "status": "MISSING",
                    "evidence": "No verification output produced for this criterion.",
                    "file": None,
                    "raw_status": "MISSING",
                }

            status_key = result_entry["status"]
            if status_key not in summary_counts:
                status_key = "UNKNOWN"
                result_entry["status"] = "UNKNOWN"
            summary_counts[status_key] += 1
            results.append(result_entry)

        total = len(criteria_order)
        passed = summary_counts["PASS"]
        progress_percent = int((passed / total) * 100) if total else 100

        return {
            "results": results,
            "summary": {
                "total": total,
                "PASS": summary_counts["PASS"],
                "FAIL": summary_counts["FAIL"],
                "PARTIAL": summary_counts["PARTIAL"],
                "MISSING": summary_counts["MISSING"],
                "UNKNOWN": summary_counts["UNKNOWN"],
            },
            "failed_items": [item for item in results if item["status"] != "PASS"],
            "all_passed": total == 0 or passed == total,
            "progress_percent": progress_percent,
            "raw_output": output,
            "unmatched": unmatched_blocks,
        }

    def _create_remediation_task_description(
        self,
        task_title: str,
        failed_items: list[dict[str, Any]],
        iteration: int,
    ) -> str:
        """Create a focused remediation task description for failed criteria."""
        if not failed_items:
            return f"""Re-evaluate the implementation for task: {task_title}

Iteration {iteration}: Verification did not succeed, but no individual failures were captured.
Re-read all related files using the EditorTool and ensure every acceptance criterion is fully satisfied.
Avoid placeholders and confirm all endpoints and front-end flows are complete."""

        bullet_lines = []
        for item in failed_items:
            status = item.get("status", "UNKNOWN")
            evidence = item.get("evidence") or "No evidence captured by verifier."
            bullet_lines.append(
                f"- {item['text']} (status: {status})\n  Gap: {evidence}"
            )

        outstanding = "\n".join(bullet_lines)
        return f"""Address outstanding acceptance criteria for task: {task_title}

Iteration {iteration} outstanding items:
{outstanding}

Implementation Instructions:
1. Use the EditorTool to UPDATE existing files—do not leave placeholders or TODO comments.
2. Deliver complete, working functionality that satisfies each listed criterion.
3. Validate your changes via GET operations before concluding the update.
4. Provide intent descriptions referencing the criterion you are fixing."""

    def _extract_result_output(self, result: Any) -> str:
        """Convert crew results into a plain string for logging."""
        if result is None:
            return ""
        if isinstance(result, str):
            return result
        if hasattr(result, "raw"):
            return str(result.raw)
        return str(result)

    @staticmethod
    def _normalize_criterion_text(text: str) -> str:
        """Normalize criterion text for consistent matching."""
        return " ".join(text.lower().split())

    def _save_run_status(self, run_status: RunStatus):
        """Save run status to file."""
        run_dir = self.runs_dir / run_status.run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        status_file = run_dir / "status.json"
        status_data = {
            "run_id": run_status.run_id,
            "task_id": run_status.task_id,
            "status": run_status.status,
            "started_at": run_status.started_at.isoformat()
            if run_status.started_at
            else None,
            "completed_at": run_status.completed_at.isoformat()
            if run_status.completed_at
            else None,
            "error": run_status.error,
            "logs": run_status.logs or [],
            "artefacts": run_status.artefacts or [],
        }

        with open(status_file, "w") as f:
            json.dump(status_data, f, indent=2)


class EditorToolWrapper(BaseTool):
    """Wrapper for Editor Tool to be used by CrewAI agents."""

    name: str = "EditorTool"
    description: str = """Execute file operations through the Cage Editor Tool.

    IMPORTANT: This is the ONLY way to create, read, update, or delete files in this system.
    Do NOT use terminal commands like 'touch', 'mkdir', 'echo', etc. Use this tool instead.

    Operations:
    - INSERT: Create new files or insert content into existing files
    - GET: Read file content
    - UPDATE: Modify existing file content
    - DELETE: Remove files

    For creating new files, use INSERT with the full file content in the payload.

    Example for creating a Python file:
    {
        "operation": "INSERT",
        "path": "hello.py",
        "payload": {"content": "#!/usr/bin/env python3\\nprint('Hello, World!')"},
        "intent": "Create Hello World Python script"
    }

    Example for creating a directory structure:
    {
        "operation": "INSERT",
        "path": "subdir/file.txt",
        "payload": {"content": "File content here"},
        "intent": "Create file in subdirectory"
    }
    """

    class EditorToolArgs(BaseModel):
        operation: str
        path: str
        selector: Optional[dict] = None
        payload: Optional[dict] = None
        intent: str = ""
        dry_run: bool = False

    args_schema = EditorToolArgs
    editor_tool: EditorTool

    def __init__(self, editor_tool: EditorTool):
        super().__init__(editor_tool=editor_tool)

    def _run(
        self,
        operation: str,
        path: str,
        selector: dict = None,
        payload: dict = None,
        intent: str = "",
        dry_run: bool = False,
    ) -> str:
        """Execute a file operation through the Editor Tool."""
        # Get the crew tool logger for detailed logging
        crew_tool_logger = logging.getLogger(f"{__name__}.crewai")

        crew_tool_logger.info(
            f"EditorToolWrapper called: operation={operation}, path={path}, intent={intent}"
        )

        try:
            # Map common operation names to valid enum values
            operation_mapping = {
                "CREATE": "INSERT",
                "create": "INSERT",
                "WRITE": "INSERT",
                "write": "INSERT",
                "MAKE": "INSERT",
                "make": "INSERT",
                "NEW": "INSERT",
                "new": "INSERT",
                "READ": "GET",
                "read": "GET",
                "VIEW": "GET",
                "view": "GET",
                "MODIFY": "UPDATE",
                "modify": "UPDATE",
                "EDIT": "UPDATE",
                "edit": "UPDATE",
                "CHANGE": "UPDATE",
                "change": "UPDATE",
                "REMOVE": "DELETE",
                "remove": "DELETE",
                "DELETE": "DELETE",
                "delete": "DELETE",
            }

            # Use mapping if available, otherwise use the original operation
            mapped_operation = operation_mapping.get(operation, operation)
            crew_tool_logger.debug(
                f"Operation mapping: {operation} -> {mapped_operation}"
            )

            # Convert operation string to enum
            operation_type = OperationType(mapped_operation)

            # Create file operation
            file_op = FileOperation(
                operation=operation_type,
                path=path,
                selector=selector,
                payload=payload,
                intent=intent,
                dry_run=dry_run,
                author="agent:implementer",
                correlation_id=str(uuid.uuid4()),
            )

            crew_tool_logger.info(
                f"Executing file operation: {operation_type.value} on {path}"
            )

            # Execute operation
            result = self.editor_tool.execute_operation(file_op)

            # If update failed because the file is missing, retry as insert to create it.
            if (
                not result.ok
                and operation_type == OperationType.UPDATE
                and result.error
                and "File not found" in result.error
            ):
                crew_tool_logger.info(
                    f"Update failed due to missing file {path}; retrying as INSERT"
                )
                file_op.operation = OperationType.INSERT
                result = self.editor_tool.execute_operation(file_op)

            if result.ok:
                executed_operation = (
                    file_op.operation.value if file_op else operation_type.value
                )
                success_msg = f"✅ Successfully executed {executed_operation} on {path}\nDiff: {result.diff}"
                crew_tool_logger.info(
                    f"File operation successful: {executed_operation} on {path}"
                )
                return success_msg
            else:
                error_msg = (
                    f"❌ Failed to execute {operation} on {path}: {result.error}"
                )
                crew_tool_logger.error(
                    f"File operation failed: {operation} on {path} - {result.error}"
                )
                return error_msg

        except Exception as e:
            error_msg = f"❌ Error executing {operation} on {path}: {str(e)}"
            crew_tool_logger.error(
                f"File operation exception: {operation} on {path} - {str(e)}"
            )
            return error_msg


class GitToolWrapper(BaseTool):
    """Wrapper for Git Tool to be used by CrewAI agents."""

    name: str = "GitTool"
    description: str = 'Execute Git operations through the Git Tool. Use JSON format: {"operation": "commit", "message": "commit message"} or {"operation": "add"}'

    class GitToolArgs(BaseModel):
        operation: str
        message: Optional[str] = None
        remote: Optional[str] = "origin"
        branch: Optional[str] = None

    args_schema = GitToolArgs
    git_tool: GitTool

    def __init__(self, git_tool: GitTool):
        super().__init__(git_tool=git_tool)

    def _run(
        self,
        operation: str,
        message: str = None,
        remote: str = "origin",
        branch: str = None,
    ) -> str:
        """Execute a Git operation."""
        # Get the crew tool logger for detailed logging
        crew_tool_logger = logging.getLogger(f"{__name__}.crewai")

        crew_tool_logger.info(
            f"GitToolWrapper called: operation={operation}, message={message}, remote={remote}, branch={branch}"
        )

        try:
            if operation == "add":
                crew_tool_logger.info("Executing Git add operation")
                result = self.git_tool.add_files()
            elif operation == "commit":
                commit_message = message or "AI agent commit"
                status_check = self.git_tool.get_status()
                if status_check.success and status_check.data.get("is_clean", False):
                    crew_tool_logger.info(
                        "Working tree clean - skipping commit request"
                    )
                    return "No changes detected. Skipping git commit."

                crew_tool_logger.info(
                    f"Executing Git commit operation with message: {commit_message}"
                )
                result = self.git_tool.commit(commit_message)
            elif operation == "push":
                crew_tool_logger.info(
                    f"Executing Git push operation to {remote}/{branch}"
                )
                result = self.git_tool.push(remote, branch)
            elif operation == "status":
                crew_tool_logger.info("Retrieving Git status")
                result = self.git_tool.get_status()
                if result.success:
                    status_data = result.data
                    return json.dumps(
                        {
                            "current_branch": status_data.get("current_branch"),
                            "staged_files": status_data.get("staged_files", []),
                            "unstaged_files": status_data.get("unstaged_files", []),
                            "untracked_files": status_data.get("untracked_files", []),
                            "is_clean": status_data.get("is_clean", False),
                        }
                    )
            else:
                error_msg = f"Unknown Git operation: {operation}"
                crew_tool_logger.error(error_msg)
                return error_msg

            if result.success:
                success_msg = f"Successfully executed Git {operation}: {result.data}"
                crew_tool_logger.info(f"Git operation successful: {operation}")
                return success_msg
            else:
                error_msg = f"Failed to execute Git {operation}: {result.error}"
                crew_tool_logger.error(
                    f"Git operation failed: {operation} - {result.error}"
                )
                return error_msg

        except Exception as e:
            error_msg = f"Error executing Git {operation}: {str(e)}"
            crew_tool_logger.error(f"Git operation exception: {operation} - {str(e)}")
            return error_msg


# Backward compatibility alias
CrewTool = ModularCrewTool
