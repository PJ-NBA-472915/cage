"""
Planner Agent Module

This module defines the Planner agent for creating detailed execution plans
using Cage-native API endpoints.
"""

import logging
from typing import List, Optional

from .base import BaseAgent, AgentConfig, AgentType


class PlannerAgent(BaseAgent):
    """
    Planner agent for creating detailed execution plans.
    
    This agent specializes in analyzing tasks and creating comprehensive,
    step-by-step plans that break down complex work into manageable,
    executable steps using Cage-native API endpoints.
    """
    
    def _get_agent_type(self) -> AgentType:
        """Return the agent type."""
        return AgentType.PLANNER
    
    def _get_tools(self) -> List:
        """
        Get the tools for the planner agent.
        
        The planner agent doesn't use tools directly - it creates plans
        that other agents will execute.
        
        Returns:
            Empty list (planner doesn't use tools)
        """
        return []
    
    @classmethod
    def create_default_config(cls) -> AgentConfig:
        """
        Create a default configuration for the planner agent.
        
        Returns:
            Default agent configuration
        """
        return AgentConfig(
            role="Planner",
            goal="Create detailed, actionable plans for task execution using Cage-native API endpoints",
            backstory="""You are an expert software architect and project planner. 
            You analyze tasks and create comprehensive, step-by-step plans that break down 
            complex work into manageable, executable steps. You consider dependencies, 
            risks, and best practices in your planning.
            
            CRITICAL: All plans MUST use Cage-native API endpoints only:
            - Use POST /files/edit for all file operations (INSERT, UPDATE, DELETE)
            - Use GET /files/sha for content validation
            - Use GET /diff for change validation
            - Use POST /git/revert for rollback operations
            - Use POST /runner/exec for optional execution checks
            - Use POST /git/open_pr for pull request creation
            - Use POST /tasks/update for task updates
            
            NEVER include terminal commands like 'touch', 'mkdir', 'echo', etc.
            Always include validation steps and rollback paths.
            Include branch names and task-linked commit messages.
            
            Output format must be EXACTLY this JSON structure (no markdown, no code blocks):
            {
              "taskName": "Task Title",
              "taskId": "task-id",
              "goal": "Clear goal description",
              "branch": "chore/task-name-YYYY-MM-DD",
              "steps": [
                {
                  "name": "Step description",
                  "request": {
                    "method": "POST",
                    "path": "/files/edit",
                    "body": {
                      "operation": "INSERT",
                      "path": "file.py",
                      "payload": {"content": "file content"},
                      "intent": "Create file",
                      "author": "planner",
                      "correlation_id": "task-id"
                    }
                  },
                  "validate": [
                    "GET /files/sha?path=file.py -> returns non-empty sha",
                    "GET /diff?branch=chore/task-name-YYYY-MM-DD -> shows added file"
                  ],
                  "onFailure": {
                    "action": "abort",
                    "rollback": {
                      "method": "POST",
                      "path": "/git/revert",
                      "body": {"branch": "chore/task-name-YYYY-MM-DD", "to": "HEAD~1"}
                    }
                  }
                }
              ]
            }
            
            CRITICAL: Return ONLY the JSON object, no markdown formatting, no code blocks, no additional text.
            """,
            verbose=True,
            allow_delegation=False,
            tools=[],
            metadata={
                "specialization": "planning",
                "output_format": "json",
                "api_endpoints": [
                    "POST /files/edit",
                    "GET /files/sha", 
                    "GET /diff",
                    "POST /git/revert",
                    "POST /runner/exec",
                    "POST /git/open_pr",
                    "POST /tasks/update"
                ]
            }
        )
    
    def create_plan_task(self, task_title: str, task_summary: str, 
                        success_criteria: List[str], acceptance_checks: List[str]) -> str:
        """
        Create a task description for plan creation.
        
        Args:
            task_title: Title of the task to plan
            task_summary: Summary of the task
            success_criteria: List of success criteria
            acceptance_checks: List of acceptance checks
            
        Returns:
            Task description for the planner
        """
        return f"""Create a detailed execution plan for task: {task_title}
        
        Task Summary: {task_summary}
        Success Criteria: {success_criteria}
        Acceptance Checks: {acceptance_checks}
        
        Create a Cage-native execution plan that uses only API endpoints:
        - Use POST /files/edit for all file operations (INSERT, UPDATE, DELETE)
        - Use GET /files/sha for content validation
        - Use GET /diff for change validation
        - Use POST /git/revert for rollback operations
        - Use POST /runner/exec for optional execution checks
        - Use POST /git/open_pr for pull request creation
        - Use POST /tasks/update for task updates
        
        Include:
        1. Branch name following convention: chore/task-name-YYYY-MM-DD
        2. Task-linked commit messages with format: "type: description (links: task {task_title})"
        3. Validation steps for each operation
        4. Rollback paths for failure scenarios
        5. Idempotent operations that can be re-run safely
        
        Output must be valid JSON following the Cage-native plan schema."""


# Default configuration instance
planner_config = PlannerAgent.create_default_config()
