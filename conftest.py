"""
Shared pytest configuration and fixtures for the cage platform.

This file provides common fixtures, configuration, and utilities that can be
used across all test files in the project.
"""

import asyncio
import os
import pytest
from unittest.mock import Mock, patch
from loguru import logger


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an instance of the default event loop for the test session.
    
    This fixture ensures that async tests can run properly.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_gemini_api_key():
    """
    Mock GEMINI_API_KEY environment variable for testing.
    
    Returns:
        str: A mock API key for testing purposes.
    """
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key-12345"}):
        yield "test-api-key-12345"


@pytest.fixture
def mock_logger():
    """
    Mock logger to capture log messages during testing.
    
    Returns:
        Mock: A mock logger object that can be used to verify log calls.
    """
    with patch("loguru.logger") as mock_log:
        yield mock_log


@pytest.fixture
def sample_environment_vars():
    """
    Sample environment variables for testing.
    
    Returns:
        dict: A dictionary of sample environment variables.
    """
    return {
        "GEMINI_API_KEY": "test-key-12345",
        "LOG_LEVEL": "INFO",
        "HEALTH_CHECK_PORT": "8080",
        "HEARTBEAT_INTERVAL": "10"
    }


@pytest.fixture
def mock_google_generativeai():
    """
    Mock google.generativeai module for testing.
    
    Returns:
        Mock: A mock module that can be used to verify API calls.
    """
    mock_genai = Mock()
    mock_genai.configure = Mock()
    mock_genai.GenerativeModel = Mock()
    
    with patch("daemon.google.generativeai", mock_genai):
        yield mock_genai


@pytest.fixture
def mock_uvloop():
    """
    Mock uvloop module for testing.
    
    Returns:
        Mock: A mock module that can be used to verify uvloop usage.
    """
    with patch("uvloop") as mock_uv:
        mock_uv.install = Mock()
        yield mock_uv


@pytest.fixture
def async_context():
    """
    Context manager for running async code in tests.
    
    Yields:
        asyncio.AbstractEventLoop: The event loop for running async code.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield loop
    finally:
        loop.close()


@pytest.fixture(autouse=True)
def setup_test_environment():
    """
    Automatically setup test environment before each test.
    
    This fixture runs before every test to ensure a clean environment.
    """
    # Clear any existing environment variables that might interfere
    test_env_vars = ["GEMINI_API_KEY", "LOG_LEVEL", "HEALTH_CHECK_PORT"]
    original_values = {}
    
    for var in test_env_vars:
        if var in os.environ:
            original_values[var] = os.environ[var]
            del os.environ[var]
    
    yield
    
    # Restore original environment variables
    for var, value in original_values.items():
        os.environ[var] = value


def pytest_configure(config):
    """
    Configure pytest with custom markers and settings.
    
    Args:
        config: The pytest configuration object.
    """
    # Register custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "asyncio: marks tests as async tests"
    )
    config.addinivalue_line(
        "markers", "network: marks tests that require network connectivity"
    )
    config.addinivalue_line(
        "markers", "docker: marks tests that require docker environment"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to add markers based on test names.
    
    Args:
        config: The pytest configuration object.
        items: List of test items to modify.
    """
    for item in items:
        # Mark async tests
        if "async" in item.name.lower() or "async" in str(item.function.__code__.co_name).lower():
            item.add_marker(pytest.mark.asyncio)
        
        # Mark network tests
        if "network" in item.name.lower() or "connectivity" in item.name.lower():
            item.add_marker(pytest.mark.network)
        
        # Mark docker tests
        if "docker" in item.name.lower() or "container" in item.name.lower():
            item.add_marker(pytest.mark.docker)
