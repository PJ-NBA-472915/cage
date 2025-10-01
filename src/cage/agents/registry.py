"""
Agent Registry System

This module provides a registry system for discovering and managing available agents,
enabling dynamic crew construction and agent management.
"""

import logging
from typing import Any, Optional

from .base import AgentConfig, AgentType, BaseAgent


class AgentRegistry:
    """
    Registry for managing and discovering available agents.

    This class provides a centralized way to register, discover, and manage
    different types of agents in the system.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the agent registry.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self._agents: dict[str, type[BaseAgent]] = {}
        self._agent_configs: dict[str, AgentConfig] = {}
        self._agent_instances: dict[str, BaseAgent] = {}

        self.logger.info("Agent registry initialized")

    def register_agent(
        self,
        agent_class: type[BaseAgent],
        config: AgentConfig,
        name: Optional[str] = None,
    ) -> str:
        """
        Register an agent class with its configuration.

        Args:
            agent_class: The agent class to register
            config: Configuration for the agent
            name: Optional custom name for the agent (defaults to role)

        Returns:
            The registered agent name
        """
        agent_name = name or config.role.lower().replace(" ", "_")

        if agent_name in self._agents:
            self.logger.warning(f"Agent '{agent_name}' already registered, overwriting")

        self._agents[agent_name] = agent_class
        self._agent_configs[agent_name] = config

        self.logger.info(
            f"Registered agent '{agent_name}' of type {agent_class.__name__}"
        )

        return agent_name

    def get_agent_class(self, name: str) -> Optional[type[BaseAgent]]:
        """
        Get an agent class by name.

        Args:
            name: The agent name

        Returns:
            The agent class or None if not found
        """
        return self._agents.get(name)

    def get_agent_config(self, name: str) -> Optional[AgentConfig]:
        """
        Get an agent configuration by name.

        Args:
            name: The agent name

        Returns:
            The agent configuration or None if not found
        """
        return self._agent_configs.get(name)

    def create_agent(self, name: str, **kwargs) -> Optional[BaseAgent]:
        """
        Create an agent instance by name.

        Args:
            name: The agent name
            **kwargs: Additional configuration parameters

        Returns:
            The agent instance or None if not found
        """
        agent_class = self.get_agent_class(name)
        config = self.get_agent_config(name)

        if not agent_class or not config:
            self.logger.error(f"Agent '{name}' not found in registry")
            return None

        try:
            # Create agent instance
            agent_instance = agent_class(config, logger=self.logger, **kwargs)

            # Cache the instance
            self._agent_instances[name] = agent_instance

            self.logger.info(f"Created agent instance '{name}'")
            return agent_instance

        except Exception as e:
            self.logger.error(f"Error creating agent '{name}': {e}")
            return None

    def get_agent_instance(self, name: str) -> Optional[BaseAgent]:
        """
        Get an existing agent instance by name.

        Args:
            name: The agent name

        Returns:
            The agent instance or None if not found
        """
        return self._agent_instances.get(name)

    def list_agents(self) -> list[str]:
        """
        List all registered agent names.

        Returns:
            List of registered agent names
        """
        return list(self._agents.keys())

    def list_agents_by_type(self, agent_type: AgentType) -> list[str]:
        """
        List agents by type.

        Args:
            agent_type: The agent type to filter by

        Returns:
            List of agent names of the specified type
        """
        matching_agents = []

        for name, agent_class in self._agents.items():
            # Create a temporary instance to check the type
            config = self._agent_configs.get(name)
            if config:
                try:
                    temp_instance = agent_class(config, logger=self.logger)
                    if temp_instance._get_agent_type() == agent_type:
                        matching_agents.append(name)
                except Exception as e:
                    self.logger.warning(f"Error checking agent type for '{name}': {e}")

        return matching_agents

    def get_agent_info(self, name: str) -> Optional[dict[str, Any]]:
        """
        Get information about a registered agent.

        Args:
            name: The agent name

        Returns:
            Dictionary containing agent information or None if not found
        """
        agent_class = self.get_agent_class(name)
        config = self.get_agent_config(name)

        if not agent_class or not config:
            return None

        return {
            "name": name,
            "class": agent_class.__name__,
            "role": config.role,
            "goal": config.goal,
            "agent_type": agent_class(config, logger=self.logger)
            ._get_agent_type()
            .value,
            "tools_count": len(config.tools),
            "verbose": config.verbose,
            "allow_delegation": config.allow_delegation,
        }

    def list_all_agent_info(self) -> list[dict[str, Any]]:
        """
        Get information about all registered agents.

        Returns:
            List of dictionaries containing agent information
        """
        return [self.get_agent_info(name) for name in self.list_agents()]

    def unregister_agent(self, name: str) -> bool:
        """
        Unregister an agent.

        Args:
            name: The agent name to unregister

        Returns:
            True if successfully unregistered, False otherwise
        """
        if name not in self._agents:
            self.logger.warning(f"Agent '{name}' not found in registry")
            return False

        # Remove from all dictionaries
        del self._agents[name]
        del self._agent_configs[name]

        # Remove instance if it exists
        if name in self._agent_instances:
            del self._agent_instances[name]

        self.logger.info(f"Unregistered agent '{name}'")
        return True

    def clear_registry(self) -> None:
        """Clear all registered agents."""
        self._agents.clear()
        self._agent_configs.clear()
        self._agent_instances.clear()
        self.logger.info("Cleared agent registry")

    def load_agents_from_module(self, module_path: str) -> list[str]:
        """
        Load agents from a module path.

        Args:
            module_path: Path to the module containing agent definitions

        Returns:
            List of loaded agent names
        """
        loaded_agents = []

        try:
            # Import the module
            import importlib.util

            spec = importlib.util.spec_from_file_location("agent_module", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Look for agent classes and configurations
            for attr_name in dir(module):
                attr = getattr(module, attr_name)

                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseAgent)
                    and attr != BaseAgent
                ):
                    # Try to find a configuration for this agent
                    config_attr_name = f"{attr_name.lower()}_config"
                    if hasattr(module, config_attr_name):
                        config = getattr(module, config_attr_name)
                        if isinstance(config, AgentConfig):
                            name = self.register_agent(attr, config)
                            loaded_agents.append(name)
                            self.logger.info(f"Loaded agent '{name}' from module")

        except Exception as e:
            self.logger.error(f"Error loading agents from module '{module_path}': {e}")

        return loaded_agents

    def __len__(self) -> int:
        """Return the number of registered agents."""
        return len(self._agents)

    def __bool__(self) -> bool:
        """Return True if the registry exists (always True for instantiated registries)."""
        return True

    def __contains__(self, name: str) -> bool:
        """Check if an agent is registered."""
        return name in self._agents

    def __repr__(self) -> str:
        """String representation of the registry."""
        return f"AgentRegistry(agents={len(self._agents)})"
