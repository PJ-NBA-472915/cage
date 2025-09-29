"""
Comprehensive test suite for Files API routes.

This module tests all file-related endpoints including:
- File CRUD operations (GET, PUT, PATCH, DELETE)
- File search functionality (RAG integration)
- File reindexing
- Audit trail
- Security features (path validation, user restrictions)
- All file types (JSON, text, code, markdown, YAML, etc.)
"""

import base64
import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock
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


class TestFileCRUDOperations:
    """Test file CRUD operations."""
    
    def test_get_file_success(self, test_client, auth_headers, temp_repo):
        """Test successful file retrieval."""
        # Create test file
        test_file = temp_repo / "test.txt"
        test_content = "Hello, World!"
        test_file.write_text(test_content)
        
        response = test_client.get("/files/test.txt", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data['path'] == "test.txt"
        
        # Decode base64 content
        import base64
        decoded_content = base64.b64decode(data['content']).decode('utf-8')
        assert decoded_content == test_content
        assert data['size'] == len(test_content)
        assert 'etag' in response.headers
    
    def test_get_file_not_found(self, test_client, auth_headers):
        """Test file retrieval when file doesn't exist."""
        response = test_client.get("/files/nonexistent.txt", headers=auth_headers)
        assert response.status_code == 404
    
    def test_get_file_raw_output(self, test_client, auth_headers, temp_repo):
        """Test raw file output."""
        test_file = temp_repo / "test.txt"
        test_content = "Raw content"
        test_file.write_text(test_content)
        
        response = test_client.get("/files/test.txt?raw=true", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.text == test_content
        assert response.headers['content-type'] == 'text/plain; charset=utf-8'
    
    def test_put_file_create(self, test_client, auth_headers):
        """Test file creation with PUT."""
        content = "New file content"
        content_base64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
        
        request_data = {
            "message": "Create new file",
            "content_base64": content_base64
        }
        
        response = test_client.put("/files/new-file.txt", json=request_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data['path'] == "new-file.txt"
        assert 'sha_after' in data
        assert 'commit' in data
    
    def test_put_file_update_requires_if_match(self, test_client, auth_headers, temp_repo):
        """Test that file updates require If-Match header."""
        # Create initial file
        test_file = temp_repo / "test.txt"
        test_file.write_text("Initial content")
        
        # Try to update without If-Match header
        content = "Updated content"
        content_base64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
        
        request_data = {
            "message": "Update file",
            "content_base64": content_base64
        }
        
        response = test_client.put("/files/test.txt", json=request_data, headers=auth_headers)
        assert response.status_code == 428  # Precondition Required
    
    def test_put_file_update_with_if_match(self, test_client, auth_headers, temp_repo):
        """Test file update with proper If-Match header."""
        # Create initial file
        test_file = temp_repo / "test.txt"
        test_file.write_text("Initial content")
        
        # Get current ETag
        get_response = test_client.get("/files/test.txt", headers=auth_headers)
        current_etag = get_response.headers.get("etag") or get_response.headers.get("ETag")
        
        # Update file with If-Match header
        content = "Updated content"
        content_base64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
        
        request_data = {
            "message": "Update file",
            "content_base64": content_base64
        }
        
        headers = {**auth_headers, "If-Match": current_etag}
        response = test_client.put("/files/test.txt", json=request_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data['path'] == "test.txt"
        assert 'sha_before' in data
        assert 'sha_after' in data
    
    def test_delete_file_success(self, test_client, auth_headers, temp_repo):
        """Test successful file deletion."""
        # Create test file
        test_file = temp_repo / "test.txt"
        test_file.write_text("Content to delete")
        
        # Get current ETag
        get_response = test_client.get("/files/test.txt", headers=auth_headers)
        current_etag = get_response.headers.get("etag") or get_response.headers.get("ETag")
        
        # Delete file
        request_data = {"message": "Delete file"}
        headers = {**auth_headers, "If-Match": current_etag}
        
        response = test_client.request("DELETE", "/files/test.txt", json=request_data, headers=headers)
        
        assert response.status_code == 200
        assert not test_file.exists()
    
    def test_delete_file_not_found(self, test_client, auth_headers):
        """Test deletion of non-existent file."""
        request_data = {"message": "Delete non-existent file"}
        headers = {**auth_headers, "If-Match": "some-etag"}
        
        response = test_client.request("DELETE", "/files/nonexistent.txt", json=request_data, headers=headers)
        assert response.status_code == 404


class TestFilePatchOperations:
    """Test file patching operations for different file types."""
    
    def test_json_patch_success(self, test_client, auth_headers, temp_repo):
        """Test JSON Patch on JSON file."""
        # Create JSON file
        json_file = temp_repo / "test.json"
        json_content = '{"name": "test", "value": 42, "items": [1, 2, 3]}'
        json_file.write_text(json_content)
        
        # Get current ETag
        get_response = test_client.get("/files/test.json", headers=auth_headers)
        current_etag = get_response.headers.get("etag") or get_response.headers.get("ETag")
        
        # Apply JSON patch
        patch_operations = [
            {"op": "replace", "path": "/value", "value": 999},
            {"op": "add", "path": "/new_field", "value": "added"}
        ]
        
        request_data = {"operations": patch_operations}
        headers = {**auth_headers, "If-Match": current_etag}
        
        response = test_client.patch("/files/test.json", json=request_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data['path'] == "test.json"
        
        # Verify changes
        updated_content = json_file.read_text()
        updated_data = json.loads(updated_content)
        assert updated_data["value"] == 999
        assert updated_data["new_field"] == "added"
    
    def test_text_patch_success(self, test_client, auth_headers, temp_repo):
        """Test text patch on any file type."""
        # Create text file
        text_file = temp_repo / "test.py"
        original_content = '''def hello():
    print("Hello, World!")

if __name__ == "__main__":
    hello()
'''
        text_file.write_text(original_content)
        
        # Get current ETag
        get_response = test_client.get("/files/test.py", headers=auth_headers)
        current_etag = get_response.headers.get("etag") or get_response.headers.get("ETag")
        
        # Apply text patch
        new_content = '''def hello():
    print("Hello, Updated World!")

def new_function():
    print("This is new!")

if __name__ == "__main__":
    hello()
    new_function()
'''
        request_data = {
            "content": new_content,
            "message": "Updated Python file"
        }
        
        headers = {**auth_headers, "If-Match": current_etag}
        response = test_client.patch("/files/test.py", json=request_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data['path'] == "test.py"
        
        # Verify changes
        updated_content = text_file.read_text()
        assert "new_function" in updated_content
        assert "Updated Python file" in updated_content
    
    def test_line_patch_success(self, test_client, auth_headers, temp_repo):
        """Test line-based patch on text file."""
        # Create text file
        text_file = temp_repo / "test.txt"
        original_content = "Line 1\nLine 2\nLine 3\nLine 4"
        text_file.write_text(original_content)
        
        # Get current ETag
        get_response = test_client.get("/files/test.txt", headers=auth_headers)
        current_etag = get_response.headers.get("etag") or get_response.headers.get("ETag")
        
        # Apply line patch
        line_operations = [
            {"op": "replace_line", "line_number": 2, "content": "Line 2: Updated"},
            {"op": "insert_at", "line_number": 4, "content": "Line 3.5: Inserted"},
            {"op": "add_line", "content": "Line 5: Added at end"}
        ]
        
        request_data = {
            "operations": line_operations,
            "message": "Applied line operations"
        }
        
        headers = {**auth_headers, "If-Match": current_etag}
        response = test_client.patch("/files/test.txt", json=request_data, headers=headers)
        
        assert response.status_code == 200
        
        # Verify changes
        updated_content = text_file.read_text()
        lines = updated_content.strip().split('\n')
        assert "Line 2: Updated" in lines[1]
        assert "Line 3.5: Inserted" in lines[3]
        assert "Line 5: Added at end" in lines[5]
    
    def test_json_patch_on_non_json_file_fails(self, test_client, auth_headers, temp_repo):
        """Test that JSON patch fails on non-JSON files."""
        # Create non-JSON file
        text_file = temp_repo / "test.py"
        text_file.write_text("This is not JSON")
        
        # Get current ETag
        get_response = test_client.get("/files/test.py", headers=auth_headers)
        current_etag = get_response.headers.get("etag") or get_response.headers.get("ETag")
        
        # Try JSON patch
        patch_operations = [{"op": "replace", "path": "/value", "value": 999}]
        request_data = {"operations": patch_operations}
        headers = {**auth_headers, "If-Match": current_etag}
        
        response = test_client.patch("/files/test.py", json=request_data, headers=headers)
        
        assert response.status_code == 422
        assert "JSON Patch not supported" in response.json()["detail"]
    
    def test_patch_without_if_match_fails(self, test_client, auth_headers, temp_repo):
        """Test that patch operations require If-Match header."""
        # Create test file
        test_file = temp_repo / "test.txt"
        test_file.write_text("Initial content")
        
        # Try patch without If-Match header
        request_data = {
            "content": "Updated content",
            "message": "Update without ETag"
        }
        
        response = test_client.patch("/files/test.txt", json=request_data, headers=auth_headers)
        assert response.status_code == 422  # Missing required header


class TestFileSearchOperations:
    """Test file search functionality (RAG integration)."""
    
    @pytest.fixture
    def test_client_with_rag(self, temp_repo):
        """Create test client with mocked RAG service."""
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
    
    def test_file_search_success(self, test_client_with_rag, auth_headers):
        """Test successful file search."""
        search_request = {
            "query": "test content",
            "filters": None,
            "top_k": 5
        }
        
        response = test_client_with_rag.post("/files/search", json=search_request, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert data['total'] == 1
        assert len(data['hits']) == 1
        assert data['hits'][0]['content'] == 'Test search result content'
        assert data['hits'][0]['metadata']['path'] == 'test.txt'
    
    def test_file_search_without_rag_service(self, test_client, auth_headers):
        """Test file search when RAG service is unavailable."""
        search_request = {
            "query": "test content",
            "top_k": 5
        }
        
        response = test_client.post("/files/search", json=search_request, headers=auth_headers)
        assert response.status_code == 503
    
    def test_file_reindex_success(self, test_client, auth_headers, temp_repo):
        """Test file reindexing."""
        mock_rag_service = AsyncMock()
        mock_rag_service.reindex_repository = AsyncMock(return_value={
            "indexed_files": 3,
            "total_chunks": 6,
            "blob_shas": ["blob123", "blob456", "blob789"]
        })
        
        with patch('src.api.main.rag_service', mock_rag_service):
            from src.api.main import app
            with TestClient(app) as client:
                reindex_request = {"scope": "repo"}
                response = client.post("/files/reindex", json=reindex_request, headers=auth_headers)
                
                assert response.status_code == 200
                data = response.json()
                assert data['status'] == 'success'
                assert data['scope'] == 'repo'
                assert data['indexed_files'] == 3
    
    def test_blob_metadata_check(self, test_client, auth_headers):
        """Test blob metadata checking."""
        mock_rag_service = AsyncMock()
        mock_rag_service.check_blob_metadata = AsyncMock(return_value={
            "exists": True,
            "metadata": {
                "path": "test.txt",
                "language": "text",
                "commit_sha": "abc123"
            }
        })
        
        with patch('src.api.main.rag_service', mock_rag_service):
            from src.api.main import app
            with TestClient(app) as client:
                response = client.get("/files/blobs/abc123", headers=auth_headers)
                
                assert response.status_code == 200
                data = response.json()
                assert data['exists'] == True
                assert data['metadata']['path'] == 'test.txt'


class TestSecurityFeatures:
    """Test security features and path validation."""
    
    def test_path_traversal_prevention(self, test_client, auth_headers):
        """Test that directory traversal attacks are prevented."""
        malicious_paths = [
            "../etc/passwd",
            "../../../home/user",
            "logs/../../etc/passwd",
            "/etc/passwd",
            "config/../../../etc/passwd"
        ]
        
        for path in malicious_paths:
            response = test_client.get(f"/files/{path}", headers=auth_headers)
            assert response.status_code in [400, 404]  # Should be rejected
    
    def test_hidden_file_access_restriction(self, test_client, auth_headers):
        """Test that access to hidden files is restricted."""
        hidden_paths = [
            ".env",
            ".git/config",
            ".ssh/id_rsa",
            "config/.secret"
        ]
        
        for path in hidden_paths:
            response = test_client.get(f"/files/{path}", headers=auth_headers)
            assert response.status_code in [400, 404]  # Should be rejected
    
    def test_cage_directory_access_allowed(self, test_client, auth_headers, temp_repo):
        """Test that .cage directory access is allowed for task management."""
        # Create .cage directory and file
        cage_dir = temp_repo / ".cage"
        cage_dir.mkdir(exist_ok=True)
        cage_file = cage_dir / "tasks.json"
        cage_file.write_text('{"tasks": []}')
        
        response = test_client.get("/files/.cage/tasks.json", headers=auth_headers)
        assert response.status_code == 200
    
    def test_authentication_required(self, test_client, temp_repo):
        """Test that authentication is required for all endpoints."""
        # Create test file
        test_file = temp_repo / "test.txt"
        test_file.write_text("Test content")
        
        endpoints = [
            ("GET", "/files/test.txt"),
            ("PUT", "/files/test.txt"),
            ("PATCH", "/files/test.txt"),
            ("DELETE", "/files/test.txt"),
            ("POST", "/files/search"),
            ("POST", "/files/reindex"),
            ("GET", "/files/blobs/test-sha"),
            ("GET", "/audit")
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = test_client.get(endpoint)
            elif method == "PUT":
                response = test_client.put(endpoint, json={"message": "test"})
            elif method == "PATCH":
                response = test_client.patch(endpoint, json={"content": "test"})
            elif method == "DELETE":
                response = test_client.request("DELETE", endpoint, json={"message": "test"})
            elif method == "POST":
                response = test_client.post(endpoint, json={"query": "test"})
            
            assert response.status_code in [401, 403]  # Should require authentication


class TestFileTypes:
    """Test different file types and their handling."""
    
    def test_json_file_operations(self, test_client, auth_headers, temp_repo):
        """Test operations on JSON files."""
        json_file = temp_repo / "config.json"
        json_content = '{"name": "test", "version": "1.0.0"}'
        json_file.write_text(json_content)
        
        # Test GET
        response = test_client.get("/files/config.json", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data['content'] == json_content
    
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
        assert data['content'] == py_content
    
    def test_markdown_file_operations(self, test_client, auth_headers, temp_repo):
        """Test operations on Markdown files."""
        md_file = temp_repo / "README.md"
        md_content = '''# Project Title

This is a test project.

## Features

- Feature 1
- Feature 2

## Usage

```python
print("Hello, World!")
```
'''
        md_file.write_text(md_content)
        
        # Test GET
        response = test_client.get("/files/README.md", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data['content'] == md_content
    
    def test_yaml_file_operations(self, test_client, auth_headers, temp_repo):
        """Test operations on YAML files."""
        yaml_file = temp_repo / "config.yaml"
        yaml_content = '''name: test-project
version: 1.0.0
settings:
  debug: true
  port: 8000
features:
  - feature1
  - feature2
'''
        yaml_file.write_text(yaml_content)
        
        # Test GET
        response = test_client.get("/files/config.yaml", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data['content'] == yaml_content
    
    def test_xml_file_operations(self, test_client, auth_headers, temp_repo):
        """Test operations on XML files."""
        xml_file = temp_repo / "config.xml"
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <settings>
        <name>test-project</name>
        <version>1.0.0</version>
    </settings>
</configuration>
'''
        xml_file.write_text(xml_content)
        
        # Test GET
        response = test_client.get("/files/config.xml", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data['content'] == xml_content


class TestAuditTrail:
    """Test audit trail functionality."""
    
    def test_audit_trail_query(self, test_client, auth_headers, temp_repo):
        """Test audit trail querying."""
        # Perform some file operations to generate audit entries
        test_file = temp_repo / "audit-test.txt"
        test_file.write_text("Initial content")
        
        # GET operation
        test_client.get("/files/audit-test.txt", headers=auth_headers)
        
        # PUT operation
        content = "Updated content"
        content_base64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
        request_data = {
            "message": "Update for audit test",
            "content_base64": content_base64
        }
        test_client.put("/files/audit-test.txt", json=request_data, headers=auth_headers)
        
        # Query audit trail
        response = test_client.get("/audit", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert 'items' in data
        assert len(data['items']) > 0
        
        # Check that audit entries contain expected fields
        for item in data['items']:
            assert 'id' in item
            assert 'timestamp' in item
            assert 'actor' in item
            assert 'method' in item
            assert 'path' in item
    
    def test_audit_trail_filtering(self, test_client, auth_headers, temp_repo):
        """Test audit trail filtering."""
        # Create and modify a specific file
        test_file = temp_repo / "filter-test.txt"
        test_file.write_text("Content")
        
        test_client.get("/files/filter-test.txt", headers=auth_headers)
        
        # Query audit trail filtered by path
        response = test_client.get("/audit?path=filter-test.txt", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # All entries should be for the filtered path
        for item in data['items']:
            assert item['path'] == "filter-test.txt"


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_json_in_patch(self, test_client, auth_headers, temp_repo):
        """Test handling of invalid JSON in patch operations."""
        # Create invalid JSON file
        json_file = temp_repo / "invalid.json"
        json_file.write_text('{"name": "test", "value": 42')  # Missing closing brace
        
        get_response = test_client.get("/files/invalid.json", headers=auth_headers)
        current_etag = get_response.headers.get("etag") or get_response.headers.get("ETag")
        
        # Try to patch invalid JSON
        patch_operations = [{"op": "replace", "path": "/value", "value": 999}]
        request_data = {"operations": patch_operations}
        headers = {**auth_headers, "If-Match": current_etag}
        
        response = test_client.patch("/files/invalid.json", json=request_data, headers=headers)
        assert response.status_code == 422
        assert "not valid JSON" in response.json()["detail"]
    
    def test_etag_mismatch(self, test_client, auth_headers, temp_repo):
        """Test ETag mismatch handling."""
        # Create test file
        test_file = temp_repo / "test.txt"
        test_file.write_text("Initial content")
        
        # Try to update with wrong ETag
        content = "Updated content"
        content_base64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
        
        request_data = {
            "message": "Update with wrong ETag",
            "content_base64": content_base64
        }
        
        headers = {**auth_headers, "If-Match": "wrong-etag"}
        response = test_client.put("/files/test.txt", json=request_data, headers=headers)
        
        assert response.status_code == 412  # Precondition Failed
    
    def test_file_too_large(self, test_client, auth_headers, temp_repo):
        """Test handling of large files."""
        # Create a large file (simulate)
        large_content = "x" * 1000000  # 1MB of content
        large_file = temp_repo / "large.txt"
        large_file.write_text(large_content)
        
        # Test GET on large file
        response = test_client.get("/files/large.txt", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data['size'] == len(large_content)
    
    def test_unicode_content(self, test_client, auth_headers, temp_repo):
        """Test handling of Unicode content."""
        unicode_content = "Hello 世界! 🌍 This is a test with émojis and spécial characters."
        unicode_file = temp_repo / "unicode.txt"
        unicode_file.write_text(unicode_content, encoding='utf-8')
        
        # Test GET
        response = test_client.get("/files/unicode.txt", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data['content'] == unicode_content
    
    def test_binary_file_handling(self, test_client, auth_headers, temp_repo):
        """Test handling of binary files."""
        # Create a binary-like file
        binary_content = b'\x00\x01\x02\x03\xff\xfe\xfd'
        binary_file = temp_repo / "binary.bin"
        binary_file.write_bytes(binary_content)
        
        # Test GET (should fail for binary content)
        response = test_client.get("/files/binary.bin", headers=auth_headers)
        # This might succeed if the content can be decoded as text
        # or fail if it's truly binary - both are acceptable
        assert response.status_code in [200, 422]


@pytest.mark.integration
class TestIntegrationScenarios:
    """Test complex integration scenarios."""
    
    def test_full_file_lifecycle(self, test_client, auth_headers, temp_repo):
        """Test complete file lifecycle: create, read, update, delete."""
        # 1. Create file
        content = "Initial content"
        content_base64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
        
        request_data = {
            "message": "Create file",
            "content_base64": content_base64
        }
        
        response = test_client.put("/files/lifecycle-test.txt", json=request_data, headers=auth_headers)
        assert response.status_code == 201
        
        file_path = temp_repo / "lifecycle-test.txt"
        assert file_path.exists()
        
        # 2. Read file
        response = test_client.get("/files/lifecycle-test.txt", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data['content'] == content
        
        # 3. Update file with PATCH (text patch)
        current_etag = response.headers.get("etag") or response.headers.get("ETag")
        new_content = "Updated content with more text"
        
        patch_request = {
            "content": new_content,
            "message": "Update file content"
        }
        
        headers = {**auth_headers, "If-Match": current_etag}
        response = test_client.patch("/files/lifecycle-test.txt", json=patch_request, headers=headers)
        assert response.status_code == 200
        
        # Verify update
        response = test_client.get("/files/lifecycle-test.txt", headers=auth_headers)
        data = response.json()
        assert data['content'] == new_content
        
        # 4. Delete file
        current_etag = response.headers.get("etag") or response.headers.get("ETag")
        delete_request = {"message": "Delete file"}
        headers = {**auth_headers, "If-Match": current_etag}
        
        response = test_client.request("DELETE", "/files/lifecycle-test.txt", json=delete_request, headers=headers)
        assert response.status_code == 200
        assert not file_path.exists()
    
    def test_concurrent_modifications(self, test_client, auth_headers, temp_repo):
        """Test handling of concurrent modifications."""
        # Create initial file
        test_file = temp_repo / "concurrent-test.txt"
        test_file.write_text("Initial content")
        
        # Get initial ETag
        response = test_client.get("/files/concurrent-test.txt", headers=auth_headers)
        initial_etag = response.headers.get("etag") or response.headers.get("ETag")
        
        # Simulate first modification
        content1 = "First modification"
        content_base641 = base64.b64encode(content1.encode('utf-8')).decode('ascii')
        
        request_data1 = {
            "message": "First modification",
            "content_base64": content_base641
        }
        
        headers1 = {**auth_headers, "If-Match": initial_etag}
        response1 = test_client.put("/files/concurrent-test.txt", json=request_data1, headers=headers1)
        assert response1.status_code == 200
        
        # Try second modification with old ETag (should fail)
        content2 = "Second modification"
        content_base642 = base64.b64encode(content2.encode('utf-8')).decode('ascii')
        
        request_data2 = {
            "message": "Second modification",
            "content_base64": content_base642
        }
        
        headers2 = {**auth_headers, "If-Match": initial_etag}  # Using old ETag
        response2 = test_client.put("/files/concurrent-test.txt", json=request_data2, headers=headers2)
        assert response2.status_code == 412  # Precondition Failed
        
        # Verify first modification succeeded
        response = test_client.get("/files/concurrent-test.txt", headers=auth_headers)
        data = response.json()
        assert data['content'] == content1
