"""
Pytest configuration for CrewAI Agents tests.

This file provides shared fixtures and configuration for all tests.
"""

import pytest
import sys
import os
import tempfile
import shutil
from unittest.mock import patch, Mock

# Add the parent directory to the path so we can import the agents
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def temp_test_dir():
    """Create a temporary directory for testing that persists across the session."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture(scope="function")
def temp_working_dir():
    """Create a temporary working directory for individual tests."""
    temp_dir = tempfile.mkdtemp()
    original_cwd = os.getcwd()
    os.chdir(temp_dir)
    
    yield temp_dir
    
    os.chdir(original_cwd)
    shutil.rmtree(temp_dir)


@pytest.fixture(scope="function")
def mock_crewai():
    """Mock CrewAI framework for testing."""
    with patch('agents.crew_manager.Crew') as mock_crew, \
         patch('agents.base_agent.Agent') as mock_agent:
        
        # Mock CrewAI agent
        mock_agent_instance = Mock()
        mock_agent_instance.name = "MockAgent"
        mock_agent.return_value = mock_agent_instance
        
        # Mock CrewAI crew
        mock_crew_instance = Mock()
        mock_crew_instance.kickoff.return_value = {
            "success": True,
            "output": "Mock task execution result"
        }
        mock_crew.return_value = mock_crew_instance
        
        yield {
            'crew': mock_crew,
            'agent': mock_agent,
            'crew_instance': mock_crew_instance,
            'agent_instance': mock_agent_instance
        }


@pytest.fixture(scope="function")
def mock_subprocess():
    """Mock subprocess for testing cursor CLI commands."""
    with patch('agents.actor_agent.subprocess.run') as mock_run:
        # Default successful result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Mock successful output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        yield mock_run


@pytest.fixture(scope="function")
def sample_task_definition():
    """Provide a sample task definition for testing."""
    return {
        "description": "Create a test Python module",
        "cursor_command": "cursor generate 'Create a Python module with hello world function' --output hello.py",
        "goals": [
            "Create a Python module",
            "Include hello world function",
            "Make it executable"
        ],
        "success_criteria": [
            {"text": "Python file is created"},
            {"text": "Function is defined"},
            {"text": "File is executable"}
        ],
        "expected_outcomes": [
            "Working Python module",
            "Executable script",
            "Hello world functionality"
        ]
    }


@pytest.fixture(scope="function")
def sample_execution_result():
    """Provide a sample execution result for testing."""
    return {
        "success": True,
        "execution_output": "Created Python module with hello world function. File is executable.",
        "task_description": "Create a test Python module",
        "cursor_command": "cursor generate 'Create a Python module with hello world function' --output hello.py",
        "expected_outcome": "Working Python module",
        "timestamp": "2025-08-25T10:00:00"
    }


@pytest.fixture(scope="function")
def sample_failed_execution_result():
    """Provide a sample failed execution result for testing."""
    return {
        "success": False,
        "error": "Permission denied: cannot create file in protected directory",
        "task_description": "Create a protected file",
        "cursor_command": "echo 'content' > /protected/file.txt",
        "expected_outcome": "Protected file exists",
        "timestamp": "2025-08-25T10:00:00"
    }


@pytest.fixture(scope="function")
def mock_cursor_cli_available():
    """Mock cursor CLI availability for testing."""
    with patch('agents.actor_agent.subprocess.run') as mock_run:
        # Mock cursor --version check
        mock_version_result = Mock()
        mock_version_result.returncode = 0
        mock_version_result.stdout = "Cursor CLI version 1.0.0"
        
        # Mock actual command execution
        mock_cmd_result = Mock()
        mock_cmd_result.returncode = 0
        mock_cmd_result.stdout = "Command executed successfully"
        
        # Configure mock to return different results for different commands
        def mock_run_side_effect(cmd, *args, **kwargs):
            if "cursor --version" in cmd:
                return mock_version_result
            else:
                return mock_cmd_result
        
        mock_run.side_effect = mock_run_side_effect
        yield mock_run


@pytest.fixture(scope="function")
def mock_cursor_cli_unavailable():
    """Mock cursor CLI unavailability for testing."""
    with patch('agents.actor_agent.subprocess.run') as mock_run:
        # Mock cursor --version check failure
        mock_run.side_effect = FileNotFoundError("cursor: command not found")
        yield mock_run


@pytest.fixture(scope="session")
def test_files():
    """Create test files that can be used across tests."""
    temp_dir = tempfile.mkdtemp()
    
    # Create a simple Python file
    python_file = os.path.join(temp_dir, "test_module.py")
    with open(python_file, "w") as f:
        f.write("""def hello_world():
    return "Hello, World!"

def add_numbers(a, b):
    return a + b

if __name__ == "__main__":
    print(hello_world())
""")
    
    # Create a test configuration file
    config_file = os.path.join(temp_dir, "test_config.yaml")
    with open(config_file, "w") as f:
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
    
    # Create a simple text file
    text_file = os.path.join(temp_dir, "test_data.txt")
    with open(text_file, "w") as f:
        f.write("This is test data for the CrewAI agents tests.\n")
        f.write("It contains multiple lines of text.\n")
        f.write("Used for testing file operations and validation.\n")
    
    yield {
        'directory': temp_dir,
        'python_file': python_file,
        'config_file': config_file,
        'text_file': text_file
    }
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture(scope="function")
def mock_time():
    """Mock time functions for testing."""
    with patch('agents.checker_agent.time.sleep') as mock_sleep, \
         patch('agents.checker_agent.datetime') as mock_datetime:
        
        # Mock datetime.now() to return predictable timestamps
        mock_now = Mock()
        mock_now.isoformat.return_value = "2025-08-25T10:00:00"
        mock_datetime.now.return_value = mock_now
        
        yield {
            'sleep': mock_sleep,
            'datetime': mock_datetime,
            'now': mock_now
        }


@pytest.fixture(scope="function")
def mock_threading():
    """Mock threading for testing."""
    with patch('agents.checker_agent.threading.Thread') as mock_thread_class:
        mock_thread = Mock()
        mock_thread.start.return_value = None
        mock_thread.join.return_value = None
        mock_thread_class.return_value = mock_thread
        
        yield {
            'thread_class': mock_thread_class,
            'thread': mock_thread
        }


def pytest_configure(config):
    """Configure pytest for CrewAI agents testing."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "crewai: mark test as requiring CrewAI framework"
    )
    config.addinivalue_line(
        "markers", "cursor_cli: mark test as requiring cursor CLI"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "functional: mark test as functional test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file location."""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "functional" in str(item.fspath):
            item.add_marker(pytest.mark.functional)
        
        # Add crewai marker for all agent tests
        if "crewai" in str(item.fspath) or "agent" in str(item.fspath):
            item.add_marker(pytest.mark.crewai)
        
        # Add cursor_cli marker for tests that use cursor CLI
        if "actor" in str(item.fspath) or "cursor" in str(item.fspath):
            item.add_marker(pytest.mark.cursor_cli)
