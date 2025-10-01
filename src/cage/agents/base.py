"""
Base Agent Classes and Interfaces

This module defines the base classes and interfaces for all Cage AI agents,
providing a consistent structure for agent definition and testing.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from crewai import Agent
from crewai.tools import BaseTool


class AgentType(Enum):
    """Enumeration of available agent types."""

    PLANNER = "planner"
    IMPLEMENTER = "implementer"
    REVIEWER = "reviewer"
    COMMITTER = "committer"
    CUSTOM = "custom"


@dataclass
class AgentConfig:
    """Configuration for an agent instance."""

    role: str
    goal: str
    backstory: str
    verbose: bool = True
    allow_delegation: bool = False
    tools: list[BaseTool] = field(default_factory=list)
    max_iter: Optional[int] = None
    max_execution_time: Optional[int] = None
    memory: bool = False
    step_callback: Optional[callable] = None
    max_rpm: Optional[int] = None
    max_execution_time: Optional[int] = None
    max_prompt_tokens: Optional[int] = None
    max_completion_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Abstract base class for all Cage AI agents.

    This class provides a consistent interface for agent definition,
    configuration, and testing. All agents must inherit from this class.
    """

    def __init__(
        self, config: AgentConfig, logger: Optional[logging.Logger] = None, **kwargs
    ):
        """
        Initialize the agent with configuration.

        Args:
            config: Agent configuration
            logger: Optional logger instance
            **kwargs: Additional configuration parameters
        """
        self.config = config
        self.logger = logger or logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )
        self.agent_type = self._get_agent_type()
        self.crewai_agent: Optional[Agent] = None
        self._initialized = False

        # Store repo_path if provided
        self.repo_path = kwargs.get("repo_path")

        # Merge additional kwargs into config
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

    @abstractmethod
    def _get_agent_type(self) -> AgentType:
        """Return the agent type. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def _get_tools(self) -> list[BaseTool]:
        """
        Get the tools for this agent. Must be implemented by subclasses.

        Returns:
            List of CrewAI tools for this agent
        """
        pass

    def initialize(self) -> Agent:
        """
        Initialize the CrewAI agent instance.

        Returns:
            Initialized CrewAI Agent instance
        """
        if self._initialized and self.crewai_agent is not None:
            return self.crewai_agent

        self.logger.info(
            f"Initializing {self.agent_type.value} agent: {self.config.role}"
        )

        # Get tools from subclass implementation
        tools = self._get_tools()

        # Create CrewAI agent with only non-None parameters
        agent_kwargs = {
            "role": self.config.role,
            "goal": self.config.goal,
            "backstory": self.config.backstory,
            "verbose": self.config.verbose,
            "allow_delegation": self.config.allow_delegation,
            "tools": tools,
        }

        # Add optional parameters only if they are not None
        if self.config.max_iter is not None:
            agent_kwargs["max_iter"] = self.config.max_iter
        if self.config.max_execution_time is not None:
            agent_kwargs["max_execution_time"] = self.config.max_execution_time
        if self.config.memory is not None:
            agent_kwargs["memory"] = self.config.memory
        if self.config.step_callback is not None:
            agent_kwargs["step_callback"] = self.config.step_callback
        if self.config.max_rpm is not None:
            agent_kwargs["max_rpm"] = self.config.max_rpm
        if self.config.max_prompt_tokens is not None:
            agent_kwargs["max_prompt_tokens"] = self.config.max_prompt_tokens
        if self.config.max_completion_tokens is not None:
            agent_kwargs["max_completion_tokens"] = self.config.max_completion_tokens
        if self.config.temperature is not None:
            agent_kwargs["temperature"] = self.config.temperature
        if self.config.top_p is not None:
            agent_kwargs["top_p"] = self.config.top_p
        if self.config.frequency_penalty is not None:
            agent_kwargs["frequency_penalty"] = self.config.frequency_penalty
        if self.config.presence_penalty is not None:
            agent_kwargs["presence_penalty"] = self.config.presence_penalty

        self.crewai_agent = Agent(**agent_kwargs)

        self._initialized = True
        self.logger.info(f"Successfully initialized {self.agent_type.value} agent")

        return self.crewai_agent

    def get_agent(self) -> Agent:
        """
        Get the CrewAI agent instance, initializing if necessary.

        Returns:
            CrewAI Agent instance
        """
        if not self._initialized:
            return self.initialize()
        return self.crewai_agent

    def test_agent(
        self, test_input: str, task_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Test the agent with a given input.

        This method provides a way to test individual agents in isolation.

        Args:
            test_input: Input to test the agent with
            task_id: Optional task ID to reference in the plan

        Returns:
            Dictionary containing test results
        """
        if not self._initialized:
            self.initialize()

        self.logger.info(
            f"Testing {self.agent_type.value} agent with input: {test_input[:100]}..."
        )

        try:
            # Create a simple test task
            from crewai import Task

            test_task = Task(
                description=test_input,
                agent=self.crewai_agent,
                expected_output="Test response from agent",
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
            self.logger.error(f"Error testing {self.agent_type.value} agent: {e}")
            return {
                "success": False,
                "agent_type": self.agent_type.value,
                "role": self.config.role,
                "input": test_input,
                "output": None,
                "error": str(e),
            }

    def get_config(self) -> dict[str, Any]:
        """
        Get the agent configuration as a dictionary.

        Returns:
            Dictionary containing agent configuration
        """
        return {
            "agent_type": self.agent_type.value,
            "role": self.config.role,
            "goal": self.config.goal,
            "backstory": self.config.backstory,
            "verbose": self.config.verbose,
            "allow_delegation": self.config.allow_delegation,
            "tools_count": len(self.config.tools),
            "max_iter": self.config.max_iter,
            "max_execution_time": self.config.max_execution_time,
            "memory": self.config.memory,
            "metadata": self.config.metadata,
        }

    def update_config(self, **kwargs) -> None:
        """
        Update agent configuration.

        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                self.logger.info(f"Updated {key} to {value}")
            else:
                self.logger.warning(f"Unknown configuration parameter: {key}")

        # Reinitialize if agent was already created
        if self._initialized:
            self._initialized = False
            self.crewai_agent = None
            self.logger.info(
                "Agent configuration updated, will reinitialize on next use"
            )

    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"{self.__class__.__name__}(role='{self.config.role}', type='{self.agent_type.value}')"
