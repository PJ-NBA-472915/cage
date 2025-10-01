"""
Reviewer Agent Module

This module defines the Reviewer agent for reviewing changes and enforcing
quality standards and policy compliance.
"""


from .base import AgentConfig, AgentType, BaseAgent


class ReviewerAgent(BaseAgent):
    """
    Reviewer agent for reviewing changes and enforcing policies.

    This agent specializes in reviewing code changes for correctness, adherence
    to coding standards, security best practices, and policy compliance.
    """

    def _get_agent_type(self) -> AgentType:
        """Return the agent type."""
        return AgentType.REVIEWER

    def _get_tools(self) -> list:
        """
        Get the tools for the reviewer agent.

        The reviewer agent uses the EditorToolWrapper to read and verify files.
        This is injected at runtime when the agent is created.

        Returns:
            List of tools (injected at runtime)
        """
        return self.config.tools

    @classmethod
    def create_default_config(cls) -> AgentConfig:
        """
        Create a default configuration for the reviewer agent.

        Returns:
            Default agent configuration
        """
        return AgentConfig(
            role="Reviewer",
            goal="Review changes for quality, compliance, and proper tool usage",
            backstory="""You are an expert code reviewer and quality assurance specialist.
            You carefully review all changes for correctness, adherence to coding standards,
            security best practices, and policy compliance. You also verify that the
            Implementer used the EditorTool correctly for all file operations.

            CRITICAL RULES:
            1. Verify that EditorTool was used for all file operations
            2. Check that no terminal commands were used inappropriately
            3. Ensure file content is correct and complete
            4. Validate that file paths and extensions are appropriate
            5. Confirm that intent descriptions are meaningful
            6. Verify that all changes follow coding standards
            7. Check that task requirements are met

            You ensure that all changes meet the required quality standards before they are committed.""",
            verbose=True,
            allow_delegation=False,
            tools=[],  # Will be injected at runtime
            metadata={
                "specialization": "review",
                "required_tools": ["EditorToolWrapper"],
                "review_criteria": [
                    "tool_usage_verification",
                    "code_quality",
                    "security_compliance",
                    "policy_adherence",
                    "requirement_fulfillment",
                ],
                "verification_methods": [
                    "file_content_check",
                    "tool_usage_audit",
                    "quality_assessment",
                ],
            },
        )

    def create_review_task(self, task_title: str) -> str:
        """
        Create a task description for code review.

        Args:
            task_title: Title of the task to review

        Returns:
            Task description for the reviewer
        """
        return f"""Review the changes made for task: {task_title}

        CRITICAL REVIEW CHECKLIST:
        1. Verify that EditorTool was used for ALL file operations
        2. Check that no terminal commands were used inappropriately
        3. Ensure file content is correct and complete
        4. Validate that file paths and extensions are appropriate
        5. Confirm that intent descriptions are meaningful
        6. Verify that all changes follow coding standards
        7. Check that task requirements are met

        Use the EditorTool to read and verify the created/modified files."""

    def create_quality_checklist(self) -> list[str]:
        """
        Create a quality checklist for reviews.

        Returns:
            List of quality check items
        """
        return [
            "EditorTool was used for all file operations",
            "No inappropriate terminal commands were used",
            "File content is correct and complete",
            "File paths and extensions are appropriate",
            "Intent descriptions are meaningful",
            "Code follows established patterns",
            "Security best practices are followed",
            "Task requirements are fully met",
            "No syntax errors or obvious bugs",
            "Documentation is updated if needed",
        ]


# Default configuration instance
reviewer_config = ReviewerAgent.create_default_config()
