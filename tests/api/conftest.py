"""
Pytest configuration and fixtures specifically for Files API tests.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def temp_repo():
    """Create a temporary repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        
        # Set up environment
        os.environ['REPO_PATH'] = str(repo_path)
        os.environ['POD_TOKEN'] = 'test-token'
        
        # Create .cage directory for task management
        (repo_path / '.cage').mkdir(exist_ok=True)
        
        yield repo_path


@pytest.fixture
def test_client(temp_repo):
    """Create a test client with mocked services."""
    with patch('src.api.main.get_repository_path') as mock_repo_path, \
         patch('src.api.main.rag_service', None):  # Disable RAG for basic tests
        
        mock_repo_path.return_value = temp_repo
        
        from src.api.main import app
        with TestClient(app) as client:
            yield client


@pytest.fixture
def auth_headers():
    """Authentication headers for API requests."""
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def test_client_with_rag(temp_repo):
    """Create test client with mocked RAG service."""
    from unittest.mock import AsyncMock
    
    mock_rag_service = AsyncMock()
    mock_rag_service.query = AsyncMock(return_value=[
        type('SearchResult', (), {
            'content': 'Test search result content',
            'metadata': type('Metadata', (), {
                'path': 'test.txt',
                'language': 'text',
                'commit_sha': 'abc123',
                'branch': 'main',
                'chunk_id': 'chunk-1'
            })(),
            'score': 0.95,
            'blob_sha': 'blob123'
        })
    ])
    
    with patch('src.api.main.get_repository_path') as mock_repo_path, \
         patch('src.api.main.rag_service', mock_rag_service):
        
        mock_repo_path.return_value = temp_repo
        
        from src.api.main import app
        with TestClient(app) as client:
            yield client
