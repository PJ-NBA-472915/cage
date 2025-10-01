"""
Planner Agent Module

This module defines the Planner agent for creating detailed execution plans
using Cage-native API endpoints.
"""

from typing import Any, Optional

from .base import AgentConfig, AgentType, BaseAgent


class PlannerAgent(BaseAgent):
    """
    Planner agent for creating detailed execution plans.

    This agent specializes in analyzing tasks and creating comprehensive,
    step-by-step plans that break down complex work into manageable,
    executable steps using Cage-native API endpoints.
    """

    def _get_agent_type(self) -> AgentType:
        """Return the agent type."""
        return AgentType.PLANNER

    def _get_tools(self) -> list:
        """
        Get the tools for the planner agent.

        The planner agent doesn't use tools directly - it creates plans
        that other agents will execute.

        Returns:
            Empty list (planner doesn't use tools)
        """
        return []

    @classmethod
    def create_default_config(cls) -> AgentConfig:
        """
        Create a default configuration for the planner agent.

        Returns:
            Default agent configuration
        """
        return AgentConfig(
            role="Planner",
            goal="Create detailed, actionable plans for task execution using Cage-native API endpoints",
            backstory="""You are an expert software architect and project planner.
            You analyze tasks and create comprehensive, step-by-step plans that break down
            complex work into manageable, executable steps. You consider dependencies,
            risks, and best practices in your planning.

            CRITICAL: All plans MUST use Cage-native API endpoints only:
            - Use POST /files/edit for all file operations (INSERT, UPDATE, DELETE)
            - Use GET /files/sha for content validation
            - Use GET /diff for change validation
            - Use POST /git/revert for rollback operations
            - Use POST /runner/exec for optional execution checks
            - Use POST /git/open_pr for pull request creation
            - Use POST /tasks/update for task updates

            NEVER include terminal commands like 'touch', 'mkdir', 'echo', etc.
            Always include validation steps and rollback paths.
            Include branch names and task-linked commit messages.

            PLAN SAVING REQUIREMENTS:
            1. ALWAYS save the plan as a JSON file in the .cage/plans/ directory
            2. Use filename format: plan-{task-id}-{timestamp}.json
            3. Include a taskFileReference field in the plan JSON that references the task file
            4. Use the EditorTool to create the plan file

            Output format must be EXACTLY this JSON structure (no markdown, no code blocks):
            {
              "taskName": "Task Title",
              "taskId": "task-id",
              "taskFileReference": ".cage/tasks/{task-id}.json",
              "goal": "Clear goal description",
              "branch": "chore/task-name-YYYY-MM-DD",
              "createdAt": "YYYY-MM-DDTHH:MM:SSZ",
              "steps": [
                {
                  "name": "Step description",
                  "request": {
                    "method": "POST",
                    "path": "/files/edit",
                    "body": {
                      "operation": "INSERT",
                      "path": "file.py",
                      "payload": {"content": "file content"},
                      "intent": "Create file",
                      "author": "planner",
                      "correlation_id": "task-id"
                    }
                  },
                  "validate": [
                    "GET /files/sha?path=file.py -> returns non-empty sha",
                    "GET /diff?branch=chore/task-name-YYYY-MM-DD -> shows added file"
                  ],
                  "onFailure": {
                    "action": "abort",
                    "rollback": {
                      "method": "POST",
                      "path": "/git/revert",
                      "body": {"branch": "chore/task-name-YYYY-MM-DD", "to": "HEAD~1"}
                    }
                  }
                }
              ]
            }

            CRITICAL WORKFLOW:
            1. First, create the plan JSON content
            2. Use EditorTool to save the plan to .cage/plans/plan-{task-id}-{timestamp}.json
            3. Return the plan JSON content (not the file creation result)

            CRITICAL: Return ONLY the JSON object, no markdown formatting, no code blocks, no additional text.
            """,
            verbose=True,
            allow_delegation=False,
            tools=[],
            metadata={
                "specialization": "planning",
                "output_format": "json",
                "api_endpoints": [
                    "POST /files/edit",
                    "GET /files/sha",
                    "GET /diff",
                    "POST /git/revert",
                    "POST /runner/exec",
                    "POST /git/open_pr",
                    "POST /tasks/update",
                ],
            },
        )

    def create_plan_task(
        self,
        task_title: str,
        task_summary: str,
        success_criteria: list[str],
        acceptance_checks: list[str],
    ) -> str:
        """
        Create a task description for plan creation.

        Args:
            task_title: Title of the task to plan
            task_summary: Summary of the task
            success_criteria: List of success criteria
            acceptance_checks: List of acceptance checks

        Returns:
            Task description for the planner
        """
        return f"""Create a detailed execution plan for task: {task_title}

        Task Summary: {task_summary}
        Success Criteria: {success_criteria}
        Acceptance Checks: {acceptance_checks}

        Create a Cage-native execution plan that uses only API endpoints:
        - Use POST /files/edit for all file operations (INSERT, UPDATE, DELETE)
        - Use GET /files/sha for content validation
        - Use GET /diff for change validation
        - Use POST /git/revert for rollback operations
        - Use POST /runner/exec for optional execution checks
        - Use POST /git/open_pr for pull request creation
        - Use POST /tasks/update for task updates

        Include:
        1. Branch name following convention: chore/task-name-YYYY-MM-DD
        2. Task-linked commit messages with format: "type: description (links: task {task_title})"
        3. Validation steps for each operation
        4. Rollback paths for failure scenarios
        5. Idempotent operations that can be re-run safely

        Output must be valid JSON following the Cage-native plan schema."""

    def test_agent(
        self, test_input: str, task_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Test the planner agent with enhanced plan saving functionality.

        Args:
            test_input: Input to test the agent with
            task_id: Optional task ID to reference in the plan

        Returns:
            Dictionary containing test results
        """
        import json
        from datetime import datetime

        if not self._initialized:
            self.initialize()

        self.logger.info(f"Testing planner agent with input: {test_input[:100]}...")

        try:
            # Create a simple test task
            from crewai import Task

            # Add task_id context to the test input if provided
            enhanced_input = test_input
            if task_id:
                enhanced_input = f"{test_input}\n\nTask ID: {task_id}\nTask File Reference: .cage/tasks/{task_id}.json"

            test_task = Task(
                description=enhanced_input,
                agent=self.crewai_agent,
                expected_output="Test response from planner agent",
            )

            # Execute the task
            result = test_task.execute_sync()

            # Parse the JSON result
            try:
                plan_data = json.loads(str(result))
            except json.JSONDecodeError:
                # If not valid JSON, wrap it
                plan_data = {"raw_output": str(result)}

            # Add task reference if task_id provided
            if task_id and isinstance(plan_data, dict):
                plan_data["taskFileReference"] = f".cage/tasks/{task_id}.json"
                plan_data["createdAt"] = datetime.now().isoformat() + "Z"

            # Save plan to file if we have a task_id
            if task_id and isinstance(plan_data, dict):
                try:
                    # Ensure .cage/plans directory exists
                    plans_dir = self.repo_path / ".cage" / "plans"
                    plans_dir.mkdir(parents=True, exist_ok=True)

                    # Generate filename with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                    plan_filename = f"plan-{task_id}-{timestamp}.json"
                    plan_path = plans_dir / plan_filename

                    # Save the plan to file
                    with open(plan_path, "w") as f:
                        json.dump(plan_data, f, indent=2)

                    self.logger.info(f"Plan saved to {plan_path}")

                    # Add plan file reference to the response
                    plan_data["planFile"] = str(plan_path.relative_to(self.repo_path))

                except Exception as e:
                    self.logger.error(f"Failed to save plan to file: {e}")

            return {
                "success": True,
                "agent_type": self.agent_type.value,
                "role": self.config.role,
                "input": test_input,
                "output": json.dumps(plan_data, indent=2),
                "error": None,
            }

        except Exception as e:
            self.logger.error(f"Error testing planner agent: {e}")
            return {
                "success": False,
                "agent_type": self.agent_type.value,
                "role": self.config.role,
                "input": test_input,
                "output": None,
                "error": str(e),
            }


# Default configuration instance
planner_config = PlannerAgent.create_default_config()
