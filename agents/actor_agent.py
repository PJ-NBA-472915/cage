"""
Actor Agent for Task Execution

This agent is responsible for executing tasks using the cursor CLI and making
changes to the repository based on task requirements.
"""

import subprocess
import json
from typing import Dict, Any, List
from .base_agent import BaseAgent
from loguru import logger


class CursorCLITool:
    """Tool for interacting with the cursor CLI."""
    
    def __init__(self):
        self.name = "cursor_cli"
        self.description = "Execute cursor CLI commands to make changes to the repository"
    
    def __call__(self, command: str, **kwargs) -> str:
        """
        Execute a cursor CLI command.
        
        Args:
            command: The cursor CLI command to execute
            
        Returns:
            Command output as string
        """
        try:
            logger.info(f"Executing cursor CLI command: {command}")
            
            # Execute the command using subprocess
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd="/app"  # Working directory in container
            )
            
            if result.returncode == 0:
                logger.info(f"Cursor CLI command successful: {command}")
                return result.stdout
            else:
                error_msg = f"Cursor CLI command failed: {result.stderr}"
                logger.error(error_msg)
                return f"ERROR: {error_msg}"
                
        except Exception as e:
            error_msg = f"Exception executing cursor CLI command: {str(e)}"
            logger.error(error_msg)
            return f"ERROR: {error_msg}"


class ActorAgent(BaseAgent):
    """Agent responsible for executing tasks using the cursor CLI."""
    
    def __init__(self):
        super().__init__(
            name="TaskExecutor",
            role="Task Execution Specialist",
            goal="Execute tasks efficiently using the cursor CLI to make repository changes",
            backstory="""You are an expert task executor with deep knowledge of software development 
            and repository management. You use the cursor CLI to implement changes, refactor code, 
            and complete development tasks. You always follow best practices and ensure code quality."""
        )
        
        # Add the cursor CLI tool
        self.cursor_tool = CursorCLITool()
        self.add_tool(self.cursor_tool)
        
        # Set specific properties for this agent
        self.allow_delegation = True  # Can delegate to other agents if needed
        
        logger.info("Actor Agent initialized with cursor CLI tool")
    
    def execute_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task using the cursor CLI.
        
        Args:
            task_input: Task definition with command and parameters
            
        Returns:
            Task execution results
        """
        try:
            logger.info(f"Actor Agent executing task: {task_input}")
            
            # Extract task details
            task_description = task_input.get('description', '')
            cursor_command = task_input.get('cursor_command', '')
            expected_outcome = task_input.get('expected_outcome', '')
            
            if not cursor_command:
                return {
                    "success": False,
                    "error": "No cursor command provided in task input",
                    "task_input": task_input
                }
            
            # Execute the cursor command
            result = self.cursor_tool(cursor_command)
            
            # Check if execution was successful
            success = not result.startswith("ERROR:")
            
            execution_result = {
                "success": success,
                "task_description": task_description,
                "cursor_command": cursor_command,
                "expected_outcome": expected_outcome,
                "execution_output": result,
                "timestamp": self._get_timestamp()
            }
            
            if success:
                logger.info(f"Task executed successfully: {task_description}")
            else:
                logger.error(f"Task execution failed: {task_description}")
            
            return execution_result
            
        except Exception as e:
            error_msg = f"Exception during task execution: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "task_input": task_input
            }
    
    def get_available_commands(self) -> List[str]:
        """Get list of available cursor CLI commands."""
        return [
            "cursor --help",
            "cursor edit <file>",
            "cursor chat <prompt>",
            "cursor generate <description>",
            "cursor refactor <file>",
            "cursor test <file>"
        ]
    
    def validate_command(self, command: str) -> bool:
        """Validate if a cursor command is safe to execute."""
        # Basic safety checks
        dangerous_patterns = [
            "rm -rf",
            "sudo",
            "chmod 777",
            "curl | bash",
            "wget | bash"
        ]
        
        for pattern in dangerous_patterns:
            if pattern in command.lower():
                logger.warning(f"Potentially dangerous command detected: {command}")
                return False
        
        return True
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for logging."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed status of the actor agent."""
        base_status = super().get_status()
        base_status.update({
            "available_commands": self.get_available_commands(),
            "cursor_tool_available": hasattr(self, 'cursor_tool'),
            "allow_delegation": self.allow_delegation
        })
        return base_status
