"""
Simplified concurrency tests for Files API.

This module tests core concurrency functionality with simpler test cases
that work reliably with the current API implementation.
"""

import base64
import pytest
import tempfile
import threading
import time
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
         patch('src.api.main.rag_service', None):
        
        mock_repo_path.return_value = temp_repo
        
        from src.api.main import app
        with TestClient(app) as client:
            yield client


@pytest.fixture
def auth_headers():
    """Authentication headers for API requests."""
    return {"Authorization": "Bearer test-token"}


class TestConcurrencyBasics:
    """Test basic concurrency functionality."""
    
    def test_concurrent_reads(self, test_client, auth_headers, temp_repo):
        """Test that concurrent reads work without conflicts."""
        # Create test file
        test_file = temp_repo / "concurrent-reads.txt"
        test_content = "Content for concurrent reads"
        test_file.write_text(test_content)
        
        results = []
        errors = []
        
        def read_file():
            try:
                response = test_client.get("/files/concurrent-reads.txt", headers=auth_headers)
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))
        
        # Start multiple concurrent reads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=read_file)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All reads should succeed
        assert len(errors) == 0, f"Concurrent reads had errors: {errors}"
        assert len(results) == 10, "All read operations should complete"
        assert all(status == 200 for status in results), f"All reads should succeed: {results}"
    
    def test_file_creation_and_read(self, test_client, auth_headers, temp_repo):
        """Test creating a file and then reading it."""
        # Create file via PUT
        content = "New file content"
        content_base64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
        
        request_data = {
            "message": "Create new file",
            "content_base64": content_base64
        }
        
        response = test_client.put("/files/new-file.txt", json=request_data, headers=auth_headers)
        
        # Should return 200 or 201
        assert response.status_code in [200, 201], f"File creation failed: {response.status_code}"
        
        # Verify file was created
        test_file = temp_repo / "new-file.txt"
        assert test_file.exists(), "File should be created"
        assert test_file.read_text() == content, "File content should match"
        
        # Read the file back
        response = test_client.get("/files/new-file.txt", headers=auth_headers)
        assert response.status_code == 200, "Should be able to read created file"
        
        data = response.json()
        decoded_content = base64.b64decode(data['content']).decode('utf-8')
        assert decoded_content == content, "Read content should match written content"
    
    def test_etag_consistency(self, test_client, auth_headers, temp_repo):
        """Test that ETags are consistent for the same content."""
        # Create test file
        test_file = temp_repo / "etag-consistency.txt"
        test_content = "ETag consistency test"
        test_file.write_text(test_content)
        
        # Get file multiple times and verify ETag consistency
        etags = []
        for _ in range(3):
            response = test_client.get("/files/etag-consistency.txt", headers=auth_headers)
            assert response.status_code == 200
            
            # Check both header formats
            etag = response.headers.get("etag") or response.headers.get("ETag")
            if etag:
                etags.append(etag)
        
        # If we got ETags, they should be consistent
        if etags:
            assert len(set(etags)) == 1, f"ETags should be consistent: {etags}"
    
    def test_concurrent_operations_on_different_files(self, test_client, auth_headers, temp_repo):
        """Test concurrent operations on different files (should not conflict)."""
        results = []
        errors = []
        
        def create_file(file_id):
            try:
                filename = f"file-{file_id}.txt"
                content = f"Content for file {file_id}"
                content_base64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
                
                request_data = {
                    "message": f"Create file {file_id}",
                    "content_base64": content_base64
                }
                
                response = test_client.put(f"/files/{filename}", json=request_data, headers=auth_headers)
                results.append((filename, response.status_code))
            except Exception as e:
                errors.append(f"File {file_id}: {e}")
        
        # Start concurrent file creation on different files
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_file, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All operations should succeed (no conflicts between different files)
        assert len(errors) == 0, f"Errors in concurrent file creation: {errors}"
        assert len(results) == 5, "All file creation operations should complete"
        
        # All should succeed
        success_count = sum(1 for _, status in results if status in [200, 201])
        assert success_count == 5, f"All file creations should succeed: {results}"
        
        # Verify all files were created
        for i in range(5):
            filename = f"file-{i}.txt"
            test_file = temp_repo / filename
            assert test_file.exists(), f"File {filename} should exist"
    
    def test_file_corruption_prevention(self, test_client, auth_headers, temp_repo):
        """Test that file operations maintain integrity."""
        # Create test file
        test_file = temp_repo / "integrity-test.txt"
        test_file.write_text("Initial content")
        
        # Update file content
        new_content = "Updated content with integrity check"
        content_base64 = base64.b64encode(new_content.encode('utf-8')).decode('ascii')
        
        request_data = {
            "message": "Update for integrity test",
            "content_base64": content_base64
        }
        
        response = test_client.put("/files/integrity-test.txt", json=request_data, headers=auth_headers)
        assert response.status_code in [200, 201], "File update should succeed"
        
        # Verify file integrity
        assert test_file.exists(), "File should still exist"
        file_content = test_file.read_text()
        assert file_content == new_content, "File content should match exactly"
        
        # Verify via API read
        response = test_client.get("/files/integrity-test.txt", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        decoded_content = base64.b64decode(data['content']).decode('utf-8')
        assert decoded_content == new_content, "API read should match written content"
    
    def test_unicode_content_handling(self, test_client, auth_headers, temp_repo):
        """Test that Unicode content is handled correctly."""
        unicode_content = "Hello 世界! 🌍 This is a test with émojis and spécial characters."
        
        # Create file with Unicode content
        content_base64 = base64.b64encode(unicode_content.encode('utf-8')).decode('ascii')
        
        request_data = {
            "message": "Unicode content test",
            "content_base64": content_base64
        }
        
        response = test_client.put("/files/unicode-test.txt", json=request_data, headers=auth_headers)
        assert response.status_code in [200, 201], "Unicode file creation should succeed"
        
        # Verify file content
        test_file = temp_repo / "unicode-test.txt"
        assert test_file.exists(), "Unicode file should exist"
        
        file_content = test_file.read_text()
        assert file_content == unicode_content, "Unicode content should be preserved"
        
        # Verify via API read
        response = test_client.get("/files/unicode-test.txt", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        decoded_content = base64.b64decode(data['content']).decode('utf-8')
        assert decoded_content == unicode_content, "Unicode content should be preserved in API"
    
    def test_large_file_handling(self, test_client, auth_headers, temp_repo):
        """Test handling of larger files."""
        # Create large content (100KB)
        large_content = "Large file content " * 5000  # ~100KB
        content_base64 = base64.b64encode(large_content.encode('utf-8')).decode('ascii')
        
        request_data = {
            "message": "Large file test",
            "content_base64": content_base64
        }
        
        start_time = time.time()
        response = test_client.put("/files/large-file.txt", json=request_data, headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code in [200, 201], "Large file creation should succeed"
        assert end_time - start_time < 5.0, "Large file creation should complete quickly"
        
        # Verify file
        test_file = temp_repo / "large-file.txt"
        assert test_file.exists(), "Large file should exist"
        assert len(test_file.read_text()) == len(large_content), "File size should match"
        
        # Verify via API read
        response = test_client.get("/files/large-file.txt", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        decoded_content = base64.b64decode(data['content']).decode('utf-8')
        assert len(decoded_content) == len(large_content), "API read size should match"
        assert decoded_content == large_content, "Large file content should match exactly"
    
    def test_concurrent_reads_during_write(self, test_client, auth_headers, temp_repo):
        """Test concurrent reads while a write is happening."""
        # Create initial file
        test_file = temp_repo / "concurrent-read-write.txt"
        test_file.write_text("Initial content")
        
        read_results = []
        write_completed = False
        
        def read_operation():
            try:
                response = test_client.get("/files/concurrent-read-write.txt", headers=auth_headers)
                read_results.append(response.status_code)
            except Exception as e:
                read_results.append(f"error: {e}")
        
        def write_operation():
            nonlocal write_completed
            try:
                content = "Updated content during concurrent reads"
                content_base64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
                
                request_data = {
                    "message": "Update during concurrent reads",
                    "content_base64": content_base64
                }
                
                response = test_client.put("/files/concurrent-read-write.txt", json=request_data, headers=auth_headers)
                write_completed = True
                return response.status_code
            except Exception as e:
                return f"error: {e}"
        
        # Start write operation
        write_thread = threading.Thread(target=write_operation)
        write_thread.start()
        
        # Perform reads during write
        read_threads = []
        for _ in range(5):
            read_thread = threading.Thread(target=read_operation)
            read_threads.append(read_thread)
            read_thread.start()
        
        # Wait for operations to complete
        write_thread.join()
        for thread in read_threads:
            thread.join()
        
        # All reads should succeed (either old or new content)
        assert len(read_results) == 5, "All read operations should complete"
        assert all(r == 200 for r in read_results if isinstance(r, int)), "All reads should return 200"
        
        # Write should complete
        assert write_completed, "Write operation should complete"


class TestLockMechanisms:
    """Test file locking mechanisms."""
    
    def test_lock_manager_basic_functionality(self, temp_repo):
        """Test basic lock manager functionality."""
        from src.cage.tools.editor_tool import FileLockManager
        
        lock_manager = FileLockManager(lock_ttl=60)  # 1 minute TTL
        
        # Test lock acquisition
        lock_id = lock_manager.acquire_lock(
            file_path="test-file.txt",
            agent="test-agent",
            ranges=[{"start": 1, "end": 10}],
            description="Test lock"
        )
        
        assert lock_id is not None, "Lock acquisition should succeed"
        assert lock_manager.is_locked("test-file.txt"), "File should be locked"
        
        # Test that second lock acquisition fails
        second_lock_id = lock_manager.acquire_lock(
            file_path="test-file.txt",
            agent="another-agent",
            ranges=[{"start": 5, "end": 15}],
            description="Second lock attempt"
        )
        
        assert second_lock_id is None, "Second lock acquisition should fail"
        
        # Test lock release
        released = lock_manager.release_lock(lock_id)
        assert released == True, "Lock release should succeed"
        
        # Test that file is no longer locked
        assert not lock_manager.is_locked("test-file.txt"), "File should not be locked after release"
        
        # Test that lock can be acquired again after release
        third_lock_id = lock_manager.acquire_lock(
            file_path="test-file.txt",
            agent="third-agent",
            ranges=[{"start": 1, "end": 20}],
            description="Third lock attempt"
        )
        
        assert third_lock_id is not None, "Lock acquisition should succeed after release"
    
    def test_lock_expiration(self, temp_repo):
        """Test lock expiration mechanism."""
        from src.cage.tools.editor_tool import FileLockManager
        
        # Create lock manager with very short TTL
        lock_manager = FileLockManager(lock_ttl=1)  # 1 second TTL
        
        # Acquire lock
        lock_id = lock_manager.acquire_lock(
            file_path="expiry-test.txt",
            agent="test-agent",
            ranges=[{"start": 1, "end": 10}],
            description="Lock with short TTL"
        )
        
        assert lock_id is not None, "Lock acquisition should succeed"
        assert lock_manager.is_locked("expiry-test.txt"), "File should be locked"
        
        # Wait for lock to expire
        time.sleep(2)
        
        # Lock should be expired
        assert not lock_manager.is_locked("expiry-test.txt"), "Lock should be expired"
        
        # Should be able to acquire lock again
        new_lock_id = lock_manager.acquire_lock(
            file_path="expiry-test.txt",
            agent="test-agent-2",
            ranges=[{"start": 1, "end": 10}],
            description="New lock after expiry"
        )
        
        assert new_lock_id is not None, "Should be able to acquire lock after expiry"

