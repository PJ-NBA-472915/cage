"""
Base Agent Class for CrewAI Integration

Provides common functionality and interface for all agents in the crew.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from crewai import Agent
from loguru import logger


class BaseAgent(ABC):
    """Base class for all agents in the crew."""
    
    def __init__(self, name: str, role: str, goal: str, backstory: str):
        """
        Initialize the base agent.
        
        Args:
            name: Agent's name
            role: Agent's role in the crew
            goal: Agent's primary goal
            backstory: Agent's background story for context
        """
        self.name = name
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.crewai_agent: Optional[Agent] = None
        self.tools = []
        self.verbose = True
        self.allow_delegation = False
        
        logger.info(f"Initialized {self.name} agent with role: {self.role}")
    
    def create_crewai_agent(self) -> Agent:
        """
        Create the CrewAI Agent instance.
        
        Returns:
            Configured CrewAI Agent
        """
        self.crewai_agent = Agent(
            role=self.role,
            goal=self.goal,
            backstory=self.backstory,
            tools=self.tools,
            verbose=self.verbose,
            allow_delegation=self.allow_delegation
        )
        
        logger.info(f"Created CrewAI agent for {self.name}")
        return self.crewai_agent
    
    @abstractmethod
    def execute_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task with the given input.
        
        Args:
            task_input: Input parameters for the task
            
        Returns:
            Task execution results
        """
        pass
    
    def add_tool(self, tool):
        """Add a tool to the agent's toolkit."""
        self.tools.append(tool)
        logger.info(f"Added tool to {self.name}: {tool}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the agent."""
        return {
            "name": self.name,
            "role": self.role,
            "goal": self.goal,
            "tools_count": len(self.tools),
            "crewai_agent_created": self.crewai_agent is not None
        }
    
    def __str__(self):
        return f"{self.name} ({self.role})"
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(name='{self.name}', role='{self.role}')>"
