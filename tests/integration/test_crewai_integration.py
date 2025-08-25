"""
Integration tests for CrewAI Agents Module

Tests the interaction between different agents and the complete workflow.
"""

import pytest
import sys
import os
import tempfile
import shutil
from unittest.mock import patch, Mock

# Add the parent directory to the path so we can import the agents
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import CrewManager, ActorAgent, ValidatorAgent, CheckerAgent


class TestCrewAIIntegration:
    """Test integration between different agents."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create a simple test file
        with open("test_file.txt", "w") as f:
            f.write("Initial content")
    
    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
    
    @patch('agents.crew_manager.Crew')
    @patch('agents.actor_agent.subprocess.run')
    def test_actor_validator_integration(self, mock_subprocess, mock_crew):
        """Test integration between actor and validator agents."""
        # Mock subprocess to simulate cursor CLI execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "File created successfully with new content"
        mock_subprocess.return_value = mock_result
        
        # Mock CrewAI crew execution
        mock_crew_instance = Mock()
        mock_crew_instance.kickoff.return_value = {
            "success": True,
            "output": "File created successfully with new content"
        }
        mock_crew.return_value = mock_crew_instance
        
        # Create crew manager
        crew_manager = CrewManager()
        
        # Define a task that should pass validation
        task = {
            "description": "Create a test file with specific content",
            "cursor_command": "echo 'New content' > new_file.txt",
            "goals": [
                "Create a new file",
                "Add specific content"
            ],
            "success_criteria": [
                {"text": "File is created"},
                {"text": "Content is added"}
            ],
            "expected_outcomes": [
                "New file exists",
                "File contains expected content"
            ]
        }
        
        # Execute the task
        result = crew_manager.execute_task(task)
        
        # Verify the result structure
        assert "task_id" in result
        assert "execution_result" in result
        assert "validation_result" in result
        assert "overall_success" in result
        
        # Verify validation passed (since our mock output matches goals)
        validation_result = result["validation_result"]
        assert validation_result["validation_passed"] is True
        assert validation_result["validation_score"] > 0.8
    
    @patch('agents.crew_manager.Crew')
    @patch('agents.actor_agent.subprocess.run')
    def test_actor_validator_integration_failure(self, mock_subprocess, mock_crew):
        """Test integration when actor fails and validator catches it."""
        # Mock subprocess to simulate cursor CLI failure
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Permission denied"
        mock_subprocess.return_value = mock_result
        
        # Mock CrewAI crew execution
        mock_crew_instance = Mock()
        mock_crew_instance.kickoff.return_value = {
            "success": False,
            "error": "Permission denied"
        }
        mock_crew.return_value = mock_crew_instance
        
        # Create crew manager
        crew_manager = CrewManager()
        
        # Define a task that should fail
        task = {
            "description": "Create a protected file",
            "cursor_command": "echo 'content' > /protected/file.txt",
            "goals": ["Create a protected file"],
            "success_criteria": [{"text": "File is created"}],
            "expected_outcomes": ["Protected file exists"]
        }
        
        # Execute the task
        result = crew_manager.execute_task(task)
        
        # Verify the result structure
        assert "task_id" in result
        assert "execution_result" in result
        assert "validation_result" in result
        
        # Verify validation failed
        validation_result = result["validation_result"]
        assert validation_result["validation_passed"] is False
        assert validation_result["validation_score"] == 0.0
    
    @patch('agents.crew_manager.Crew')
    def test_checker_monitoring_integration(self, mock_crew):
        """Test integration of checker agent with monitoring."""
        # Mock CrewAI crew
        mock_crew_instance = Mock()
        mock_crew.return_value = mock_crew_instance
        
        # Create crew manager
        crew_manager = CrewManager()
        
        # Start monitoring
        monitoring_result = crew_manager.start_monitoring()
        assert monitoring_result["success"] is True
        
        # Get crew status to verify monitoring is active
        crew_status = crew_manager.get_crew_status()
        assert crew_status["monitoring_active"] is True
        
        # Stop monitoring
        stop_result = crew_manager.stop_monitoring()
        assert stop_result["success"] is True
        
        # Verify monitoring is stopped
        crew_status = crew_manager.get_crew_status()
        assert crew_status["monitoring_active"] is False
    
    def test_agent_tool_integration(self):
        """Test that agents have the correct tools integrated."""
        # Test Actor Agent tools
        actor = ActorAgent()
        assert len(actor.tools) == 1
        assert hasattr(actor, 'cursor_tool')
        assert actor.cursor_tool.name == "cursor_cli"
        
        # Test Validator Agent tools
        validator = ValidatorAgent()
        assert len(validator.tools) == 1
        assert hasattr(validator, 'validation_tool')
        assert validator.validation_tool.name == "task_validator"
        
        # Test Checker Agent tools
        checker = CheckerAgent()
        assert len(checker.tools) == 2
        assert hasattr(checker, 'progress_tool')
        assert hasattr(checker, 'termination_tool')
        assert checker.progress_tool.name == "progress_monitor"
        assert checker.termination_tool.name == "task_terminator"
    
    @patch('agents.crew_manager.Crew')
    def test_complete_workflow_integration(self, mock_crew):
        """Test the complete workflow from task creation to completion."""
        # Mock CrewAI crew
        mock_crew_instance = Mock()
        mock_crew_instance.kickoff.return_value = {
            "success": True,
            "output": "Task completed successfully"
        }
        mock_crew.return_value = mock_crew_instance
        
        # Create crew manager
        crew_manager = CrewManager()
        
        # Start monitoring
        crew_manager.start_monitoring()
        
        # Execute multiple tasks
        tasks = [
            {
                "description": "Task 1: Create file A",
                "cursor_command": "echo 'A' > file_a.txt",
                "goals": ["Create file A"],
                "success_criteria": [{"text": "File A exists"}],
                "expected_outcomes": ["File A created"]
            },
            {
                "description": "Task 2: Create file B",
                "cursor_command": "echo 'B' > file_b.txt",
                "goals": ["Create file B"],
                "success_criteria": [{"text": "File B exists"}],
                "expected_outcomes": ["File B created"]
            }
        ]
        
        results = []
        for task in tasks:
            result = crew_manager.execute_task(task)
            results.append(result)
        
        # Verify all tasks were executed
        assert len(results) == 2
        
        # Verify task history
        history = crew_manager.get_task_history()
        assert len(history) == 2
        
        # Verify crew status
        crew_status = crew_manager.get_crew_status()
        assert crew_status["completed_tasks_count"] == 2
        assert crew_status["agents"]["actor"]["name"] == "TaskExecutor"
        assert crew_status["agents"]["validator"]["name"] == "TaskValidator"
        assert crew_status["agents"]["checker"]["name"] == "ProgressChecker"
        
        # Stop monitoring
        crew_manager.stop_monitoring()
    
    def test_agent_communication_patterns(self):
        """Test that agents can communicate through the crew manager."""
        with patch('agents.crew_manager.Crew'):
            crew_manager = CrewManager()
            
            # Test agent status retrieval
            actor_status = crew_manager.get_agent_status('actor')
            validator_status = crew_manager.get_agent_status('validator')
            checker_status = crew_manager.get_agent_status('checker')
            
            assert actor_status is not None
            assert validator_status is not None
            assert checker_status is not None
            
            # Verify agent names
            assert actor_status["name"] == "TaskExecutor"
            assert validator_status["name"] == "TaskValidator"
            assert checker_status["name"] == "ProgressChecker"
            
            # Test crew status includes all agents
            crew_status = crew_manager.get_crew_status()
            assert "actor" in crew_status["agents"]
            assert "validator" in crew_status["agents"]
            assert "checker" in crew_status["agents"]
    
    @patch('agents.crew_manager.Crew')
    def test_error_handling_integration(self, mock_crew):
        """Test error handling across the entire system."""
        # Mock CrewAI crew to raise an exception
        mock_crew.side_effect = Exception("CrewAI initialization failed")
        
        # Test that crew manager handles initialization errors gracefully
        with pytest.raises(Exception) as exc_info:
            CrewManager()
        
        assert "CrewAI initialization failed" in str(exc_info.value)
    
    def test_agent_tool_functionality(self):
        """Test that agent tools work correctly."""
        # Test validation tool
        from agents.validator_agent import ValidationTool
        validation_tool = ValidationTool()
        
        # Test with valid execution result
        task_def = {"goals": ["Create file"], "success_criteria": [{"text": "File exists"}]}
        exec_result = {"success": True, "execution_output": "Created file successfully"}
        
        validation_result = validation_tool(task_def, exec_result)
        assert validation_result["validation_passed"] is True
        assert validation_result["validation_score"] > 0.0
        
        # Test with failed execution
        failed_exec = {"success": False, "error": "Permission denied"}
        failed_validation = validation_tool(task_def, failed_exec)
        assert failed_validation["validation_passed"] is False
        assert failed_validation["validation_score"] == 0.0


class TestCrewAIPerformance:
    """Test performance characteristics of the crew."""
    
    @patch('agents.crew_manager.Crew')
    def test_agent_initialization_performance(self, mock_crew):
        """Test that agent initialization is reasonably fast."""
        import time
        
        # Mock CrewAI crew
        mock_crew_instance = Mock()
        mock_crew.return_value = mock_crew_instance
        
        start_time = time.time()
        crew_manager = CrewManager()
        end_time = time.time()
        
        # Initialization should take less than 1 second
        assert (end_time - start_time) < 1.0
        
        # Verify all agents were created
        assert len(crew_manager.agents) == 3
    
    @patch('agents.crew_manager.Crew')
    def test_status_retrieval_performance(self, mock_crew):
        """Test that status retrieval is fast."""
        import time
        
        # Mock CrewAI crew
        mock_crew_instance = Mock()
        mock_crew.return_value = mock_crew_instance
        
        crew_manager = CrewManager()
        
        # Test status retrieval performance
        start_time = time.time()
        crew_status = crew_manager.get_crew_status()
        end_time = time.time()
        
        # Status retrieval should be very fast (< 100ms)
        assert (end_time - start_time) < 0.1
        
        # Verify status contains expected data
        assert "crew_id" in crew_status
        assert "agents" in crew_status


if __name__ == "__main__":
    pytest.main([__file__])
