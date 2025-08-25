"""
Crew Manager for Agent Coordination

This module manages the crew of agents (validator, actor, checker) and coordinates
their work on tasks. It handles the complete task lifecycle from execution to validation.
"""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from crewai import Crew, Task
from loguru import logger

from .actor_agent import ActorAgent
from .validator_agent import ValidatorAgent
from .checker_agent import CheckerAgent


class CrewManager:
    """Manages the crew of agents and coordinates task execution."""
    
    def __init__(self):
        """Initialize the crew manager with all agents."""
        self.crew_id = str(uuid.uuid4())
        self.agents = {}
        self.active_tasks = {}
        self.task_history = []
        
        # Initialize agents
        self._initialize_agents()
        
        # Create CrewAI crew
        self.crew = None
        self._create_crew()
        
        logger.info(f"Crew Manager initialized with ID: {self.crew_id}")
    
    def _initialize_agents(self):
        """Initialize all agents in the crew."""
        try:
            # Create actor agent
            self.agents['actor'] = ActorAgent()
            
            # Create validator agent
            self.agents['validator'] = ValidatorAgent()
            
            # Create checker agent
            self.agents['checker'] = CheckerAgent(check_interval_minutes=10)
            
            logger.info("All agents initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize agents: {str(e)}")
            raise
    
    def _create_crew(self):
        """Create the CrewAI crew with all agents."""
        try:
            # Create CrewAI agents
            crewai_agents = []
            for agent_type, agent in self.agents.items():
                crewai_agent = agent.create_crewai_agent()
                crewai_agents.append(crewai_agent)
            
            # Create the crew
            self.crew = Crew(
                agents=crewai_agents,
                verbose=True,
                memory=True
            )
            
            logger.info("CrewAI crew created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create CrewAI crew: {str(e)}")
            raise
    
    def execute_task(self, task_definition: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a complete task using the crew.
        
        Args:
            task_definition: Complete task definition with goals, criteria, etc.
            
        Returns:
:           Task execution results
        """
        try:
            task_id = str(uuid.uuid4())
            logger.info(f"Starting task execution: {task_id}")
            
            # Start monitoring the task
            self.agents['checker'].progress_tool.update_progress(
                task_id, 
                {"status": "started", "action": "Task execution initiated"}
            )
            
            # Create task for actor agent
            actor_task = Task(
                description=task_definition.get('description', ''),
                agent=self.agents['actor'].crewai_agent,
                expected_output="Task execution results and any changes made"
            )
            
            # Execute the task
            execution_result = self.crew.kickoff()
            
            # Update progress
            self.agents['checker'].progress_tool.update_progress(
                task_id, 
                {"status": "executed", "action": "Task execution completed"}
            )
            
            # Validate the results
            validation_input = {
                'task_id': task_id,
                'task_definition': task_definition,
                'execution_result': execution_result
            }
            
            validation_result = self.agents['validator'].execute_task(validation_input)
            
            # Update progress
            self.agents['checker'].progress_tool.update_progress(
                task_id, 
                {"status": "validated", "action": "Task validation completed"}
            )
            
            # Compile final results
            final_result = {
                "task_id": task_id,
                "task_definition": task_definition,
                "execution_result": execution_result,
                "validation_result": validation_result,
                "crew_id": self.crew_id,
                "execution_timestamp": datetime.now().isoformat(),
                "overall_success": validation_result.get('validation_passed', False)
            }
            
            # Store in history
            self.task_history.append(final_result)
            
            # Stop monitoring this task
            self.agents['checker'].progress_tool("stop_monitoring", task_id=task_id)
            
            logger.info(f"Task {task_id} completed successfully")
            return final_result
            
        except Exception as e:
            error_msg = f"Exception during task execution: {str(e)}"
            logger.error(error_msg)
            
            # Update progress with error
            if 'task_id' in locals():
                self.agents['checker'].progress_tool.update_progress(
                    task_id, 
                    {"status": "failed", "action": f"Task execution failed: {error_msg}"}
                )
            
            return {
                "success": False,
                "error": error_msg,
                "task_definition": task_definition
            }
    
    def start_monitoring(self) -> Dict[str, Any]:
        """Start the continuous monitoring process."""
        try:
            result = self.agents['checker'].start_monitoring()
            if result['success']:
                logger.info("Crew monitoring started successfully")
            return result
        except Exception as e:
            error_msg = f"Failed to start crew monitoring: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def stop_monitoring(self) -> Dict[str, Any]:
        """Stop the continuous monitoring process."""
        try:
            result = self.agents['checker'].stop_monitoring()
            if result['success']:
                logger.info("Crew monitoring stopped successfully")
            return result
        except Exception as e:
            error_msg = f"Failed to stop crew monitoring: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def get_crew_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the entire crew."""
        try:
            crew_status = {
                "crew_id": self.crew_id,
                "crew_created": self.crew is not None,
                "agents": {},
                "active_tasks_count": len(self.active_tasks),
                "completed_tasks_count": len(self.task_history),
                "monitoring_active": self.agents['checker'].monitoring_active
            }
            
            # Get status for each agent
            for agent_type, agent in self.agents.items():
                crew_status['agents'][agent_type] = agent.get_status()
            
            return crew_status
            
        except Exception as e:
            error_msg = f"Failed to get crew status: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def get_task_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent task history."""
        try:
            # Return most recent tasks
            recent_tasks = self.task_history[-limit:] if self.task_history else []
            
            # Add summary information
            for task in recent_tasks:
                task['summary'] = {
                    'execution_success': task.get('execution_result', {}).get('success', False),
                    'validation_passed': task.get('validation_result', {}).get('validation_passed', False),
                    'overall_success': task.get('overall_success', False)
                }
            
            return recent_tasks
            
        except Exception as e:
            error_msg = f"Failed to get task history: {str(e)}"
            logger.error(error_msg)
            return []
    
    def get_agent_status(self, agent_type: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific agent."""
        try:
            if agent_type in self.agents:
                return self.agents[agent_type].get_status()
            else:
                logger.warning(f"Unknown agent type: {agent_type}")
                return None
        except Exception as e:
            error_msg = f"Failed to get agent status for {agent_type}: {str(e)}"
            logger.error(error_msg)
            return None
    
    def execute_simple_task(self, description: str, cursor_command: str) -> Dict[str, Any]:
        """
        Execute a simple task with just description and cursor command.
        
        Args:
            description: Task description
            cursor_command: Cursor CLI command to execute
            
        Returns:
            Task execution results
        """
        task_definition = {
            "description": description,
            "cursor_command": cursor_command,
            "goals": [description],
            "success_criteria": [{"text": "Task executed successfully"}],
            "expected_outcomes": [description]
        }
        
        return self.execute_task(task_definition)
    
    def __str__(self):
        return f"CrewManager({self.crew_id})"
    
    def __repr__(self):
        return f"<CrewManager(crew_id='{self.crew_id}', agents={list(self.agents.keys())})>"
