"""
Modular CrewAI Integration Tool for Cage Pod

This module implements the CrewAI integration using the new modular agent system,
providing dynamic crew construction and individual agent testing capabilities.
"""

import json
import logging
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
from ..models import TaskManager
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
        from src.cage.utils.daily_logger import setup_daily_logger

        # Set up daily logger for crewai
        self.crewai_logger = setup_daily_logger("crewai", level=logging.DEBUG)

        self.logger.info("CrewAI daily logging initialized")

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
            if agent_name == "implementer" or agent_name == "reviewer":
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

            planning_crew = self.crew_builder.reset().add_agent(planner_agent).build()
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
        """Execute a plan using the modular crew system."""
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

            # Create execution agents with tools
            implementer_agent = self.agent_factory.create_agent("implementer")
            reviewer_agent = self.agent_factory.create_agent("reviewer")
            committer_agent = self.agent_factory.create_agent("committer")

            # Inject tools into agents
            implementer_agent.config.tools = [EditorToolWrapper(self.editor_tool)]
            reviewer_agent.config.tools = [EditorToolWrapper(self.editor_tool)]
            committer_agent.config.tools = [GitToolWrapper(self.git_tool)]

            # Reinitialize agents with tools
            implementer_agent.initialize()
            reviewer_agent.initialize()
            committer_agent.initialize()

            # Create execution tasks
            implement_task = Task(
                description=implementer_agent.create_implementation_task(
                    task_title=task.title, plan_content=plan_data.get("plan", "")
                ),
                agent=implementer_agent.get_agent(),
                expected_output="Confirmation of successful file operations using EditorTool and changes made",
            )

            review_task = Task(
                description=reviewer_agent.create_review_task(task.title),
                agent=reviewer_agent.get_agent(),
                expected_output="Review report confirming EditorTool usage and file quality, with approval or specific issues found",
            )

            commit_task = Task(
                description=committer_agent.create_commit_task(task.title),
                agent=committer_agent.get_agent(),
                expected_output="Confirmation of successful commit with commit SHA",
            )

            # Execute the crew workflow
            self.logger.info(
                "Creating execution crew with Implementer, Reviewer, and Committer agents"
            )
            self._log_crew_execution(
                "Execution Crew",
                task.title,
                "Started",
                {
                    "run_id": run_id,
                    "task_id": task_id,
                    "agents": ["implementer", "reviewer", "committer"],
                    "tasks": ["implement_task", "review_task", "commit_task"],
                },
            )

            execution_crew = (
                self.crew_builder.reset()
                .add_agent(implementer_agent)
                .add_agent(reviewer_agent)
                .add_agent(committer_agent)
                .add_task(implement_task)
                .add_task(review_task)
                .add_task(commit_task)
                .set_process(Process.sequential)
                .set_verbose(True)
                .build()
            )

            # Execute the crew
            self.logger.info("Starting crew execution...")
            result = execution_crew.kickoff()
            self.logger.info("Crew execution completed")
            self._log_crew_execution(
                "Execution Crew",
                task.title,
                "Completed",
                {
                    "run_id": run_id,
                    "result_type": type(result).__name__,
                    "result_length": len(str(result)) if result else 0,
                },
            )

            # Update run status
            run_status.status = "completed"
            run_status.completed_at = datetime.now()
            run_status.logs.append(f"Crew execution completed: {result}")

            self._save_run_status(run_status)
            self.logger.info(f"Run status updated to completed for run {run_id}")

            # Update task progress
            task_data = task.model_dump()
            task_data["status"] = "in-progress"
            task_data["progress_percent"] = 75  # After implementation
            task_data["changelog"].append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "text": f"Crew execution completed for run {run_id}",
                }
            )

            self.task_manager.update_task(task_id, task_data)
            self.logger.info(f"Task {task_id} updated with execution results")

            self._log_agent_activity(
                "Crew",
                "Plan Application Completed",
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "status": "success",
                    "result_type": type(result).__name__,
                },
            )

            self.logger.info(
                f"Successfully executed plan for task {task_id}, run {run_id}"
            )

            return {
                "status": "success",
                "run_id": run_id,
                "task_id": task_id,
                "result": result,
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

            # Update run status with error
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
                if agent_name == "implementer" or agent_name == "reviewer":
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
