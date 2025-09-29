"""
Basic test suite for Files API routes.

This module tests the core file operations to ensure the API is working correctly.
"""

import base64
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def temp_repo():
    """Create a temporary repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        
        # Set up environment
        import os
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


class TestBasicFileOperations:
    """Test basic file operations."""
    
    def test_get_existing_file(self, test_client, auth_headers, temp_repo):
        """Test retrieving an existing file."""
        # Create test file
        test_file = temp_repo / "test.txt"
        test_content = "Hello, World!"
        test_file.write_text(test_content)
        
        response = test_client.get("/files/test.txt", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data['path'] == "test.txt"
        
        # Decode base64 content
        decoded_content = base64.b64decode(data['content']).decode('utf-8')
        assert decoded_content == test_content
        assert data['size'] == len(test_content)
    
    def test_get_nonexistent_file(self, test_client, auth_headers):
        """Test retrieving a non-existent file."""
        response = test_client.get("/files/nonexistent.txt", headers=auth_headers)
        
        # Should return 404 or 500 depending on error handling
        assert response.status_code in [404, 500]
    
    def test_put_create_file(self, test_client, auth_headers, temp_repo):
        """Test creating a file with PUT."""
        content = "New file content"
        content_base64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
        
        request_data = {
            "message": "Create new file",
            "content_base64": content_base64
        }
        
        response = test_client.put("/files/new-file.txt", json=request_data, headers=auth_headers)
        
        # Should return 200 or 201
        assert response.status_code in [200, 201]
        
        # Verify file was created
        new_file = temp_repo / "new-file.txt"
        assert new_file.exists()
        assert new_file.read_text() == content
    
    def test_authentication_required(self, test_client, temp_repo):
        """Test that authentication is required."""
        # Create test file
        test_file = temp_repo / "test.txt"
        test_file.write_text("Test content")
        
        # Try to access without authentication
        response = test_client.get("/files/test.txt")
        
        # Should require authentication
        assert response.status_code in [401, 403]
    
    def test_path_validation(self, test_client, auth_headers):
        """Test path validation prevents directory traversal."""
        # Try to access files outside the repository
        malicious_paths = [
            "../etc/passwd",
            "../../../home/user",
            "/etc/passwd"
        ]
        
        for path in malicious_paths:
            response = test_client.get(f"/files/{path}", headers=auth_headers)
            # Should be rejected
            assert response.status_code in [400, 404, 500]
    
    def test_json_file_operations(self, test_client, auth_headers, temp_repo):
        """Test operations on JSON files."""
        json_file = temp_repo / "config.json"
        json_content = '{"name": "test", "version": "1.0.0"}'
        json_file.write_text(json_content)
        
        # Test GET
        response = test_client.get("/files/config.json", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data['path'] == "config.json"
        
        # Decode and verify content
        decoded_content = base64.b64decode(data['content']).decode('utf-8')
        assert decoded_content == json_content
    
    def test_python_file_operations(self, test_client, auth_headers, temp_repo):
        """Test operations on Python files."""
        py_file = temp_repo / "main.py"
        py_content = '''#!/usr/bin/env python3
"""Main module."""

def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
'''
        py_file.write_text(py_content)
        
        # Test GET
        response = test_client.get("/files/main.py", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data['path'] == "main.py"
        
        # Decode and verify content
        decoded_content = base64.b64decode(data['content']).decode('utf-8')
        assert decoded_content == py_content

