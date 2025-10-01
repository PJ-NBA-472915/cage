"""
Agent Configuration Management

This module provides configuration management for agents, including loading
configurations from files and environment variables.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from .base import AgentConfig
from .committer import committer_config
from .implementer import implementer_config
from .planner import planner_config
from .reviewer import reviewer_config


class AgentConfigManager:
    """
    Manager for agent configurations.

    This class handles loading, saving, and managing agent configurations
    from various sources including files and environment variables.
    """

    def __init__(
        self, config_dir: Optional[Path] = None, logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the configuration manager.

        Args:
            config_dir: Directory containing configuration files
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.config_dir = config_dir or Path("config") / "agents"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Default configurations
        self._default_configs = {
            "planner": planner_config,
            "implementer": implementer_config,
            "reviewer": reviewer_config,
            "committer": committer_config,
        }

        self.logger.info(
            f"Agent configuration manager initialized with config dir: {self.config_dir}"
        )

    def get_default_config(self, agent_name: str) -> Optional[AgentConfig]:
        """
        Get the default configuration for an agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Default configuration or None if not found
        """
        return self._default_configs.get(agent_name.lower())

    def load_config_from_file(self, config_file: Path) -> Optional[dict[str, Any]]:
        """
        Load configuration from a JSON file.

        Args:
            config_file: Path to the configuration file

        Returns:
            Configuration dictionary or None if failed
        """
        try:
            with open(config_file) as f:
                config_data = json.load(f)

            self.logger.info(f"Loaded configuration from {config_file}")
            return config_data

        except Exception as e:
            self.logger.error(f"Error loading configuration from {config_file}: {e}")
            return None

    def save_config_to_file(self, config: AgentConfig, config_file: Path) -> bool:
        """
        Save configuration to a JSON file.

        Args:
            config: Agent configuration to save
            config_file: Path to save the configuration

        Returns:
            True if successful, False otherwise
        """
        try:
            config_data = {
                "role": config.role,
                "goal": config.goal,
                "backstory": config.backstory,
                "verbose": config.verbose,
                "allow_delegation": config.allow_delegation,
                "max_iter": config.max_iter,
                "max_execution_time": config.max_execution_time,
                "memory": config.memory,
                "max_rpm": config.max_rpm,
                "max_prompt_tokens": config.max_prompt_tokens,
                "max_completion_tokens": config.max_completion_tokens,
                "temperature": config.temperature,
                "top_p": config.top_p,
                "frequency_penalty": config.frequency_penalty,
                "presence_penalty": config.presence_penalty,
                "metadata": config.metadata,
            }

            # Ensure directory exists
            config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(config_file, "w") as f:
                json.dump(config_data, f, indent=2)

            self.logger.info(f"Saved configuration to {config_file}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving configuration to {config_file}: {e}")
            return False

    def load_config_from_env(self, agent_name: str) -> Optional[AgentConfig]:
        """
        Load configuration from environment variables.

        Args:
            agent_name: Name of the agent

        Returns:
            Agent configuration or None if not found
        """
        prefix = f"CAGE_AGENT_{agent_name.upper()}_"

        # Get configuration values from environment
        role = os.getenv(f"{prefix}ROLE")
        goal = os.getenv(f"{prefix}GOAL")
        backstory = os.getenv(f"{prefix}BACKSTORY")

        if not all([role, goal, backstory]):
            self.logger.warning(
                f"Incomplete environment configuration for agent {agent_name}"
            )
            return None

        # Parse boolean values
        verbose = os.getenv(f"{prefix}VERBOSE", "true").lower() == "true"
        allow_delegation = (
            os.getenv(f"{prefix}ALLOW_DELEGATION", "false").lower() == "true"
        )
        memory = os.getenv(f"{prefix}MEMORY", "false").lower() == "true"

        # Parse numeric values
        max_iter = os.getenv(f"{prefix}MAX_ITER")
        max_iter = int(max_iter) if max_iter else None

        max_execution_time = os.getenv(f"{prefix}MAX_EXECUTION_TIME")
        max_execution_time = int(max_execution_time) if max_execution_time else None

        max_rpm = os.getenv(f"{prefix}MAX_RPM")
        max_rpm = int(max_rpm) if max_rpm else None

        max_prompt_tokens = os.getenv(f"{prefix}MAX_PROMPT_TOKENS")
        max_prompt_tokens = int(max_prompt_tokens) if max_prompt_tokens else None

        max_completion_tokens = os.getenv(f"{prefix}MAX_COMPLETION_TOKENS")
        max_completion_tokens = (
            int(max_completion_tokens) if max_completion_tokens else None
        )

        temperature = os.getenv(f"{prefix}TEMPERATURE")
        temperature = float(temperature) if temperature else None

        top_p = os.getenv(f"{prefix}TOP_P")
        top_p = float(top_p) if top_p else None

        frequency_penalty = os.getenv(f"{prefix}FREQUENCY_PENALTY")
        frequency_penalty = float(frequency_penalty) if frequency_penalty else None

        presence_penalty = os.getenv(f"{prefix}PRESENCE_PENALTY")
        presence_penalty = float(presence_penalty) if presence_penalty else None

        # Parse metadata
        metadata_str = os.getenv(f"{prefix}METADATA", "{}")
        try:
            metadata = json.loads(metadata_str)
        except json.JSONDecodeError:
            metadata = {}

        config = AgentConfig(
            role=role,
            goal=goal,
            backstory=backstory,
            verbose=verbose,
            allow_delegation=allow_delegation,
            tools=[],  # Tools are injected at runtime
            max_iter=max_iter,
            max_execution_time=max_execution_time,
            memory=memory,
            max_rpm=max_rpm,
            max_prompt_tokens=max_prompt_tokens,
            max_completion_tokens=max_completion_tokens,
            temperature=temperature,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            metadata=metadata,
        )

        self.logger.info(f"Loaded configuration for {agent_name} from environment")
        return config

    def get_config(
        self, agent_name: str, source: str = "default"
    ) -> Optional[AgentConfig]:
        """
        Get configuration for an agent from the specified source.

        Args:
            agent_name: Name of the agent
            source: Source to load from ("default", "file", "env", "auto")

        Returns:
            Agent configuration or None if not found
        """
        if source == "default":
            return self.get_default_config(agent_name)

        elif source == "file":
            config_file = self.config_dir / f"{agent_name}.json"
            if config_file.exists():
                config_data = self.load_config_from_file(config_file)
                if config_data:
                    return AgentConfig(**config_data)
            return None

        elif source == "env":
            return self.load_config_from_env(agent_name)

        elif source == "auto":
            # Try environment first, then file, then default
            config = self.load_config_from_env(agent_name)
            if config:
                return config

            config_file = self.config_dir / f"{agent_name}.json"
            if config_file.exists():
                config_data = self.load_config_from_file(config_file)
                if config_data:
                    return AgentConfig(**config_data)

            return self.get_default_config(agent_name)

        else:
            self.logger.error(f"Unknown configuration source: {source}")
            return None

    def list_available_configs(self) -> list[str]:
        """
        List available configuration sources.

        Returns:
            List of available configuration names
        """
        configs = []

        # Add default configurations
        configs.extend(self._default_configs.keys())

        # Add file-based configurations
        for config_file in self.config_dir.glob("*.json"):
            configs.append(config_file.stem)

        return list(set(configs))

    def create_config_template(
        self, agent_name: str, config_file: Optional[Path] = None
    ) -> bool:
        """
        Create a configuration template file for an agent.

        Args:
            agent_name: Name of the agent
            config_file: Optional path for the template file

        Returns:
            True if successful, False otherwise
        """
        if not config_file:
            config_file = self.config_dir / f"{agent_name}.json.template"

        # Get default config or create a basic one
        config = self.get_default_config(agent_name)
        if not config:
            config = AgentConfig(
                role=f"{agent_name.title()} Agent",
                goal=f"Goal for {agent_name} agent",
                backstory=f"Backstory for {agent_name} agent",
            )

        return self.save_config_to_file(config, config_file)
