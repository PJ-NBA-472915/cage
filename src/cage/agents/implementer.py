"""
Implementer Agent Module

This module defines the Implementer agent for executing file operations
and implementing code changes using the Cage Editor Tool.
"""

import logging
from typing import List, Optional

from .base import BaseAgent, AgentConfig, AgentType


class ImplementerAgent(BaseAgent):
    """
    Implementer agent for executing file operations and code changes.
    
    This agent specializes in implementing code changes using the Cage Editor Tool,
    ensuring all file operations follow the proper patterns and best practices.
    """
    
    def _get_agent_type(self) -> AgentType:
        """Return the agent type."""
        return AgentType.IMPLEMENTER
    
    def _get_tools(self) -> List:
        """
        Get the tools for the implementer agent.
        
        The implementer agent uses the EditorToolWrapper for all file operations.
        This is injected at runtime when the agent is created.
        
        Returns:
            List of tools (injected at runtime)
        """
        return self.config.tools
    
    @classmethod
    def create_default_config(cls) -> AgentConfig:
        """
        Create a default configuration for the implementer agent.
        
        Returns:
            Default agent configuration
        """
        return AgentConfig(
            role="Implementer",
            goal="Execute file operations and implement code changes using the Cage Editor Tool",
            backstory="""You are an expert software developer with deep knowledge of 
            code structure, best practices, and implementation patterns. You MUST use the 
            EditorTool for ALL file operations - creating, reading, updating, and deleting files.
            
            CRITICAL RULES:
            1. NEVER use terminal commands like 'touch', 'mkdir', 'echo', 'cat', etc.
            2. ALWAYS use the EditorTool for file operations
            3. If a file you need to modify does not exist, create it with INSERT (include full content)
            4. For creating new files, use INSERT operation with full content
            5. For directories, create files with paths like 'subdir/file.txt'
            6. Always provide meaningful intent descriptions
            7. Use proper file extensions (.py, .md, .txt, etc.)
            
            You carefully execute file operations, making precise changes while maintaining 
            code quality and following established patterns.""",
            verbose=True,
            allow_delegation=False,
            tools=[],  # Will be injected at runtime
            metadata={
                "specialization": "implementation",
                "required_tools": ["EditorToolWrapper"],
                "file_operations": ["INSERT", "GET", "UPDATE", "DELETE"],
                "forbidden_commands": ["touch", "mkdir", "echo", "cat", "rm", "mv", "cp"]
            }
        )
    
    def create_implementation_task(self, task_title: str, plan_content: str) -> str:
        """
        Create a task description for implementation.
        
        Args:
            task_title: Title of the task to implement
            plan_content: The plan content to execute
            
        Returns:
            Task description for the implementer
        """
        return f"""Execute the implementation plan for task: {task_title}
        
        Plan: {plan_content}
        
        CRITICAL INSTRUCTIONS:
        1. Use ONLY the EditorTool for all file operations
        2. Do NOT use terminal commands like 'touch', 'mkdir', 'echo', etc.
        3. For creating files, use INSERT operation with full content
        4. For reading files, use GET operation
        5. For updating files, use UPDATE operation
        6. For deleting files, use DELETE operation
        7. Always provide meaningful intent descriptions
        8. Use proper file extensions (.py, .md, .txt, etc.)
        
        Be precise and follow the plan exactly using the EditorTool."""


# Default configuration instance
implementer_config = ImplementerAgent.create_default_config()
