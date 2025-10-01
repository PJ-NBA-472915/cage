"""
Pytest configuration and shared fixtures.
"""

import os
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture(scope="session")  # type: ignore[misc]
def test_environment() -> Generator[None, None, None]:
    """Set up test environment variables."""
    # Set test environment variables
    os.environ["POD_TOKEN"] = "test-token"
    os.environ["REPO_PATH"] = "/tmp/test_repo"
    os.environ["TESTING"] = "true"

    yield

    # Cleanup after tests
    if "TESTING" in os.environ:
        del os.environ["TESTING"]


@pytest.fixture  # type: ignore[misc]
def temp_repo_dir() -> Generator[Path, None, None]:
    """Create a temporary repository directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_path = Path(tmp_dir)
        yield repo_path


@pytest.fixture  # type: ignore[misc]
def sample_files(temp_repo_dir: Path) -> Path:
    """Create sample files for testing."""
    # Create some sample files
    (temp_repo_dir / "README.md").write_text(
        "# Test Repository\n\nThis is a test repository."
    )
    (temp_repo_dir / "src" / "main.py").write_text("print('Hello, World!')")
    (temp_repo_dir / "src" / "utils.py").write_text("def helper(): pass")
    (temp_repo_dir / "tests" / "test_main.py").write_text("def test_main(): pass")

    # Create .gitignore
    (temp_repo_dir / ".gitignore").write_text("__pycache__/\n*.pyc\n.env")

    return temp_repo_dir


@pytest.fixture  # type: ignore[misc]
def mock_api_response() -> dict[str, str | dict[str, str]]:
    """Mock API response for testing."""
    return {
        "status": "success",
        "data": {"message": "Test response"},
        "timestamp": "2025-09-29T20:00:00Z",
    }


# Pytest configuration
def pytest_configure(config: Any) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "smoke: mark test as a smoke test (basic functionality)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running (takes more than 5 seconds)"
    )
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "api: mark test as API test")
    config.addinivalue_line("markers", "unit: mark test as unit test")


def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:
    """Modify test collection to add markers based on file location."""
    for item in items:
        # Add markers based on file path
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "api" in str(item.fspath):
            item.add_marker(pytest.mark.api)

        # Add slow marker for tests that might be slow
        if "large" in item.name or "stress" in item.name:
            item.add_marker(pytest.mark.slow)
