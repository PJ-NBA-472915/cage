#!/usr/bin/env python3
"""
Example Usage of CrewAI Agents

This script demonstrates how to use the crew of agents to execute tasks.
"""

import sys
import os
from loguru import logger

# Add the parent directory to the path so we can import the agents
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import CrewManager


def main():
    """Main function demonstrating crew usage."""
    logger.info("Starting CrewAI Agents Example")
    
    try:
        # Create the crew manager
        logger.info("Creating crew manager...")
        crew_manager = CrewManager()
        
        # Start monitoring
        logger.info("Starting continuous monitoring...")
        monitoring_result = crew_manager.start_monitoring()
        logger.info(f"Monitoring started: {monitoring_result}")
        
        # Get crew status
        crew_status = crew_manager.get_crew_status()
        logger.info(f"Crew status: {crew_status}")
        
        # Example 1: Execute a simple task
        logger.info("Executing simple task...")
        simple_task_result = crew_manager.execute_simple_task(
            description="Create a test file with hello world",
            cursor_command="echo 'Hello World from CrewAI!' > test_output.txt"
        )
        logger.info(f"Simple task result: {simple_task_result}")
        
        # Example 2: Execute a more complex task
        logger.info("Executing complex task...")
        complex_task = {
            "description": "Create a Python script that demonstrates the agents",
            "cursor_command": "cursor generate 'Create a Python script that shows how to use the CrewAI agents' --output demo_agents.py",
            "goals": [
                "Create a Python script",
                "Demonstrate agent usage",
                "Include proper documentation"
            ],
            "success_criteria": [
                {"text": "Script file is created"},
                {"text": "Script contains agent usage examples"},
                {"text": "Script has proper documentation"}
            ],
            "expected_outcomes": [
                "A working Python script file",
                "Clear examples of agent usage",
                "Well-documented code"
            ]
        }
        
        complex_task_result = crew_manager.execute_task(complex_task)
        logger.info(f"Complex task result: {complex_task_result}")
        
        # Get task history
        task_history = crew_manager.get_task_history()
        logger.info(f"Task history: {len(task_history)} tasks completed")
        
        # Get individual agent statuses
        for agent_type in ['actor', 'validator', 'checker']:
            agent_status = crew_manager.get_agent_status(agent_type)
            logger.info(f"{agent_type.capitalize()} agent status: {agent_status}")
        
        # Stop monitoring
        logger.info("Stopping monitoring...")
        stop_result = crew_manager.stop_monitoring()
        logger.info(f"Monitoring stopped: {stop_result}")
        
        logger.info("CrewAI Agents Example completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in CrewAI Agents Example: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
