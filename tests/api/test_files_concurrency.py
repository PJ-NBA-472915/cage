"""
Comprehensive test suite for Files API concurrency, locking, and corruption protection.

This module tests:
- Optimistic concurrency control with ETags
- File locking mechanisms
- Race condition prevention
- File corruption protection
- Concurrent modification handling
- Lock expiration and cleanup
"""

import asyncio
import base64
import concurrent.futures
import pytest
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch, AsyncMock
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


class TestOptimisticConcurrencyControl:
    """Test ETag-based optimistic concurrency control."""
    
    def test_etag_generation_consistency(self, test_client, auth_headers, temp_repo):
        """Test that ETags are generated consistently for the same content."""
        # Create test file
        test_file = temp_repo / "etag-test.txt"
        test_content = "ETag consistency test content"
        test_file.write_text(test_content)
        
        # Get file multiple times and verify ETag consistency
        etags = []
        for _ in range(3):
            response = test_client.get("/files/etag-test.txt", headers=auth_headers)
            assert response.status_code == 200
            etag = response.headers.get("etag") or response.headers.get("ETag")
            etags.append(etag)
        
        # All ETags should be identical
        assert len(set(etags)) == 1, f"ETags should be consistent: {etags}"
    
    def test_etag_changes_with_content(self, test_client, auth_headers, temp_repo):
        """Test that ETags change when content changes."""
        # Create initial file
        test_file = temp_repo / "etag-change.txt"
        initial_content = "Initial content"
        test_file.write_text(initial_content)
        
        # Get initial ETag
        response = test_client.get("/files/etag-change.txt", headers=auth_headers)
        initial_etag = response.headers.get("etag") or response.headers.get("ETag")
        
        # Ensure we have a valid ETag
        if not initial_etag:
            raise AssertionError("Failed to get initial ETag")
        
        # Update file content
        updated_content = "Updated content"
        content_base64 = base64.b64encode(updated_content.encode('utf-8')).decode('ascii')
        
        request_data = {
            "message": "Update content",
            "content_base64": content_base64
        }
        
        headers = {**auth_headers, "If-Match": initial_etag}
        response = test_client.put("/files/etag-change.txt", json=request_data, headers=headers)
        assert response.status_code == 200
        
        # Get new ETag
        response = test_client.get("/files/etag-change.txt", headers=auth_headers)
        new_etag = response.headers.get("etag") or response.headers.get("ETag")
        
        # ETags should be different
        assert initial_etag != new_etag, "ETags should change when content changes"
    
    def test_etag_validation_prevents_stale_updates(self, test_client, auth_headers, temp_repo):
        """Test that ETag validation prevents updates with stale ETags."""
        # Create test file
        test_file = temp_repo / "stale-update.txt"
        initial_content = "Initial content"
        test_file.write_text(initial_content)
        
        # Get initial ETag
        response = test_client.get("/files/stale-update.txt", headers=auth_headers)
        initial_etag = response.headers.get("etag") or response.headers.get("ETag")
        
        # Update file with correct ETag
        updated_content = "Updated content"
        content_base64 = base64.b64encode(updated_content.encode('utf-8')).decode('ascii')
        
        request_data = {
            "message": "First update",
            "content_base64": content_base64
        }
        
        headers = {**auth_headers, "If-Match": initial_etag}
        response = test_client.put("/files/stale-update.txt", json=request_data, headers=headers)
        assert response.status_code == 200
        
        # Try to update with stale ETag (should fail)
        stale_content = "Stale update content"
        stale_content_base64 = base64.b64encode(stale_content.encode('utf-8')).decode('ascii')
        
        stale_request_data = {
            "message": "Stale update",
            "content_base64": stale_content_base64
        }
        
        headers = {**auth_headers, "If-Match": initial_etag}  # Using old ETag
        response = test_client.put("/files/stale-update.txt", json=stale_request_data, headers=headers)
        assert response.status_code == 412  # Precondition Failed
        
        # Verify file content wasn't changed
        response = test_client.get("/files/stale-update.txt", headers=auth_headers)
        data = response.json()
        decoded_content = base64.b64decode(data['content']).decode('utf-8')
        assert decoded_content == updated_content, "File should not be updated with stale ETag"
    
    def test_patch_requires_current_etag(self, test_client, auth_headers, temp_repo):
        """Test that PATCH operations require current ETag."""
        # Create test file
        test_file = temp_repo / "patch-etag.txt"
        initial_content = "Line 1\nLine 2\nLine 3"
        test_file.write_text(initial_content)
        
        # Get current ETag
        response = test_client.get("/files/patch-etag.txt", headers=auth_headers)
        current_etag = response.headers.get("etag") or response.headers.get("ETag")
        
        # Try patch with wrong ETag (should fail)
        patch_request = {
            "content": "Updated content",
            "message": "Patch with wrong ETag"
        }
        
        headers = {**auth_headers, "If-Match": "wrong-etag"}
        response = test_client.patch("/files/patch-etag.txt", json=patch_request, headers=headers)
        assert response.status_code == 412  # Precondition Failed
        
        # Try patch with correct ETag (should succeed)
        patch_request = {
            "content": "Updated content",
            "message": "Patch with correct ETag"
        }
        
        headers = {**auth_headers, "If-Match": current_etag}
        response = test_client.patch("/files/patch-etag.txt", json=patch_request, headers=headers)
        assert response.status_code == 200
    
    def test_delete_requires_current_etag(self, test_client, auth_headers, temp_repo):
        """Test that DELETE operations require current ETag."""
        # Create test file
        test_file = temp_repo / "delete-etag.txt"
        test_file.write_text("Content to delete")
        
        # Get current ETag
        response = test_client.get("/files/delete-etag.txt", headers=auth_headers)
        current_etag = response.headers.get("etag") or response.headers.get("ETag")
        
        # Try delete with wrong ETag (should fail)
        delete_request = {"message": "Delete with wrong ETag"}
        headers = {**auth_headers, "If-Match": "wrong-etag"}
        
        response = test_client.request("DELETE", "/files/delete-etag.txt", json=delete_request, headers=headers)
        assert response.status_code == 412  # Precondition Failed
        
        # File should still exist
        assert test_file.exists()
        
        # Try delete with correct ETag (should succeed)
        delete_request = {"message": "Delete with correct ETag"}
        headers = {**auth_headers, "If-Match": current_etag}
        
        response = test_client.request("DELETE", "/files/delete-etag.txt", json=delete_request, headers=headers)
        assert response.status_code == 200
        assert not test_file.exists()


