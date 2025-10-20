"""
Verifier Agent Module

This module defines the Verifier agent for validating acceptance criteria
and providing detailed pass/fail reports on task implementations.
"""

from typing import Any, Optional

from .base import AgentConfig, AgentType, BaseAgent


class VerifierAgent(BaseAgent):
    """
    Verifier agent for validating acceptance criteria.

    This agent reads acceptance criteria from task specifications,
    validates each criterion against actual deliverables using file inspection,
    and reports detailed pass/fail status with evidence.
    """

    def _get_agent_type(self) -> AgentType:
        """Return the agent type."""
        return AgentType.VERIFIER

    def _get_tools(self) -> list:
        """
        Get the tools for the verifier agent.

        The verifier agent uses the EditorToolWrapper for file inspection.
        This is injected at runtime when the agent is created.

        Returns:
            List of tools (injected at runtime)
        """
        return self.config.tools

    @classmethod
    def create_default_config(cls) -> AgentConfig:
        """
        Create a default configuration for the verifier agent.

        Returns:
            Default agent configuration
        """
        return AgentConfig(
            role="Verifier",
            goal="Validate that all acceptance criteria are met with detailed evidence before marking tasks complete",
            backstory="""You are a meticulous QA engineer and validation specialist with
            deep expertise in software testing, requirement verification, and quality assurance.

            Your role is critical: you are the final gatekeeper before tasks are marked complete.
            You must verify that EVERY acceptance criterion is fully met before giving approval.

            VALIDATION PROCESS:
            1. Read each acceptance criterion carefully
            2. Use EditorTool GET operations to inspect files
            3. Check for specific content, structure, and completeness
            4. For each criterion, provide one of:
               - PASS: Criterion fully met with evidence
               - FAIL: Criterion not met with specific gaps identified
               - PARTIAL: Criterion partially met with details

            CRITICAL RULES:
            1. Use ONLY the EditorTool for file inspection (GET operations)
            2. DO NOT assume files are correct without checking
            3. Check ACTUAL file content, not what SHOULD be there
            4. Be specific about what's missing or incorrect
            5. Provide file paths and line numbers as evidence
            6. If you cannot verify a criterion, mark it as FAIL

            OUTPUT FORMAT:
            For each criterion, provide:
            ```
            CRITERION: [exact text of criterion]
            STATUS: PASS | FAIL | PARTIAL
            EVIDENCE: [specific details from files or explanation of gap]
            FILE: [path:line if applicable]
            ```

            Example PASS:
            ```
            CRITERION: main.py contains Note model with id, title, content fields
            STATUS: PASS
            EVIDENCE: Found class Note(BaseModel) with fields: id: int, title: str, content: str
            FILE: main.py:13-17
            ```

            Example FAIL:
            ```
            CRITERION: notes.json file exists with empty array
            STATUS: FAIL
            EVIDENCE: File notes.json not found in repository
            FILE: N/A
            ```

            You are thorough, objective, and precise. Your validation reports are the
            foundation for accurate task completion tracking.""",
            verbose=True,
            allow_delegation=False,
            tools=[],  # Will be injected at runtime
            metadata={
                "specialization": "verification",
                "required_tools": ["EditorToolWrapper"],
                "validation_types": [
                    "file_exists",
                    "content_contains",
                    "structure_matches",
                    "functionality_complete",
                ],
            },
        )

    def create_verification_task(
        self, task_title: str, acceptance_criteria: list[str]
    ) -> str:
        """
        Create a task description for verification.

        Args:
            task_title: Title of the task to verify
            acceptance_criteria: List of acceptance criteria to validate

        Returns:
            Task description for the verifier
        """
        criteria_list = "\n".join(
            [f"{i+1}. {criterion}" for i, criterion in enumerate(acceptance_criteria)]
        )

        return f"""Verify acceptance criteria for task: {task_title}

        ACCEPTANCE CRITERIA TO VALIDATE:
        {criteria_list}

        VALIDATION INSTRUCTIONS:
        1. For EACH criterion above, use EditorTool GET operation to inspect relevant files
        2. Determine if the criterion is fully met (PASS), not met (FAIL), or partially met (PARTIAL)
        3. Provide specific evidence from files or explanation of gaps
        4. Include file paths and line numbers when referencing code

        CRITICAL:
        - Use EditorTool GET operation to read files before making judgments
        - Base your validation on ACTUAL file content, not assumptions
        - Be specific about what's missing or incorrect
        - Check ALL files mentioned in criteria

        OUTPUT FORMAT for each criterion:
        ```
        CRITERION: [exact text]
        STATUS: PASS | FAIL | PARTIAL
        EVIDENCE: [specific details]
        FILE: [path:line if applicable]
        ```

        After validating ALL criteria, provide a SUMMARY:
        ```
        VALIDATION SUMMARY:
        Total Criteria: [number]
        Passed: [number]
        Failed: [number]
        Partial: [number]
        Overall Status: [APPROVED | REJECTED | NEEDS_WORK]
        ```

        Begin verification now."""

    def test_agent(
        self, test_input: str, task_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Test the verifier agent with enhanced validation functionality.

        Args:
            test_input: Input to test the agent with
            task_id: Optional task ID to reference

        Returns:
            Dictionary containing test results
        """
        if not self._initialized:
            self.initialize()

        self.logger.info(f"Testing verifier agent with input: {test_input[:100]}...")

        try:
            # Create a simple test task
            from crewai import Task

            test_task = Task(
                description=test_input,
                agent=self.crewai_agent,
                expected_output="Detailed validation report with PASS/FAIL for each criterion",
            )

            # Execute the task
            result = test_task.execute_sync()

            return {
                "success": True,
                "agent_type": self.agent_type.value,
                "role": self.config.role,
                "input": test_input,
                "output": str(result),
                "error": None,
            }

        except Exception as e:
            self.logger.error(f"Error testing verifier agent: {e}")
            return {
                "success": False,
                "agent_type": self.agent_type.value,
                "role": self.config.role,
                "input": test_input,
                "output": None,
                "error": str(e),
            }


# Default configuration instance
verifier_config = VerifierAgent.create_default_config()
