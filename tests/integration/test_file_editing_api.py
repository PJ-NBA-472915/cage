"""
Integration tests for the new File Editing API endpoints.

This module tests the optimistic concurrency file editing API with ETag support,
JSON Patch operations, audit trail, and detailed logging.
"""

import base64
import json
import os
import tempfile
import time
from pathlib import Path
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.cage.utils.file_editing_utils import ETagManager, PathValidator, AuditTrailManager


@pytest.fixture
def test_repo_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_client(test_repo_dir):
    """Create a test client with temporary repository."""
    # Set environment variables for testing
    os.environ["REPO_PATH"] = str(test_repo_dir)
    os.environ["POD_TOKEN"] = "test-token"
    
    # Create test file
    test_file = test_repo_dir / "test.json"
    test_content = '{"name": "test", "value": 42}'
    test_file.write_text(test_content)
    
    with TestClient(app) as client:
        yield client


@pytest.fixture
def auth_headers():
    """Authentication headers for test requests."""
    return {"Authorization": "Bearer test-token"}


class TestFileEditingAPI:
    """Test suite for the File Editing API endpoints."""
    
    def test_get_file_success(self, test_client, auth_headers):
        """Test successful file retrieval with ETag."""
        response = test_client.get("/files/test.json", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "path" in data
        assert "sha" in data
        assert "size" in data
        assert "encoding" in data
        assert "content" in data
        assert "last_modified" in data
        
        # Verify content
        assert data["path"] == "test.json"
        assert data["encoding"] == "base64"
        assert data["size"] > 0
        
        # Decode and verify content
        decoded_content = base64.b64decode(data["content"]).decode('utf-8')
        assert decoded_content == '{"name": "test", "value": 42}'
    
    def test_get_file_raw_mode(self, test_client, auth_headers):
        """Test file retrieval in raw mode."""
        response = test_client.get("/files/test.json?raw=true", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"
        assert "ETag" in response.headers
        
        # Verify raw content
        content = response.content.decode('utf-8')
        assert content == '{"name": "test", "value": 42}'
    
    def test_get_file_not_found(self, test_client, auth_headers):
        """Test file retrieval for non-existent file."""
        response = test_client.get("/files/nonexistent.json", headers=auth_headers)
        
        assert response.status_code == 404
        assert "File not found" in response.json()["detail"]
    
    def test_get_file_path_traversal(self, test_client, auth_headers):
        """Test path traversal protection."""
        response = test_client.get("/files/../../../etc/passwd", headers=auth_headers)
        
        assert response.status_code == 400
        assert "directory traversal" in response.json()["detail"]
    
    def test_put_file_create_new(self, test_client, auth_headers):
        """Test creating a new file with PUT."""
        new_content = '{"name": "new", "value": 100}'
        content_base64 = base64.b64encode(new_content.encode('utf-8')).decode('ascii')
        
        request_data = {
            "message": "Create new file",
            "content_base64": content_base64
        }
        
        response = test_client.put(
            "/files/new.json",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200  # PUT returns 200 for updates, 201 for creates
        data = response.json()
        
        # Check response structure
        assert "path" in data
        assert "sha_before" in data
        assert "sha_after" in data
        assert "commit" in data
        
        # Verify file was created
        new_file = Path(os.environ["REPO_PATH"]) / "new.json"
        assert new_file.exists()
        assert new_file.read_text() == new_content
    
    def test_put_file_update_existing(self, test_client, auth_headers):
        """Test updating an existing file with ETag validation."""
        # First, get the current ETag
        get_response = test_client.get("/files/test.json", headers=auth_headers)
        assert get_response.status_code == 200
        
        # Update the file
        new_content = '{"name": "updated", "value": 999}'
        content_base64 = base64.b64encode(new_content.encode('utf-8')).decode('ascii')
        
        request_data = {
            "message": "Update existing file",
            "content_base64": content_base64
        }
        
        response = test_client.put(
            "/files/test.json",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify file was updated
        updated_file = Path(os.environ["REPO_PATH"]) / "test.json"
        assert updated_file.read_text() == new_content
    
    def test_put_file_etag_mismatch(self, test_client, auth_headers):
        """Test PUT with incorrect ETag fails with 412."""
        # Use wrong ETag
        wrong_etag = 'W/"wrong-etag"'
        
        new_content = '{"name": "should-fail", "value": 0}'
        content_base64 = base64.b64encode(new_content.encode('utf-8')).decode('ascii')
        
        request_data = {
            "message": "Should fail due to wrong ETag",
            "content_base64": content_base64
        }
        
        headers = {**auth_headers, "If-Match": wrong_etag}
        response = test_client.put(
            "/files/test.json",
            json=request_data,
            headers=headers
        )
        
        assert response.status_code == 412
        assert "Precondition failed" in response.json()["detail"]
    
    def test_patch_file_json_patch(self, test_client, auth_headers):
        """Test JSON Patch operations."""
        # First, get the current ETag
        get_response = test_client.get("/files/test.json", headers=auth_headers)
        assert get_response.status_code == 200
        
        # Apply JSON Patch
        patch_operations = [
            {"op": "replace", "path": "/value", "value": 999},
            {"op": "add", "path": "/new_field", "value": "added"}
        ]
        
        request_data = {"operations": patch_operations}
        
        response = test_client.patch(
            "/files/test.json",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify file was patched
        patched_file = Path(os.environ["REPO_PATH"]) / "test.json"
        patched_content = json.loads(patched_file.read_text())
        
        assert patched_content["value"] == 999
        assert patched_content["new_field"] == "added"
        assert patched_content["name"] == "test"  # Should remain unchanged
    
    def test_patch_file_invalid_json(self, test_client, auth_headers):
        """Test JSON PATCH on non-JSON file fails appropriately."""
        # Create a non-JSON file
        text_file = Path(os.environ["REPO_PATH"]) / "test.txt"
        text_file.write_text("This is not JSON")
        
        # First get the ETag
        get_response = test_client.get("/files/test.txt", headers=auth_headers)
        assert get_response.status_code == 200
        current_etag = get_response.headers.get("etag") or get_response.headers.get("ETag")
        
        patch_operations = [{"op": "replace", "path": "/value", "value": 999}]
        request_data = {"operations": patch_operations}
        
        patch_headers = {**auth_headers, "If-Match": current_etag}
        response = test_client.patch(
            "/files/test.txt",
            json=request_data,
            headers=patch_headers
        )
        
        assert response.status_code == 422
        assert "JSON Patch not supported" in response.json()["detail"]
    
    def test_patch_file_invalid_operations(self, test_client, auth_headers):
        """Test PATCH with invalid operations fails."""
        invalid_operations = [
            {"op": "invalid", "path": "/value", "value": 999}  # Invalid operation
        ]
        
        request_data = {"operations": invalid_operations}
        
        response = test_client.patch(
            "/files/test.json",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422
        assert "Invalid JSON Patch operations" in response.json()["detail"]
    
    def test_delete_file_success(self, test_client, auth_headers):
        """Test successful file deletion."""
        # First, get the current ETag
        get_response = test_client.get("/files/test.json", headers=auth_headers)
        assert get_response.status_code == 200
        
        # Delete the file
        request_data = {"message": "Delete test file"}
        
        response = test_client.delete(
            "/files/test.json",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "deleted successfully" in data["message"]
        
        # Verify file was deleted
        deleted_file = Path(os.environ["REPO_PATH"]) / "test.json"
        assert not deleted_file.exists()
    
    def test_delete_file_not_found(self, test_client, auth_headers):
        """Test deletion of non-existent file."""
        request_data = {"message": "Delete non-existent file"}
        
        response = test_client.delete(
            "/files/nonexistent.json",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "File not found" in response.json()["detail"]
    
    def test_delete_file_etag_mismatch(self, test_client, auth_headers):
        """Test DELETE with incorrect ETag fails with 412."""
        wrong_etag = 'W/"wrong-etag"'
        
        request_data = {"message": "Should fail due to wrong ETag"}
        headers = {**auth_headers, "If-Match": wrong_etag}
        
        response = test_client.delete(
            "/files/test.json",
            json=request_data,
            headers=headers
        )
        
        assert response.status_code == 412
        assert "Precondition failed" in response.json()["detail"]
    
    def test_audit_trail_query(self, test_client, auth_headers):
        """Test audit trail querying."""
        # Perform some operations to generate audit entries
        get_response = test_client.get("/files/test.json", headers=auth_headers)
        assert get_response.status_code == 200
        
        # Query audit trail
        response = test_client.get("/audit", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "items" in data
        assert "next_cursor" in data
        assert isinstance(data["items"], list)
    
    def test_audit_trail_filtering(self, test_client, auth_headers):
        """Test audit trail filtering by path."""
        # Perform operations
        test_client.get("/files/test.json", headers=auth_headers)
        
        # Query with path filter
        response = test_client.get("/audit?path=test.json", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned entries should match the path filter
        for entry in data["items"]:
            assert "test.json" in entry["path"]
    
    def test_audit_trail_limit(self, test_client, auth_headers):
        """Test audit trail limit parameter."""
        response = test_client.get("/audit?limit=5", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["items"]) <= 5
    
    def test_audit_trail_invalid_limit(self, test_client, auth_headers):
        """Test audit trail with invalid limit."""
        response = test_client.get("/audit?limit=0", headers=auth_headers)
        
        assert response.status_code == 400
        assert "between 1 and 1000" in response.json()["detail"]
        
        response = test_client.get("/audit?limit=2000", headers=auth_headers)
        
        assert response.status_code == 400
        assert "between 1 and 1000" in response.json()["detail"]
    
    def test_audit_trail_invalid_timestamp(self, test_client, auth_headers):
        """Test audit trail with invalid timestamp format."""
        response = test_client.get("/audit?since=invalid-timestamp", headers=auth_headers)
        
        assert response.status_code == 400
        assert "Invalid since timestamp format" in response.json()["detail"]
    
    def test_authentication_required(self, test_client):
        """Test that authentication is required for all endpoints."""
        endpoints = [
            ("GET", "/files/test.json"),
            ("PUT", "/files/test.json"),
            ("PATCH", "/files/test.json"),
            ("DELETE", "/files/test.json"),
            ("GET", "/audit")
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = test_client.get(endpoint)
            elif method == "PUT":
                response = test_client.put(endpoint, json={})
            elif method == "PATCH":
                response = test_client.patch(endpoint, json={})
            elif method == "DELETE":
                response = test_client.delete(endpoint, json={})
            
            assert response.status_code == 401
            assert "Invalid token" in response.json()["detail"]
    
    def test_concurrent_operations_etag_protection(self, test_client, auth_headers):
        """Test that ETag prevents concurrent modification issues."""
        # Get initial file state
        get_response1 = test_client.get("/files/test.json", headers=auth_headers)
        assert get_response1.status_code == 200
        
        # Simulate first client modifying the file
        new_content1 = '{"name": "client1", "value": 100}'
        content_base64_1 = base64.b64encode(new_content1.encode('utf-8')).decode('ascii')
        
        request_data1 = {
            "message": "Client 1 update",
            "content_base64": content_base64_1
        }
        
        response1 = test_client.put(
            "/files/test.json",
            json=request_data1,
            headers=auth_headers
        )
        assert response1.status_code == 200
        
        # Simulate second client trying to modify with stale ETag
        # (In real scenario, second client would have cached the old ETag)
        old_etag = 'W/"old-etag"'
        new_content2 = '{"name": "client2", "value": 200}'
        content_base64_2 = base64.b64encode(new_content2.encode('utf-8')).decode('ascii')
        
        request_data2 = {
            "message": "Client 2 update",
            "content_base64": content_base64_2
        }
        
        headers_with_old_etag = {**auth_headers, "If-Match": old_etag}
        response2 = test_client.put(
            "/files/test.json",
            json=request_data2,
            headers=headers_with_old_etag
        )
        
        # Should fail with 412 Precondition Failed
        assert response2.status_code == 412
        assert "Precondition failed" in response2.json()["detail"]
        
        # Verify first client's changes are still there
        final_file = Path(os.environ["REPO_PATH"]) / "test.json"
        final_content = json.loads(final_file.read_text())
        assert final_content["name"] == "client1"
        assert final_content["value"] == 100


class TestETagManager:
    """Test suite for ETag management utilities."""
    
    def test_etag_generation(self):
        """Test ETag generation."""
        content = "test content"
        file_path = "/test/file.json"
        
        etag = ETagManager.generate_etag(content, file_path)
        
        assert etag.startswith('W/"')
        assert etag.endswith('"')
        assert len(etag) > 10  # Should have some hash content
    
    def test_etag_consistency(self):
        """Test that ETag is consistent for same content."""
        content = "test content"
        file_path = "/test/file.json"
        
        etag1 = ETagManager.generate_etag(content, file_path)
        etag2 = ETagManager.generate_etag(content, file_path)
        
        assert etag1 == etag2
    
    def test_etag_different_for_different_content(self):
        """Test that ETag is different for different content."""
        content1 = "test content 1"
        content2 = "test content 2"
        file_path = "/test/file.json"
        
        etag1 = ETagManager.generate_etag(content1, file_path)
        etag2 = ETagManager.generate_etag(content2, file_path)
        
        assert etag1 != etag2
    
    def test_sha_generation(self):
        """Test SHA generation."""
        content = "test content"
        
        sha = ETagManager.generate_sha(content)
        
        assert len(sha) == 64  # SHA-256 hex length
        assert sha.isalnum()
    
    def test_etag_validation(self):
        """Test ETag validation."""
        etag1 = 'W/"abc123"'
        etag2 = 'W/"abc123"'
        etag3 = 'W/"def456"'
        
        assert ETagManager.validate_etag(etag1, etag2) is True
        assert ETagManager.validate_etag(etag1, etag3) is False


class TestPathValidator:
    """Test suite for path validation utilities."""
    
    def test_normalize_path_success(self):
        """Test successful path normalization."""
        validator = PathValidator("/repo/root")
        
        normalized = validator.normalize_path("test/file.json")
        
        assert str(normalized).endswith("test/file.json")
    
    def test_normalize_path_directory_traversal(self):
        """Test that directory traversal is blocked."""
        validator = PathValidator("/repo/root")
        
        with pytest.raises(ValueError, match="directory traversal"):
            validator.normalize_path("../../../etc/passwd")
    
    def test_normalize_path_absolute_path(self):
        """Test that absolute paths are blocked."""
        validator = PathValidator("/repo/root")
        
        with pytest.raises(ValueError, match="directory traversal"):
            validator.normalize_path("/absolute/path")
    
    def test_is_allowed_extension(self):
        """Test extension validation."""
        validator = PathValidator("/repo/root")
        
        assert validator.is_allowed_extension("test.json", [".json", ".md"]) is True
        assert validator.is_allowed_extension("test.txt", [".json", ".md"]) is False
        assert validator.is_allowed_extension("test.JSON", [".json", ".md"]) is True  # Case insensitive


class TestAuditTrailManager:
    """Test suite for audit trail management."""
    
    def test_record_operation(self, test_repo_dir):
        """Test recording audit operations."""
        manager = AuditTrailManager(str(test_repo_dir))
        
        entry_id = manager.record_operation(
            actor="test-actor",
            method="PUT",
            path="test.json",
            base_etag='W/"old"',
            new_etag='W/"new"',
            sha_before="old-sha",
            sha_after="new-sha",
            message="Test operation"
        )
        
        assert entry_id is not None
        assert len(entry_id) > 0
    
    def test_query_audit_trail(self, test_repo_dir):
        """Test querying audit trail."""
        manager = AuditTrailManager(str(test_repo_dir))
        
        # Record some operations
        manager.record_operation("actor1", "GET", "file1.json", message="Read file1")
        manager.record_operation("actor2", "PUT", "file2.json", message="Write file2")
        manager.record_operation("actor1", "DELETE", "file1.json", message="Delete file1")
        
        # Query all entries
        entries = manager.query_audit_trail()
        assert len(entries) == 3
        
        # Query by actor
        entries = manager.query_audit_trail(actor="actor1")
        assert len(entries) == 2
        
        # Query by path
        entries = manager.query_audit_trail(path="file1.json")
        assert len(entries) == 2
        
        # Query with limit
        entries = manager.query_audit_trail(limit=2)
        assert len(entries) == 2


class TestJsonPatchValidator:
    """Test suite for JSON Patch validation."""
    
    def test_validate_patch_operations_valid(self):
        """Test validation of valid patch operations."""
        from src.cage.utils.file_editing_utils import JsonPatchValidator
        
        valid_ops = [
            {"op": "replace", "path": "/value", "value": 999},
            {"op": "add", "path": "/new_field", "value": "added"}
        ]
        
        assert JsonPatchValidator.validate_patch_operations(valid_ops) is True
    
    def test_validate_patch_operations_invalid(self):
        """Test validation of invalid patch operations."""
        from src.cage.utils.file_editing_utils import JsonPatchValidator
        
        invalid_ops = [
            {"op": "invalid", "path": "/value", "value": 999}  # Invalid operation
        ]
        
        assert JsonPatchValidator.validate_patch_operations(invalid_ops) is False
    
    def test_apply_patch_replace(self):
        """Test applying replace patch operation."""
        from src.cage.utils.file_editing_utils import JsonPatchValidator
        
        content = '{"name": "test", "value": 42}'
        operations = [{"op": "replace", "path": "/value", "value": 999}]
        
        result = JsonPatchValidator.apply_patch(content, operations)
        parsed = json.loads(result)
        
        assert parsed["value"] == 999
        assert parsed["name"] == "test"  # Should remain unchanged
    
    def test_apply_patch_add(self):
        """Test applying add patch operation."""
        from src.cage.utils.file_editing_utils import JsonPatchValidator
        
        content = '{"name": "test"}'
        operations = [{"op": "add", "path": "/value", "value": 42}]
        
        result = JsonPatchValidator.apply_patch(content, operations)
        parsed = json.loads(result)
        
        assert parsed["value"] == 42
        assert parsed["name"] == "test"
    
    def test_apply_patch_remove(self):
        """Test applying remove patch operation."""
        from src.cage.utils.file_editing_utils import JsonPatchValidator
        
        content = '{"name": "test", "value": 42}'
        operations = [{"op": "remove", "path": "/value"}]
        
        result = JsonPatchValidator.apply_patch(content, operations)
        parsed = json.loads(result)
        
        assert "value" not in parsed
        assert parsed["name"] == "test"
    
    def test_apply_patch_invalid_json(self):
        """Test applying patch to invalid JSON fails."""
        from src.cage.utils.file_editing_utils import JsonPatchValidator
        
        invalid_json = '{"name": "test", "value": 42'  # Missing closing brace
        operations = [{"op": "replace", "path": "/value", "value": 999}]
        
        with pytest.raises(ValueError, match="Failed to apply JSON patch"):
            JsonPatchValidator.apply_patch(invalid_json, operations)


class TestFileTypeSupport:
    """Test suite for multi-file-type support."""
    
    def test_text_patch_python_file(self, test_client, auth_headers):
        """Test text patch on Python file."""
        # Create a Python file
        py_file = Path(os.environ["REPO_PATH"]) / "test.py"
        py_content = '''def hello():
    print("Hello, World!")

if __name__ == "__main__":
    hello()
'''
        py_file.write_text(py_content)
        
        # Get current ETag
        get_response = test_client.get("/files/test.py", headers=auth_headers)
        assert get_response.status_code == 200
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
        text_patch_request = {
            "content": new_content,
            "message": "Updated Python file"
        }
        
        patch_headers = {**auth_headers, "If-Match": current_etag}
        response = test_client.patch("/files/test.py", json=text_patch_request, headers=patch_headers)
        
        assert response.status_code == 200
        
        # Verify changes
        updated_content = py_file.read_text()
        assert "new_function" in updated_content
        assert "Updated Python file" in updated_content
    
    def test_line_patch_text_file(self, test_client, auth_headers):
        """Test line-based patch on text file."""
        # Create a text file
        txt_file = Path(os.environ["REPO_PATH"]) / "test.txt"
        txt_content = "Line 1\nLine 2\nLine 3\nLine 4"
        txt_file.write_text(txt_content)
        
        # Get current ETag
        get_response = test_client.get("/files/test.txt", headers=auth_headers)
        assert get_response.status_code == 200
        current_etag = get_response.headers.get("etag") or get_response.headers.get("ETag")
        
        # Apply line patch
        line_patch_request = {
            "operations": [
                {"op": "replace_line", "line_number": 2, "content": "Line 2: Updated"},
                {"op": "insert_at", "line_number": 4, "content": "Line 3.5: Inserted"},
                {"op": "add_line", "content": "Line 5: Added at end"}
            ],
            "message": "Applied line operations"
        }
        
        patch_headers = {**auth_headers, "If-Match": current_etag}
        response = test_client.patch("/files/test.txt", json=line_patch_request, headers=patch_headers)
        
        assert response.status_code == 200
        
        # Verify changes
        updated_content = txt_file.read_text()
        lines = updated_content.strip().split('\n')
        assert "Line 2: Updated" in lines[1]
        assert "Line 3.5: Inserted" in lines[3]
        assert "Line 5: Added at end" in lines[5]
    
    def test_markdown_text_patch(self, test_client, auth_headers):
        """Test text patch on Markdown file."""
        # Create a markdown file
        md_file = Path(os.environ["REPO_PATH"]) / "test.md"
        md_content = """# Test

This is a test.

## Section 1

Content here.
"""
        md_file.write_text(md_content)
        
        # Get current ETag
        get_response = test_client.get("/files/test.md", headers=auth_headers)
        assert get_response.status_code == 200
        current_etag = get_response.headers.get("etag") or get_response.headers.get("ETag")
        
        # Apply text patch
        new_content = """# Updated Test

This is an updated test.

## Section 1

Updated content here.

## New Section

This is a new section.
"""
        text_patch_request = {
            "content": new_content,
            "message": "Updated markdown file"
        }
        
        patch_headers = {**auth_headers, "If-Match": current_etag}
        response = test_client.patch("/files/test.md", json=text_patch_request, headers=patch_headers)
        
        assert response.status_code == 200
        
        # Verify changes
        updated_content = md_file.read_text()
        assert "Updated Test" in updated_content
        assert "New Section" in updated_content
    
    def test_yaml_line_patch(self, test_client, auth_headers):
        """Test line patch on YAML file."""
        # Create a YAML file
        yaml_file = Path(os.environ["REPO_PATH"]) / "test.yaml"
        yaml_content = """name: test
version: 1.0
settings:
  debug: true
  port: 8080
"""
        yaml_file.write_text(yaml_content)
        
        # Get current ETag
        get_response = test_client.get("/files/test.yaml", headers=auth_headers)
        assert get_response.status_code == 200
        current_etag = get_response.headers.get("etag") or get_response.headers.get("ETag")
        
        # Apply line patch
        line_patch_request = {
            "operations": [
                {"op": "replace_line", "line_number": 2, "content": "version: 2.0"},
                {"op": "replace_line", "line_number": 5, "content": "  port: 9090"}
            ],
            "message": "Updated YAML configuration"
        }
        
        patch_headers = {**auth_headers, "If-Match": current_etag}
        response = test_client.patch("/files/test.yaml", json=line_patch_request, headers=patch_headers)
        
        assert response.status_code == 200
        
        # Verify changes
        updated_content = yaml_file.read_text()
        assert "version: 2.0" in updated_content
        assert "port: 9090" in updated_content
    
    def test_file_type_detection(self):
        """Test file type detection utility."""
        from src.cage.utils.file_editing_utils import FileTypeDetector
        
        # Test various file types
        assert FileTypeDetector.get_file_type("test.json") == "json"
        assert FileTypeDetector.get_file_type("script.py") == "code"
        assert FileTypeDetector.get_file_type("readme.md") == "markdown"
        assert FileTypeDetector.get_file_type("config.yaml") == "yaml"
        assert FileTypeDetector.get_file_type("data.xml") == "xml"
        assert FileTypeDetector.get_file_type("log.txt") == "text"
        
        # Test patch capability detection
        assert FileTypeDetector.can_apply_json_patch("json") == True
        assert FileTypeDetector.can_apply_json_patch("code") == False
        
        assert FileTypeDetector.can_apply_line_patch("text") == True
        assert FileTypeDetector.can_apply_line_patch("code") == True
        assert FileTypeDetector.can_apply_line_patch("json") == False
    
    def test_line_patch_validator(self):
        """Test line patch validator."""
        from src.cage.utils.file_editing_utils import LinePatchValidator
        
        # Test valid operations
        valid_ops = [
            {"op": "replace_line", "line_number": 1, "content": "new content"},
            {"op": "add_line", "content": "new line"},
            {"op": "insert_at", "line_number": 2, "content": "inserted"}
        ]
        assert LinePatchValidator.validate_line_operations(valid_ops) == True
        
        # Test invalid operations
        invalid_ops = [
            {"op": "invalid_op", "line_number": 1}
        ]
        assert LinePatchValidator.validate_line_operations(invalid_ops) == False
        
        # Test line patch application
        content = "Line 1\nLine 2\nLine 3"
        operations = [
            {"op": "replace_line", "line_number": 2, "content": "Updated Line 2"},
            {"op": "add_line", "content": "Line 4"}
        ]
        
        result = LinePatchValidator.apply_line_patch(content, operations)
        lines = result.strip().split('\n')
        assert "Updated Line 2" in lines[1]
        assert "Line 4" in lines[3]