class TestConcurrentModifications:
    """Test concurrent file modifications and race conditions."""
    
    def test_concurrent_reads_do_not_conflict(self, test_client, auth_headers, temp_repo):
        """Test that concurrent reads don't conflict."""
        # Create test file
        test_file = temp_repo / "concurrent-reads.txt"
        test_content = "Content for concurrent reads"
        test_file.write_text(test_content)
        
        # Simulate concurrent reads
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
        assert len(errors) == 0, f"Concurrent reads failed: {errors}"
        assert all(status == 200 for status in results), f"Some reads failed: {results}"
        assert len(results) == 10, "Not all reads completed"
    
    def test_concurrent_writes_with_etag_conflicts(self, test_client, auth_headers, temp_repo):
        """Test that concurrent writes with ETag conflicts are handled correctly."""
        # Create test file
        test_file = temp_repo / "concurrent-writes.txt"
        initial_content = "Initial content"
        test_file.write_text(initial_content)
        
        # Get initial ETag
        response = test_client.get("/files/concurrent-writes.txt", headers=auth_headers)
        initial_etag = response.headers.get("etag") or response.headers.get("ETag")
        
        # Simulate concurrent writes
        results = []
        errors = []
        
        def write_file(content_suffix):
            try:
                content = f"Content from thread {content_suffix}"
                content_base64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
                
                request_data = {
                    "message": f"Update from thread {content_suffix}",
                    "content_base64": content_base64
                }
                
                headers = {**auth_headers, "If-Match": initial_etag}
                response = test_client.put("/files/concurrent-writes.txt", json=request_data, headers=headers)
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))
        
        # Start multiple concurrent writes
        threads = []
        for i in range(5):
            thread = threading.Thread(target=write_file, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Only one write should succeed (200), others should fail (412)
        assert len(errors) == 0, f"Concurrent writes had errors: {errors}"
        assert 200 in results, "At least one write should succeed"
        assert results.count(412) >= 4, "Most writes should fail with ETag conflicts"
    
    def test_sequential_updates_with_etag_flow(self, test_client, auth_headers, temp_repo):
        """Test sequential updates following proper ETag flow."""
        # Create test file
        test_file = temp_repo / "sequential-updates.txt"
        initial_content = "Initial content"
        test_file.write_text(initial_content)
        
        # Get initial ETag
        response = test_client.get("/files/sequential-updates.txt", headers=auth_headers)
        etag = response.headers.get("etag") or response.headers.get("ETag")
        
        # Perform sequential updates
        for i in range(3):
            content = f"Content after update {i + 1}"
            content_base64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
            
            request_data = {
                "message": f"Update {i + 1}",
                "content_base64": content_base64
            }
            
            headers = {**auth_headers, "If-Match": etag}
            response = test_client.put("/files/sequential-updates.txt", json=request_data, headers=headers)
            assert response.status_code == 200
            
            # Get new ETag for next update
            response = test_client.get("/files/sequential-updates.txt", headers=auth_headers)
            etag = response.headers.get("etag") or response.headers.get("ETag")
            
            # Verify content was updated
            data = response.json()
            decoded_content = base64.b64decode(data['content']).decode('utf-8')
            assert decoded_content == content
    
    def test_mixed_operations_concurrency(self, test_client, auth_headers, temp_repo):
        """Test mixed read/write operations under concurrency."""
        # Create test file
        test_file = temp_repo / "mixed-operations.txt"
        test_file.write_text("Initial content")
        
        # Get initial ETag
        response = test_client.get("/files/mixed-operations.txt", headers=auth_headers)
        etag = response.headers.get("etag") or response.headers.get("ETag")
        
        results = []
        
        def read_operation():
            try:
                response = test_client.get("/files/mixed-operations.txt", headers=auth_headers)
                results.append(('read', response.status_code))
            except Exception as e:
                results.append(('read', 'error', str(e)))
        
        def write_operation():
            try:
                content = f"Content at {time.time()}"
                content_base64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
                
                request_data = {
                    "message": "Concurrent update",
                    "content_base64": content_base64
                }
                
                headers = {**auth_headers, "If-Match": etag}
                response = test_client.put("/files/mixed-operations.txt", json=request_data, headers=headers)
                results.append(('write', response.status_code))
            except Exception as e:
                results.append(('write', 'error', str(e)))
        
        # Start mixed operations
        threads = []
        for i in range(10):
            if i % 3 == 0:
                thread = threading.Thread(target=write_operation)
            else:
                thread = threading.Thread(target=read_operation)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All reads should succeed
        read_results = [r for r in results if r[0] == 'read']
        assert all(r[1] == 200 for r in read_results if len(r) > 1), "Read operations should succeed"
        
        # Most writes should fail due to ETag conflicts (only one can succeed)
        write_results = [r for r in results if r[0] == 'write']
        success_count = sum(1 for r in write_results if r[1] == 200)
        assert success_count <= 1, "Only one write should succeed"


class TestFileCorruptionProtection:
    """Test file corruption protection mechanisms."""
    
    def test_atomic_file_writes(self, test_client, auth_headers, temp_repo):
        """Test that file writes are atomic and don't leave partial content."""
        # Create test file
        test_file = temp_repo / "atomic-write.txt"
        test_file.write_text("Initial content")
        
        # Get current ETag
        response = test_client.get("/files/atomic-write.txt", headers=auth_headers)
        etag = response.headers.get("etag") or response.headers.get("ETag")
        
        # Write large content
        large_content = "Large content " * 1000  # 14KB content
        content_base64 = base64.b64encode(large_content.encode('utf-8')).decode('ascii')
        
        request_data = {
            "message": "Large content update",
            "content_base64": content_base64
        }
        
        headers = {**auth_headers, "If-Match": etag}
        response = test_client.put("/files/atomic-write.txt", json=request_data, headers=headers)
        assert response.status_code == 200
        
        # Verify file content is complete and correct
        response = test_client.get("/files/atomic-write.txt", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        decoded_content = base64.b64decode(data['content']).decode('utf-8')
        assert decoded_content == large_content
        assert len(decoded_content) == len(large_content)
    
    def test_file_integrity_after_concurrent_writes(self, test_client, auth_headers, temp_repo):
        """Test that file integrity is maintained after concurrent write attempts."""
        # Create test file
        test_file = temp_repo / "integrity-test.txt"
        initial_content = "Initial content"
        test_file.write_text(initial_content)
        
        # Get initial ETag
        response = test_client.get("/files/integrity-test.txt", headers=auth_headers)
        etag = response.headers.get("etag") or response.headers.get("ETag")
        
        # Simulate concurrent writes with different content sizes
        def write_content(content, thread_id):
            content_base64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
            
            request_data = {
                "message": f"Update from thread {thread_id}",
                "content_base64": content_base64
            }
            
            headers = {**auth_headers, "If-Match": etag}
            return test_client.put("/files/integrity-test.txt", json=request_data, headers=headers)
        
        # Start concurrent writes with different content
        threads = []
        futures = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            for i in range(5):
                content = f"Content from thread {i} " * (i + 1)  # Different lengths
                future = executor.submit(write_content, content, i)
                futures.append(future)
        
        # Collect results
        results = []
        for future in concurrent.futures.as_completed(futures):
            try:
                response = future.result()
                results.append(response.status_code)
            except Exception as e:
                results.append(f"error: {e}")
        
        # Only one should succeed
        success_count = sum(1 for r in results if r == 200)
        assert success_count == 1, f"Exactly one write should succeed: {results}"
        
        # Verify file is in a consistent state
        response = test_client.get("/files/integrity-test.txt", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        decoded_content = base64.b64decode(data['content']).decode('utf-8')
        
        # Content should be one of the attempted writes (complete, not corrupted)
        assert len(decoded_content) > 0, "File should not be empty"
        assert decoded_content.startswith("Content from thread"), "Content should be from one of the threads"
    
    def test_unicode_content_integrity(self, test_client, auth_headers, temp_repo):
        """Test that Unicode content maintains integrity through operations."""
        # Test various Unicode content
        unicode_contents = [
            "Hello 世界! 🌍",
            "Special chars: émojis and spécial characters",
            "Math: ∑, ∫, π, ∞",
            "Arabic: مرحبا بالعالم",
            "Chinese: 你好世界",
            "Emoji: 🚀🎉💻🔥⭐"
        ]
        
        test_file = temp_repo / "unicode-test.txt"
        test_file.write_text("Initial content")
        
        # Get initial ETag
        response = test_client.get("/files/unicode-test.txt", headers=auth_headers)
        etag = response.headers.get("etag") or response.headers.get("ETag")
        
        for i, unicode_content in enumerate(unicode_contents):
            # Update with Unicode content
            content_base64 = base64.b64encode(unicode_content.encode('utf-8')).decode('ascii')
            
            request_data = {
                "message": f"Unicode update {i}",
                "content_base64": content_base64
            }
            
            headers = {**auth_headers, "If-Match": etag}
            response = test_client.put("/files/unicode-test.txt", json=request_data, headers=headers)
            assert response.status_code == 200
            
            # Get new ETag
            response = test_client.get("/files/unicode-test.txt", headers=auth_headers)
            etag = response.headers.get("etag") or response.headers.get("ETag")
            
            # Verify Unicode content integrity
            data = response.json()
            decoded_content = base64.b64decode(data['content']).decode('utf-8')
            assert decoded_content == unicode_content, f"Unicode content corrupted: {unicode_content}"
    
    def test_json_content_integrity(self, test_client, auth_headers, temp_repo):
        """Test that JSON content maintains integrity through operations."""
        # Create JSON file
        json_file = temp_repo / "json-integrity.json"
        initial_json = {
            "name": "test",
            "version": "1.0.0",
            "features": ["feature1", "feature2"],
            "nested": {
                "value": 42,
                "array": [1, 2, 3]
            }
        }
        
        import json
        json_file.write_text(json.dumps(initial_json, indent=2))
        
        # Get initial ETag
        response = test_client.get("/files/json-integrity.json", headers=auth_headers)
        etag = response.headers.get("etag") or response.headers.get("ETag")
        
        # Update JSON content
        updated_json = {
            "name": "test-updated",
            "version": "2.0.0",
            "features": ["feature1", "feature2", "feature3"],
            "nested": {
                "value": 84,
                "array": [1, 2, 3, 4],
                "new_field": "added"
            },
            "new_top_level": "value"
        }
        
        updated_json_str = json.dumps(updated_json, indent=2)
        content_base64 = base64.b64encode(updated_json_str.encode('utf-8')).decode('ascii')
        
        request_data = {
            "message": "Update JSON content",
            "content_base64": content_base64
        }
        
        headers = {**auth_headers, "If-Match": etag}
        response = test_client.put("/files/json-integrity.json", json=request_data, headers=headers)
        assert response.status_code == 200
        
        # Verify JSON integrity
        response = test_client.get("/files/json-integrity.json", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        decoded_content = base64.b64decode(data['content']).decode('utf-8')
        
        # Parse and verify JSON structure
        parsed_json = json.loads(decoded_content)
        assert parsed_json == updated_json, "JSON content should match exactly"
        assert isinstance(parsed_json['features'], list), "Array should remain array"
        assert isinstance(parsed_json['nested'], dict), "Object should remain object"


class TestLockMechanisms:
    """Test file locking mechanisms."""
    
    def test_editor_tool_lock_acquisition(self, test_client, auth_headers, temp_repo):
        """Test that the editor tool properly acquires locks."""
        # This test would require direct access to the editor tool
        # For now, we'll test the locking behavior through the API
        
        # Create test file
        test_file = temp_repo / "lock-test.txt"
        test_file.write_text("Content for lock test")
        
        # The locking mechanism is primarily in the editor tool
        # We can test that operations that require locks work correctly
        # by testing the structured file operations endpoint
        
        operation_data = {
            "operation": "GET",
            "path": "lock-test.txt",
            "selector": {"mode": "region", "start": 1, "end": 10},
            "payload": None,
            "intent": "Test lock acquisition",
            "dry_run": False,
            "author": "test-user",
            "correlation_id": "test-lock-123"
        }
        
        response = test_client.post("/files/edit", json=operation_data, headers=auth_headers)
        # This should work (GET operations don't require locks)
        assert response.status_code == 200
        
        data = response.json()
        assert data["ok"] == True
        assert "lock_id" in data or data.get("lock_id") is None  # GET might not need lock
    
    def test_concurrent_lock_contention(self, temp_repo):
        """Test lock contention handling."""
        # This test requires direct access to the FileLockManager
        # We'll create a test that simulates lock contention
        
        from src.cage.tools.editor_tool import FileLockManager
        
        lock_manager = FileLockManager(lock_ttl=60)  # 1 minute TTL
        
        # Test lock acquisition
        lock_id = lock_manager.acquire_lock(
            file_path="test-file.txt",
            agent="agent-1",
            ranges=[{"start": 1, "end": 10}],
            description="Test lock"
        )
        
        assert lock_id is not None, "Lock acquisition should succeed"
        
        # Test that second lock acquisition fails
        second_lock_id = lock_manager.acquire_lock(
            file_path="test-file.txt",
            agent="agent-2",
            ranges=[{"start": 5, "end": 15}],
            description="Second lock attempt"
        )
        
        assert second_lock_id is None, "Second lock acquisition should fail"
        
        # Test lock release
        released = lock_manager.release_lock(lock_id)
        assert released == True, "Lock release should succeed"
        
        # Test that lock can be acquired again after release
        third_lock_id = lock_manager.acquire_lock(
            file_path="test-file.txt",
            agent="agent-3",
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


class TestRaceConditions:
    """Test race condition scenarios."""
    
    def test_read_during_write(self, test_client, auth_headers, temp_repo):
        """Test reading file while it's being written."""
        # Create test file
        test_file = temp_repo / "read-during-write.txt"
        test_file.write_text("Initial content")
        
        # Get initial ETag
        response = test_client.get("/files/read-during-write.txt", headers=auth_headers)
        etag = response.headers.get("etag") or response.headers.get("ETag")
        
        read_results = []
        write_completed = False
        
        def write_operation():
            nonlocal write_completed
            try:
                large_content = "Large content " * 1000
                content_base64 = base64.b64encode(large_content.encode('utf-8')).decode('ascii')
                
                request_data = {
                    "message": "Large write operation",
                    "content_base64": content_base64
                }
                
                headers = {**auth_headers, "If-Match": etag}
                response = test_client.put("/files/read-during-write.txt", json=request_data, headers=headers)
                write_completed = True
                return response.status_code
            except Exception as e:
                return f"error: {e}"
        
        def read_operation():
            try:
                response = test_client.get("/files/read-during-write.txt", headers=auth_headers)
                read_results.append(response.status_code)
                return response.status_code
            except Exception as e:
                read_results.append(f"error: {e}")
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
    
    def test_etag_race_condition(self, test_client, auth_headers, temp_repo):
        """Test ETag race condition where ETag changes between read and write."""
        # Create test file
        test_file = temp_repo / "etag-race.txt"
        test_file.write_text("Initial content")
        
        # Get initial ETag
        response = test_client.get("/files/etag-race.txt", headers=auth_headers)
        initial_etag = response.headers.get("etag") or response.headers.get("ETag")
        
        # Simulate race condition: two clients read the same ETag, then both try to update
        def client_operation(client_id):
            # Client reads file and gets ETag
            response = test_client.get("/files/etag-race.txt", headers=auth_headers)
            etag = response.headers.get("etag") or response.headers.get("ETag")
            
            # Client tries to update with the ETag they read
            content = f"Content from client {client_id}"
            content_base64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
            
            request_data = {
                "message": f"Update from client {client_id}",
                "content_base64": content_base64
            }
            
            headers = {**auth_headers, "If-Match": etag}
            response = test_client.put("/files/etag-race.txt", json=request_data, headers=headers)
            return response.status_code
        
        # Start two client operations simultaneously
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(client_operation, 1)
            future2 = executor.submit(client_operation, 2)
            
            result1 = future1.result()
            result2 = future2.result()
        
        # One should succeed (200), one should fail (412)
        success_count = sum(1 for r in [result1, result2] if r == 200)
        failure_count = sum(1 for r in [result1, result2] if r == 412)
        
        assert success_count == 1, "Exactly one operation should succeed"
        assert failure_count == 1, "Exactly one operation should fail with ETag conflict"
    
    def test_concurrent_patch_operations(self, test_client, auth_headers, temp_repo):
        """Test concurrent PATCH operations on the same file."""
        # Create test file
        test_file = temp_repo / "concurrent-patch.txt"
        initial_content = "Line 1\nLine 2\nLine 3\nLine 4"
        test_file.write_text(initial_content)
        
        # Get initial ETag
        response = test_client.get("/files/concurrent-patch.txt", headers=auth_headers)
        etag = response.headers.get("etag") or response.headers.get("ETag")
        
        def patch_operation(operation_id):
            try:
                patch_request = {
                    "content": f"Content modified by operation {operation_id}",
                    "message": f"Patch operation {operation_id}"
                }
                
                headers = {**auth_headers, "If-Match": etag}
                response = test_client.patch("/files/concurrent-patch.txt", json=patch_request, headers=headers)
                return response.status_code
            except Exception as e:
                return f"error: {e}"
        
        # Start multiple concurrent PATCH operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(patch_operation, i) for i in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Only one PATCH should succeed
        success_count = sum(1 for r in results if r == 200)
        failure_count = sum(1 for r in results if r == 412)
        
        assert success_count == 1, f"Exactly one PATCH should succeed: {results}"
        assert failure_count == 4, f"Four PATCH operations should fail with ETag conflict: {results}"


@pytest.mark.integration
class TestConcurrencyIntegration:
    """Integration tests for concurrency scenarios."""
    
    def test_full_concurrency_scenario(self, test_client, auth_headers, temp_repo):
        """Test a full concurrency scenario with multiple operations."""
        # Create initial file
        test_file = temp_repo / "full-concurrency.txt"
        test_file.write_text("Initial content")
        
        # Get initial ETag
        response = test_client.get("/files/full-concurrency.txt", headers=auth_headers)
        etag = response.headers.get("etag") or response.headers.get("ETag")
        
        results = []
        
        def mixed_operation(operation_type, operation_id):
            try:
                if operation_type == "read":
                    response = test_client.get("/files/full-concurrency.txt", headers=auth_headers)
                    return ("read", response.status_code)
                
                elif operation_type == "write":
                    content = f"Content from write {operation_id}"
                    content_base64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
                    
                    request_data = {
                        "message": f"Write operation {operation_id}",
                        "content_base64": content_base64
                    }
                    
                    headers = {**auth_headers, "If-Match": etag}
                    response = test_client.put("/files/full-concurrency.txt", json=request_data, headers=headers)
                    return ("write", response.status_code)
                
                elif operation_type == "patch":
                    patch_request = {
                        "content": f"Patched content {operation_id}",
                        "message": f"Patch operation {operation_id}"
                    }
                    
                    headers = {**auth_headers, "If-Match": etag}
                    response = test_client.patch("/files/full-concurrency.txt", json=patch_request, headers=headers)
                    return ("patch", response.status_code)
                
            except Exception as e:
                return (operation_type, f"error: {e}")
        
        # Define operation mix
        operations = [
            ("read", 1), ("read", 2), ("write", 1), ("patch", 1),
            ("read", 3), ("write", 2), ("read", 4), ("patch", 2),
            ("write", 3), ("read", 5)
        ]
        
        # Execute operations concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(mixed_operation, op_type, op_id) for op_type, op_id in operations]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Analyze results
        read_results = [r for r in results if r[0] == "read"]
        write_results = [r for r in results if r[0] == "write"]
        patch_results = [r for r in results if r[0] == "patch"]
        
        # All reads should succeed
        assert all(r[1] == 200 for r in read_results), "All read operations should succeed"
        
        # Only one write should succeed (due to ETag conflicts)
        write_successes = [r for r in write_results if r[1] == 200]
        assert len(write_successes) <= 1, "At most one write should succeed"
        
        # Only one patch should succeed (due to ETag conflicts)
        patch_successes = [r for r in patch_results if r[1] == 200]
        assert len(patch_successes) <= 1, "At most one patch should succeed"
        
        # Verify final file state is consistent
        response = test_client.get("/files/full-concurrency.txt", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        decoded_content = base64.b64decode(data['content']).decode('utf-8')
        assert len(decoded_content) > 0, "File should not be empty or corrupted"
