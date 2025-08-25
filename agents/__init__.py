"""
CrewAI Agents Module for Cage Repository

This module provides a crew of agents that can work together to execute tasks:
- Validator Agent: Verifies task completion against original goals
- Actor Agent: Executes tasks using the cursor CLI
- Checker Agent: Monitors progress and can terminate stalled tasks
"""

from .base_agent import BaseAgent
from .validator_agent import ValidatorAgent
from .actor_agent import ActorAgent
from .checker_agent import CheckerAgent
from .crew_manager import CrewManager

__all__ = [
    'BaseAgent',
    'ValidatorAgent', 
    'ActorAgent',
    'CheckerAgent',
    'CrewManager'
]
