"""
Functional tests for CrewAI Agents Module

Tests the actual behavior and functionality of the agents without mocking.
"""

import pytest
import sys
import os
import tempfile
import shutil
import time
from pathlib import Path

# Add the parent directory to the path so we can import the agents
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import CrewManager, ActorAgent, ValidatorAgent, CheckerAgent


class TestCrewAIFunctional:
    """Test functional behavior of the crew agents."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create test files
        self.create_test_files()
    
    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
    
    def create_test_files(self):
        """Create test files for testing."""
        # Create a simple Python file
        with open("test_module.py", "w") as f:
            f.write("""def hello_world():
    return "Hello, World!"

def add_numbers(a, b):
    return a + b

if __name__ == "__main__":
    print(hello_world())
""")
        
        # Create a test configuration file
        with open("test_config.yaml", "w") as f:
            f.write("""# Test configuration
app:
  name: "Test App"
  version: "1.0.0"
  debug: true

database:
  host: "localhost"
  port: 5432
  name: "test_db"
""")
    
    def test_actor_agent_real_execution(self):
        """Test actor agent with real command execution."""
        # Skip if cursor CLI is not available
        try:
            import subprocess
            result = subprocess.run(["cursor", "--version"], 
                                  capture_output=True, text=True, timeout=5)
            cursor_available = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            cursor_available = False
        
        if not cursor_available:
            pytest.skip("Cursor CLI not available for testing")
        
        agent = ActorAgent()
        
        # Test with a simple command that should work
        task_input = {
            "description": "List current directory contents",
            "cursor_command": "ls -la",
            "expected_outcome": "Directory listing"
        }
        
        result = agent.execute_task(task_input)
        
        # Verify the result structure
        assert "success" in result
        assert "execution_output" in result
        assert "task_description" in result
        assert "cursor_command" in result
    
    def test_validator_agent_real_validation(self):
        """Test validator agent with real validation logic."""
        agent = ValidatorAgent()
        
        # Test validation with a successful task
        task_input = {
            "task_id": "test-123",
            "task_definition": {
                "goals": ["Create a Python file", "Add a function"],
                "success_criteria": [
                    {"text": "File is created"},
                    {"text": "Function is defined"}
                ],
                "expected_outcomes": ["Working Python module"]
            },
            "execution_result": {
                "success": True,
                "execution_output": "Created Python file with hello_world function"
            }
        }
        
        result = agent.execute_task(task_input)
        
        # Verify validation result structure
        assert "validation_passed" in result
        assert "validation_score" in result
        assert "goal_validation" in result
        assert "criteria_validation" in result
        assert "overall_assessment" in result
        assert "recommendations" in result
        
        # Since our execution output matches the goals, validation should pass
        assert result["validation_passed"] is True
        assert result["validation_score"] > 0.8
        
        # Verify goal validation details
        goal_validation = result["goal_validation"]
        assert goal_validation["total_goals"] == 2
        assert goal_validation["achievement_rate"] > 0.0
        
        # Verify criteria validation details
        criteria_validation = result["criteria_validation"]
        assert criteria_validation["total_criteria"] == 2
        assert criteria_validation["completion_rate"] > 0.0
    
    def test_validator_agent_failed_execution(self):
        """Test validator agent with failed execution."""
        agent = ValidatorAgent()
        
        # Test validation with a failed task
        task_input = {
            "task_id": "test-456",
            "task_definition": {
                "goals": ["Create a protected file"],
                "success_criteria": [{"text": "File is created"}],
                "expected_outcomes": ["Protected file exists"]
            },
            "execution_result": {
                "success": False,
                "error": "Permission denied: cannot create file in protected directory"
            }
        }
        
        result = agent.execute_task(task_input)
        
        # Validation should fail for failed execution
        assert result["validation_passed"] is False
        assert result["validation_score"] == 0.0
        assert result["reason"] == "Task execution failed"
    
    def test_checker_agent_monitoring_functionality(self):
        """Test checker agent monitoring functionality."""
        agent = CheckerAgent(check_interval_minutes=1)  # Use 1 minute for testing
        
        # Start monitoring
        start_result = agent.start_monitoring()
        assert start_result["success"] is True
        assert agent.monitoring_active is True
        
        # Wait a moment for monitoring to start
        time.sleep(0.1)
        
        # Check that monitoring is active
        assert agent.monitoring_active is True
        
        # Stop monitoring
        stop_result = agent.stop_monitoring()
        assert stop_result["success"] is True
        assert agent.monitoring_active is False
    
    def test_checker_agent_progress_tracking(self):
        """Test checker agent progress tracking functionality."""
        agent = CheckerAgent()
        
        # Start monitoring a task
        task_info = {"description": "Test task for progress tracking"}
        start_result = agent.progress_tool("start_monitoring", 
                                         task_id="progress-test-123", 
                                         task_info=task_info)
        assert start_result["success"] is True
        
        # Check progress
        progress_result = agent.progress_tool("check_progress", 
                                           task_id="progress-test-123")
        assert progress_result["success"] is True
        assert "progress" in progress_result
        
        # Update progress
        agent.progress_tool.update_progress("progress-test-123", 
                                          {"status": "in_progress", "action": "Processing"})
        
        # Check progress again
        updated_progress = agent.progress_tool("check_progress", 
                                            task_id="progress-test-123")
        assert updated_progress["success"] is True
        assert updated_progress["progress"]["progress_updates_count"] > 0
        
        # Stop monitoring
        stop_result = agent.progress_tool("stop_monitoring", 
                                        task_id="progress-test-123")
        assert stop_result["success"] is True
    
    def test_checker_agent_task_termination(self):
        """Test checker agent task termination functionality."""
        agent = CheckerAgent()
        
        # Test task termination
        termination_result = agent.termination_tool("test-termination-123", 
                                                 "Test termination for functional testing")
        assert termination_result["success"] is True
        assert termination_result["task_id"] == "test-termination-123"
        assert "termination_timestamp" in termination_result
    
    def test_crew_manager_basic_functionality(self):
        """Test basic crew manager functionality."""
        # Note: This test may fail if CrewAI is not properly installed
        # We'll handle that gracefully
        try:
            crew_manager = CrewManager()
            
            # Test basic status retrieval
            crew_status = crew_manager.get_crew_status()
            assert "crew_id" in crew_status
            assert "agents" in crew_status
            assert "monitoring_active" in crew_status
            
            # Test agent status retrieval
            for agent_type in ['actor', 'validator', 'checker']:
                agent_status = crew_manager.get_agent_status(agent_type)
                assert agent_status is not None
                assert "name" in agent_status
            
            # Test task history (should be empty initially)
            history = crew_manager.get_task_history()
            assert isinstance(history, list)
            assert len(history) == 0
            
        except Exception as e:
            # If CrewAI is not available, skip the test
            if "CrewAI" in str(e) or "crewai" in str(e).lower():
                pytest.skip(f"CrewAI not available: {e}")
            else:
                raise
    
    def test_agent_tool_integration_functional(self):
        """Test that agent tools are properly integrated and functional."""
        # Test Actor Agent
        actor = ActorAgent()
        assert hasattr(actor, 'cursor_tool')
        assert actor.cursor_tool.name == "cursor_cli"
        assert callable(actor.cursor_tool)
        
        # Test Validator Agent
        validator = ValidatorAgent()
        assert hasattr(validator, 'validation_tool')
        assert validator.validation_tool.name == "task_validator"
        assert callable(validator.validation_tool)
        
        # Test Checker Agent
        checker = CheckerAgent()
        assert hasattr(checker, 'progress_tool')
        assert hasattr(checker, 'termination_tool')
        assert checker.progress_tool.name == "progress_monitor"
        assert checker.termination_tool.name == "task_terminator"
        assert callable(checker.progress_tool)
        assert callable(checker.termination_tool)
    
    def test_agent_communication_functional(self):
        """Test that agents can communicate through the crew manager."""
        try:
            crew_manager = CrewManager()
            
            # Test that all agents are accessible
            assert 'actor' in crew_manager.agents
            assert 'validator' in crew_manager.agents
            assert 'checker' in crew_manager.agents
            
            # Test agent communication through status
            actor_status = crew_manager.get_agent_status('actor')
            validator_status = crew_manager.get_agent_status('validator')
            checker_status = crew_manager.get_agent_status('checker')
            
            # Verify all agents have status information
            assert actor_status is not None
            assert validator_status is not None
            assert checker_status is not None
            
            # Verify agent names are correct
            assert actor_status["name"] == "TaskExecutor"
            assert validator_status["name"] == "TaskValidator"
            assert checker_status["name"] == "ProgressChecker"
            
        except Exception as e:
            if "CrewAI" in str(e) or "crewai" in str(e).lower():
                pytest.skip(f"CrewAI not available: {e}")
            else:
                raise
    
    def test_agent_error_handling_functional(self):
        """Test that agents handle errors gracefully."""
        # Test actor agent with invalid input
        actor = ActorAgent()
        invalid_task = {"description": "Invalid task"}  # Missing cursor_command
        
        result = actor.execute_task(invalid_task)
        assert result["success"] is False
        assert "No cursor command provided" in result["error"]
        
        # Test validator agent with missing data
        validator = ValidatorAgent()
        invalid_validation_input = {"task_id": "test-123"}  # Missing required fields
        
        result = validator.execute_task(invalid_validation_input)
        assert result["success"] is False
        assert "Missing task definition" in result["error"]
        
        # Test checker agent with unknown action
        checker = CheckerAgent()
        invalid_action = {"action": "unknown_action"}
        
        result = checker.execute_task(invalid_action)
        assert result["success"] is False
        assert "Unknown action" in result["error"]


class TestCrewAIRealWorldScenarios:
    """Test real-world usage scenarios."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_file_creation_workflow(self):
        """Test a complete file creation workflow."""
        try:
            crew_manager = CrewManager()
            
            # Start monitoring
            crew_manager.start_monitoring()
            
            # Execute a simple file creation task
            task = {
                "description": "Create a test configuration file",
                "cursor_command": "echo 'app_name: TestApp' > config.yaml",
                "goals": [
                    "Create a configuration file",
                    "Add application name"
                ],
                "success_criteria": [
                    {"text": "File exists"},
                    {"text": "Contains app name"}
                ],
                "expected_outcomes": [
                    "Configuration file created",
                    "File contains required data"
                ]
            }
            
            # Execute the task
            result = crew_manager.execute_task(task)
            
            # Verify the result structure
            assert "task_id" in result
            assert "execution_result" in result
            assert "validation_result" in result
            
            # Stop monitoring
            crew_manager.stop_monitoring()
            
        except Exception as e:
            if "CrewAI" in str(e) or "crewai" in str(e).lower():
                pytest.skip(f"CrewAI not available: {e}")
            else:
                raise
    
    def test_multiple_task_execution(self):
        """Test executing multiple tasks in sequence."""
        try:
            crew_manager = CrewManager()
            
            # Start monitoring
            crew_manager.start_monitoring()
            
            # Define multiple tasks
            tasks = [
                {
                    "description": "Create directory structure",
                    "cursor_command": "mkdir -p src tests docs",
                    "goals": ["Create directory structure"],
                    "success_criteria": [{"text": "Directories exist"}],
                    "expected_outcomes": ["Project structure created"]
                },
                {
                    "description": "Create README file",
                    "cursor_command": "echo '# Test Project' > README.md",
                    "goals": ["Create README file"],
                    "success_criteria": [{"text": "README exists"}],
                    "expected_outcomes": ["README file created"]
                }
            ]
            
            # Execute all tasks
            results = []
            for task in tasks:
                result = crew_manager.execute_task(task)
                results.append(result)
            
            # Verify all tasks were executed
            assert len(results) == 2
            
            # Verify task history
            history = crew_manager.get_task_history()
            assert len(history) == 2
            
            # Stop monitoring
            crew_manager.stop_monitoring()
            
        except Exception as e:
            if "CrewAI" in str(e) or "crewai" in str(e).lower():
                pytest.skip(f"CrewAI not available: {e}")
            else:
                raise


if __name__ == "__main__":
    pytest.main([__file__])
