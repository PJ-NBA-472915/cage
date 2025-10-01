"""
Committer Agent Module

This module defines the Committer agent for handling Git operations
and creating proper commits with meaningful messages.
"""


from .base import AgentConfig, AgentType, BaseAgent


class CommitterAgent(BaseAgent):
    """
    Committer agent for handling Git operations and commits.

    This agent specializes in version control operations including staging,
    committing, and pushing changes with clear, descriptive commit messages.
    """

    def _get_agent_type(self) -> AgentType:
        """Return the agent type."""
        return AgentType.COMMITTER

    def _get_tools(self) -> list:
        """
        Get the tools for the committer agent.

        The committer agent uses the GitToolWrapper for all Git operations.
        This is injected at runtime when the agent is created.

        Returns:
            List of tools (injected at runtime)
        """
        return self.config.tools

    @classmethod
    def create_default_config(cls) -> AgentConfig:
        """
        Create a default configuration for the committer agent.

        Returns:
            Default agent configuration
        """
        return AgentConfig(
            role="Committer",
            goal="Handle Git operations and create proper commits with meaningful messages",
            backstory="""You are an expert in version control and Git workflows. You handle
            all Git operations including staging, committing, and pushing changes. You create
            clear, descriptive commit messages that follow best practices and provide good
            audit trails.""",
            verbose=True,
            allow_delegation=False,
            tools=[],  # Will be injected at runtime
            metadata={
                "specialization": "version_control",
                "required_tools": ["GitToolWrapper"],
                "git_operations": ["add", "commit", "push", "status"],
                "commit_message_format": "type: description (links: task {task_id})",
                "best_practices": [
                    "meaningful_commit_messages",
                    "atomic_commits",
                    "proper_branch_naming",
                    "task_linked_commits",
                ],
            },
        )

    def create_commit_task(self, task_title: str) -> str:
        """
        Create a task description for committing changes.

        Args:
            task_title: Title of the task to commit

        Returns:
            Task description for the committer
        """
        return f"""Commit the changes for task: {task_title}

        Stage all changes and create a proper commit with a meaningful message.
        Check the working tree status first; if there are no changes, respond with a
        summary indicating nothing needed to be committed instead of forcing a commit.
        Update task provenance with commit information."""

    def create_commit_message(
        self, task_title: str, task_id: str, change_summary: str
    ) -> str:
        """
        Create a standardized commit message.

        Args:
            task_title: Title of the task
            task_id: ID of the task
            change_summary: Summary of changes made

        Returns:
            Formatted commit message
        """
        # Determine commit type based on task title
        task_lower = task_title.lower()
        if any(keyword in task_lower for keyword in ["fix", "bug", "error", "issue"]):
            commit_type = "fix"
        elif any(
            keyword in task_lower for keyword in ["feat", "feature", "add", "new"]
        ):
            commit_type = "feat"
        elif any(
            keyword in task_lower
            for keyword in ["refactor", "restructure", "reorganize"]
        ):
            commit_type = "refactor"
        elif any(keyword in task_lower for keyword in ["test", "testing"]):
            commit_type = "test"
        elif any(
            keyword in task_lower for keyword in ["doc", "documentation", "readme"]
        ):
            commit_type = "docs"
        else:
            commit_type = "chore"

        return f"{commit_type}: {change_summary} (links: task {task_id})"

    def get_git_workflow_steps(self) -> list[str]:
        """
        Get the standard Git workflow steps.

        Returns:
            List of Git workflow steps
        """
        return [
            "Check git status to see current state",
            "Add all changes to staging area",
            "Verify staged changes are correct",
            "Create commit with meaningful message",
            "Verify commit was created successfully",
            "Push changes to remote repository (if needed)",
        ]


# Default configuration instance
committer_config = CommitterAgent.create_default_config()
