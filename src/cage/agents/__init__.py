"""
Cage AI Agents Module

This module provides a modular system for defining and managing CrewAI agents
with support for runtime crew construction and individual agent testing.
"""

from .base import BaseAgent, AgentConfig, AgentType
from .registry import AgentRegistry
from .factory import AgentFactory, CrewBuilder

__all__ = [
    'BaseAgent',
    'AgentConfig', 
    'AgentType',
    'AgentRegistry',
    'AgentFactory',
    'CrewBuilder'
]
