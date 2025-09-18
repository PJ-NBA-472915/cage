"""
Agent Factory and Crew Builder

This module provides factory classes for creating agents and building crews
dynamically at runtime.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from crewai import Agent, Crew, Process, Task
from crewai.tools import BaseTool

from .base import BaseAgent, AgentConfig, AgentType
from .registry import AgentRegistry


class AgentFactory:
    """
    Factory for creating agent instances with different configurations.
    
    This class provides methods to create agents with various configurations
    and supports both predefined and custom agent types.
    """
    
    def __init__(self, registry: Optional[AgentRegistry] = None, logger: Optional[logging.Logger] = None):
        """
        Initialize the agent factory.
        
        Args:
            registry: Optional agent registry instance
            logger: Optional logger instance
        """
        self.registry = registry or AgentRegistry(logger)
        self.logger = logger or logging.getLogger(__name__)
        
        self.logger.info("Agent factory initialized")
    
    def create_agent(
        self,
        name: str,
        config: Optional[AgentConfig] = None,
        **kwargs
    ) -> Optional[BaseAgent]:
        """
        Create an agent by name with optional custom configuration.
        
        Args:
            name: The agent name (must be registered)
            config: Optional custom configuration
            **kwargs: Additional configuration parameters
            
        Returns:
            The created agent instance or None if not found
        """
        if name not in self.registry:
            self.logger.error(f"Agent '{name}' not found in registry")
            return None
        
        # Use custom config if provided, otherwise use registered config
        if config:
            agent_class = self.registry.get_agent_class(name)
            if agent_class:
                return agent_class(config, logger=self.logger, **kwargs)
        else:
            return self.registry.create_agent(name, **kwargs)
    
    def create_agent_with_config_override(
        self,
        name: str,
        config_overrides: Dict[str, Any],
        **kwargs
    ) -> Optional[BaseAgent]:
        """
        Create an agent with configuration overrides.
        
        Args:
            name: The agent name (must be registered)
            config_overrides: Configuration parameters to override
            **kwargs: Additional configuration parameters
            
        Returns:
            The created agent instance or None if not found
        """
        base_config = self.registry.get_agent_config(name)
        if not base_config:
            self.logger.error(f"Agent '{name}' not found in registry")
            return None
        
        # Create a new config with overrides
        config_dict = {
            "role": base_config.role,
            "goal": base_config.goal,
            "backstory": base_config.backstory,
            "verbose": base_config.verbose,
            "allow_delegation": base_config.allow_delegation,
            "tools": base_config.tools,
            "max_iter": base_config.max_iter,
            "max_execution_time": base_config.max_execution_time,
            "memory": base_config.memory,
            "step_callback": base_config.step_callback,
            "max_rpm": base_config.max_rpm,
            "max_prompt_tokens": base_config.max_prompt_tokens,
            "max_completion_tokens": base_config.max_completion_tokens,
            "temperature": base_config.temperature,
            "top_p": base_config.top_p,
            "frequency_penalty": base_config.frequency_penalty,
            "presence_penalty": base_config.presence_penalty,
            "metadata": base_config.metadata.copy()
        }
        
        # Apply overrides
        config_dict.update(config_overrides)
        
        # Create new config
        custom_config = AgentConfig(**config_dict)
        
        return self.create_agent(name, custom_config, **kwargs)
    
    def create_agents_by_type(
        self,
        agent_type: AgentType,
        count: int = 1,
        **kwargs
    ) -> List[BaseAgent]:
        """
        Create multiple agents of a specific type.
        
        Args:
            agent_type: The type of agents to create
            count: Number of agents to create
            **kwargs: Additional configuration parameters
            
        Returns:
            List of created agent instances
        """
        agent_names = self.registry.list_agents_by_type(agent_type)
        
        if not agent_names:
            self.logger.warning(f"No agents of type '{agent_type.value}' found")
            return []
        
        agents = []
        for i in range(min(count, len(agent_names))):
            agent_name = agent_names[i % len(agent_names)]
            agent = self.create_agent(agent_name, **kwargs)
            if agent:
                agents.append(agent)
        
        return agents
    
    def create_agent_from_config(
        self,
        agent_class: type,
        config: AgentConfig,
        **kwargs
    ) -> BaseAgent:
        """
        Create an agent directly from a class and configuration.
        
        Args:
            agent_class: The agent class
            config: The agent configuration
            **kwargs: Additional configuration parameters
            
        Returns:
            The created agent instance
        """
        return agent_class(config, logger=self.logger, **kwargs)


class CrewBuilder:
    """
    Builder for creating CrewAI crews dynamically.
    
    This class provides a fluent interface for building crews with different
    agent combinations and configurations.
    """
    
    def __init__(self, factory: Optional[AgentFactory] = None, logger: Optional[logging.Logger] = None):
        """
        Initialize the crew builder.
        
        Args:
            factory: Optional agent factory instance
            logger: Optional logger instance
        """
        self.factory = factory or AgentFactory(logger)
        self.logger = logger or logging.getLogger(__name__)
        self._agents: List[BaseAgent] = []
        self._tasks: List[Task] = []
        self._process: Process = Process.sequential
        self._verbose: bool = True
        self._memory: bool = False
        self._planning: bool = False
        self._max_rpm: Optional[int] = None
        self._max_execution_time: Optional[int] = None
        self._step_callback: Optional[callable] = None
        
        self.logger.info("Crew builder initialized")
    
    def add_agent(self, agent: Union[str, BaseAgent]) -> 'CrewBuilder':
        """
        Add an agent to the crew.
        
        Args:
            agent: Agent name (string) or agent instance
            
        Returns:
            Self for method chaining
        """
        if isinstance(agent, str):
            agent_instance = self.factory.create_agent(agent)
            if not agent_instance:
                self.logger.error(f"Failed to create agent '{agent}'")
                return self
            agent = agent_instance
        
        self._agents.append(agent)
        self.logger.info(f"Added agent '{agent.config.role}' to crew")
        return self
    
    def add_agents(self, agents: List[Union[str, BaseAgent]]) -> 'CrewBuilder':
        """
        Add multiple agents to the crew.
        
        Args:
            agents: List of agent names or agent instances
            
        Returns:
            Self for method chaining
        """
        for agent in agents:
            self.add_agent(agent)
        return self
    
    def add_agents_by_type(self, agent_type: AgentType, count: int = 1) -> 'CrewBuilder':
        """
        Add agents by type to the crew.
        
        Args:
            agent_type: The type of agents to add
            count: Number of agents to add
            
        Returns:
            Self for method chaining
        """
        agents = self.factory.create_agents_by_type(agent_type, count)
        self._agents.extend(agents)
        return self
    
    def add_task(self, task: Task) -> 'CrewBuilder':
        """
        Add a task to the crew.
        
        Args:
            task: The task to add
            
        Returns:
            Self for method chaining
        """
        self._tasks.append(task)
        self.logger.info(f"Added task '{task.description[:50]}...' to crew")
        return self
    
    def add_tasks(self, tasks: List[Task]) -> 'CrewBuilder':
        """
        Add multiple tasks to the crew.
        
        Args:
            tasks: List of tasks to add
            
        Returns:
            Self for method chaining
        """
        for task in tasks:
            self.add_task(task)
        return self
    
    def set_process(self, process: Process) -> 'CrewBuilder':
        """
        Set the crew process type.
        
        Args:
            process: The process type (sequential, hierarchical, etc.)
            
        Returns:
            Self for method chaining
        """
        self._process = process
        return self
    
    def set_verbose(self, verbose: bool) -> 'CrewBuilder':
        """
        Set verbose mode for the crew.
        
        Args:
            verbose: Whether to enable verbose mode
            
        Returns:
            Self for method chaining
        """
        self._verbose = verbose
        return self
    
    def set_memory(self, memory: bool) -> 'CrewBuilder':
        """
        Set memory mode for the crew.
        
        Args:
            memory: Whether to enable memory
            
        Returns:
            Self for method chaining
        """
        self._memory = memory
        return self
    
    def set_planning(self, planning: bool) -> 'CrewBuilder':
        """
        Set planning mode for the crew.
        
        Args:
            planning: Whether to enable planning
            
        Returns:
            Self for method chaining
        """
        self._planning = planning
        return self
    
    def set_max_rpm(self, max_rpm: int) -> 'CrewBuilder':
        """
        Set maximum requests per minute for the crew.
        
        Args:
            max_rpm: Maximum requests per minute
            
        Returns:
            Self for method chaining
        """
        self._max_rpm = max_rpm
        return self
    
    def set_max_execution_time(self, max_execution_time: int) -> 'CrewBuilder':
        """
        Set maximum execution time for the crew.
        
        Args:
            max_execution_time: Maximum execution time in seconds
            
        Returns:
            Self for method chaining
        """
        self._max_execution_time = max_execution_time
        return self
    
    def set_step_callback(self, step_callback: callable) -> 'CrewBuilder':
        """
        Set step callback for the crew.
        
        Args:
            step_callback: Callback function for each step
            
        Returns:
            Self for method chaining
        """
        self._step_callback = step_callback
        return self
    
    def build(self) -> Crew:
        """
        Build the crew with the configured agents and settings.
        
        Returns:
            The built CrewAI crew
        """
        if not self._agents:
            raise ValueError("No agents added to crew")
        
        if not self._tasks:
            raise ValueError("No tasks added to crew")
        
        # Get CrewAI agents
        crewai_agents = [agent.get_agent() for agent in self._agents]
        
        # Build crew
        crew = Crew(
            agents=crewai_agents,
            tasks=self._tasks,
            process=self._process,
            verbose=self._verbose,
            memory=self._memory,
            planning=self._planning,
            max_rpm=self._max_rpm,
            max_execution_time=self._max_execution_time,
            step_callback=self._step_callback
        )
        
        self.logger.info(f"Built crew with {len(self._agents)} agents and {len(self._tasks)} tasks")
        
        return crew
    
    def reset(self) -> 'CrewBuilder':
        """
        Reset the builder to initial state.
        
        Returns:
            Self for method chaining
        """
        self._agents.clear()
        self._tasks.clear()
        self._process = Process.sequential
        self._verbose = True
        self._memory = False
        self._planning = False
        self._max_rpm = None
        self._max_execution_time = None
        self._step_callback = None
        
        self.logger.info("Crew builder reset")
        return self
    
    def get_agent_info(self) -> List[Dict[str, Any]]:
        """
        Get information about the agents in the current crew.
        
        Returns:
            List of agent information dictionaries
        """
        return [agent.get_config() for agent in self._agents]
    
    def __len__(self) -> int:
        """Return the number of agents in the crew."""
        return len(self._agents)
    
    def __repr__(self) -> str:
        """String representation of the crew builder."""
        return f"CrewBuilder(agents={len(self._agents)}, tasks={len(self._tasks)})"
