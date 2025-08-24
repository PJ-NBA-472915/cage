"""
Shared pytest fixtures and configuration for all tests.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch


@pytest.fixture(scope="session")
def test_data_dir():
    """Provide test data directory path."""
    return Path(__file__).parent / "tests" / "data"


@pytest.fixture(scope="function")
def mock_spec_manager():
    """Provide a mocked SpecManager instance."""
    from manager.spec_manager import SpecManager
    
    with patch.object(SpecManager, 'verify_spec_directory') as mock_verify:
        mock_verify.return_value = {
            "status": "healthy",
            "file_count": 42,
            "last_verified": "2025-01-27T10:00:00Z"
        }
        
        manager = SpecManager()
        yield manager


@pytest.fixture(scope="function")
def sample_spec_structure():
    """Provide sample spec directory structure for testing."""
    return {
        "000_MASTER": ["SPEC_RAW.md", "CONTENT_HASH.txt", "EXTRACT_LOG.txt"],
        "100_SPLIT": ["007-source-control-ci.md", "008-runtime-images.md"],
        "200_INDEX": ["HEADINGS.json", "KEYWORDS.json", "MANIFEST.yaml", "XREF.json"],
        "GUIDE.md": []
    }
