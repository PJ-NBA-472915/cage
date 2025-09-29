"""
Stress tests for Files API concurrency and performance.

This module tests:
- High-load concurrent operations
- Memory and performance under stress
- Edge cases and boundary conditions
- System stability under extreme conditions
"""

import asyncio
import base64
import concurrent.futures
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


class TestHighLoadConcurrency:
    """Test high-load concurrent operations."""
    
    def test_many_concurrent_reads(self, test_client, auth_headers, temp_repo):
        """Test system stability with many concurrent reads."""
        # Create test file
        test_file = temp_repo / "high-load-reads.txt"
        test_content = "Content for high-load testing " * 100
        test_file.write_text(test_content)
        
        results = []
        errors = []
        
        def read_operation():
            try:
                start_time = time.time()
                response = test_client.get("/files/high-load-reads.txt", headers=auth_headers)
                end_time = time.time()
                
                results.append({
                    'status_code': response.status_code,
                    'response_time': end_time - start_time
                })
            except Exception as e:
                errors.append(str(e))
        
        # Start many concurrent reads
        num_operations = 100
        threads = []
        
        start_time = time.time()
        for _ in range(num_operations):
            thread = threading.Thread(target=read_operation)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Verify results
        assert len(errors) == 0, f"Errors in high-load reads: {errors[:5]}"  # Show first 5 errors
        assert len(results) == num_operations, "All operations should complete"
        
        # All reads should succeed
        success_count = sum(1 for r in results if r['status_code'] == 200)
        assert success_count == num_operations, f"All reads should succeed: {success_count}/{num_operations}"
        
        # Performance should be reasonable
        avg_response_time = sum(r['response_time'] for r in results) / len(results)
        assert avg_response_time < 1.0, f"Average response time too high: {avg_response_time}s"
        
        # Total time should be reasonable (concurrent operations)
        assert total_time < 10.0, f"Total execution time too high: {total_time}s"
    
    def test_many_concurrent_writes_with_conflicts(self, test_client, auth_headers, temp_repo):
        """Test system stability with many concurrent writes (most will conflict)."""
        # Create test file
        test_file = temp_repo / "high-load-writes.txt"
        test_file.write_text("Initial content")
        
        # Get initial ETag
        response = test_client.get("/files/high-load-writes.txt", headers=auth_headers)
        etag = response.headers.get("etag") or response.headers.get("ETag")
        
        results = []
        errors = []
        
        def write_operation(operation_id):
            try:
                content = f"Content from operation {operation_id}"
                content_base64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
                
                request_data = {
                    "message": f"High-load write {operation_id}",
                    "content_base64": content_base64
                }
                
                headers = {**auth_headers, "If-Match": etag}
                start_time = time.time()
                response = test_client.put("/files/high-load-writes.txt", json=request_data, headers=headers)
                end_time = time.time()
                
                results.append({
                    'status_code': response.status_code,
                    'response_time': end_time - start_time,
                    'operation_id': operation_id
                })
            except Exception as e:
                errors.append(f"Operation {operation_id}: {e}")
        
        # Start many concurrent writes
        num_operations = 50
        threads = []
        
        start_time = time.time()
        for i in range(num_operations):
            thread = threading.Thread(target=write_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Verify results
        assert len(errors) == 0, f"Errors in high-load writes: {errors[:5]}"
        assert len(results) == num_operations, "All operations should complete"
        
        # Most writes should fail due to ETag conflicts (only one can succeed)
        success_count = sum(1 for r in results if r['status_code'] == 200)
        conflict_count = sum(1 for r in results if r['status_code'] == 412)
        
        assert success_count == 1, f"Exactly one write should succeed: {success_count}"
        assert conflict_count == num_operations - 1, f"Most writes should conflict: {conflict_count}"
        
        # Performance should be reasonable even with conflicts
        avg_response_time = sum(r['response_time'] for r in results) / len(results)
        assert avg_response_time < 2.0, f"Average response time too high: {avg_response_time}s"
        
        # Total time should be reasonable
        assert total_time < 15.0, f"Total execution time too high: {total_time}s"
    
    def test_mixed_high_load_operations(self, test_client, auth_headers, temp_repo):
        """Test mixed high-load operations (reads, writes, patches)."""
        # Create test file
        test_file = temp_repo / "mixed-high-load.txt"
        test_file.write_text("Initial content")
        
        # Get initial ETag
        response = test_client.get("/files/mixed-high-load.txt", headers=auth_headers)
        etag = response.headers.get("etag") or response.headers.get("ETag")
        
        results = []
        errors = []
        
        def read_operation(operation_id):
            try:
                response = test_client.get("/files/mixed-high-load.txt", headers=auth_headers)
                results.append(('read', response.status_code, operation_id))
            except Exception as e:
                errors.append(f"Read {operation_id}: {e}")
        
        def write_operation(operation_id):
            try:
                content = f"Write content {operation_id}"
                content_base64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
                
                request_data = {
                    "message": f"Write {operation_id}",
                    "content_base64": content_base64
                }
                
                headers = {**auth_headers, "If-Match": etag}
                response = test_client.put("/files/mixed-high-load.txt", json=request_data, headers=headers)
                results.append(('write', response.status_code, operation_id))
            except Exception as e:
                errors.append(f"Write {operation_id}: {e}")
        
        def patch_operation(operation_id):
            try:
                patch_request = {
                    "content": f"Patch content {operation_id}",
                    "message": f"Patch {operation_id}"
                }
                
                headers = {**auth_headers, "If-Match": etag}
                response = test_client.patch("/files/mixed-high-load.txt", json=patch_request, headers=headers)
                results.append(('patch', response.status_code, operation_id))
            except Exception as e:
                errors.append(f"Patch {operation_id}: {e}")
        
        # Start mixed operations
        num_operations = 30
        threads = []
        
        start_time = time.time()
        for i in range(num_operations):
            if i % 3 == 0:
                thread = threading.Thread(target=write_operation, args=(i,))
            elif i % 3 == 1:
                thread = threading.Thread(target=patch_operation, args=(i,))
            else:
                thread = threading.Thread(target=read_operation, args=(i,))
            
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Verify results
        assert len(errors) == 0, f"Errors in mixed high-load: {errors[:5]}"
        assert len(results) == num_operations, "All operations should complete"
        
        # Analyze results by operation type
        read_results = [r for r in results if r[0] == 'read']
        write_results = [r for r in results if r[0] == 'write']
        patch_results = [r for r in results if r[0] == 'patch']
        
        # All reads should succeed
        assert all(r[1] == 200 for r in read_results), "All reads should succeed"
        
        # At most one write and one patch should succeed
        write_successes = sum(1 for r in write_results if r[1] == 200)
        patch_successes = sum(1 for r in patch_results if r[1] == 200)
        
        assert write_successes <= 1, f"At most one write should succeed: {write_successes}"
        assert patch_successes <= 1, f"At most one patch should succeed: {patch_successes}"
        
        # Total time should be reasonable
        assert total_time < 20.0, f"Total execution time too high: {total_time}s"


class TestLargeFileOperations:
    """Test operations on large files."""
    
    def test_large_file_read(self, test_client, auth_headers, temp_repo):
        """Test reading large files."""
        # Create large file (1MB)
        test_file = temp_repo / "large-file.txt"
        large_content = "Large file content " * 50000  # ~1MB
        test_file.write_text(large_content)
        
        start_time = time.time()
        response = test_client.get("/files/large-file.txt", headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        assert end_time - start_time < 5.0, "Large file read should complete quickly"
        
        # Verify content integrity
        data = response.json()
        decoded_content = base64.b64decode(data['content']).decode('utf-8')
        assert len(decoded_content) == len(large_content)
        assert decoded_content == large_content
    
    def test_large_file_write(self, test_client, auth_headers, temp_repo):
        """Test writing large files."""
        # Create initial file
        test_file = temp_repo / "large-write.txt"
        test_file.write_text("Initial content")
        
        # Get initial ETag
        response = test_client.get("/files/large-write.txt", headers=auth_headers)
        etag = response.headers.get("etag") or response.headers.get("ETag")
        
        # Create large content (1MB)
        large_content = "Large write content " * 50000
        content_base64 = base64.b64encode(large_content.encode('utf-8')).decode('ascii')
        
        request_data = {
            "message": "Large file write",
            "content_base64": content_base64
        }
        
        headers = {**auth_headers, "If-Match": etag}
        start_time = time.time()
        response = test_client.put("/files/large-write.txt", json=request_data, headers=headers)
        end_time = time.time()
        
        assert response.status_code == 200
        assert end_time - start_time < 10.0, "Large file write should complete in reasonable time"
        
        # Verify content was written correctly
        response = test_client.get("/files/large-write.txt", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        decoded_content = base64.b64decode(data['content']).decode('utf-8')
        assert len(decoded_content) == len(large_content)
        assert decoded_content == large_content
    
    def test_concurrent_large_file_operations(self, test_client, auth_headers, temp_repo):
        """Test concurrent operations on large files."""
        # Create large file
        test_file = temp_repo / "concurrent-large.txt"
        large_content = "Large content " * 30000  # ~400KB
        test_file.write_text(large_content)
        
        results = []
        
        def read_large_file():
            try:
                start_time = time.time()
                response = test_client.get("/files/concurrent-large.txt", headers=auth_headers)
                end_time = time.time()
                
                results.append({
                    'type': 'read',
                    'status': response.status_code,
                    'time': end_time - start_time
                })
            except Exception as e:
                results.append({'type': 'read', 'status': 'error', 'error': str(e)})
        
        # Start multiple concurrent reads of large file
        num_operations = 20
        threads = []
        
        start_time = time.time()
        for _ in range(num_operations):
            thread = threading.Thread(target=read_large_file)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Verify results
        read_results = [r for r in results if r['type'] == 'read']
        assert len(read_results) == num_operations, "All operations should complete"
        
        # All reads should succeed
        success_count = sum(1 for r in read_results if r['status'] == 200)
        assert success_count == num_operations, f"All reads should succeed: {success_count}/{num_operations}"
        
        # Performance should be reasonable
        avg_time = sum(r['time'] for r in read_results if 'time' in r) / len(read_results)
        assert avg_time < 3.0, f"Average read time too high: {avg_time}s"
        
        # Total time should be reasonable (concurrent)
        assert total_time < 10.0, f"Total execution time too high: {total_time}s"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_file_operations(self, test_client, auth_headers, temp_repo):
        """Test operations on empty files."""
        # Create empty file
        test_file = temp_repo / "empty.txt"
        test_file.write_text("")
        
        # Read empty file
        response = test_client.get("/files/empty.txt", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        decoded_content = base64.b64decode(data['content']).decode('utf-8')
        assert decoded_content == ""
        assert data['size'] == 0
        
        # Update empty file
        etag = response.headers.get("etag") or response.headers.get("ETag")
        content = "New content"
        content_base64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
        
        request_data = {
            "message": "Update empty file",
            "content_base64": content_base64
        }
        
        headers = {**auth_headers, "If-Match": etag}
        response = test_client.put("/files/empty.txt", json=request_data, headers=headers)
        assert response.status_code == 200
        
        # Verify update
        response = test_client.get("/files/empty.txt", headers=auth_headers)
        data = response.json()
        decoded_content = base64.b64decode(data['content']).decode('utf-8')
        assert decoded_content == content
    
    def test_very_long_filename(self, test_client, auth_headers, temp_repo):
        """Test operations with very long filenames."""
        # Create file with very long name
        long_name = "very_long_filename_" + "x" * 200 + ".txt"
        test_file = temp_repo / long_name
        test_file.write_text("Content for long filename")
        
        # Test operations on long filename
        response = test_client.get(f"/files/{long_name}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data['path'] == long_name
    
    def test_special_characters_in_filename(self, test_client, auth_headers, temp_repo):
        """Test operations with special characters in filenames."""
        # Test various special characters
        special_names = [
            "file with spaces.txt",
            "file-with-dashes.txt",
            "file_with_underscores.txt",
            "file.with.dots.txt",
            "file(with)parentheses.txt",
            "file[with]brackets.txt",
            "file{with}braces.txt"
        ]
        
        for filename in special_names:
            test_file = temp_repo / filename
            test_file.write_text(f"Content for {filename}")
            
            # Test read
            response = test_client.get(f"/files/{filename}", headers=auth_headers)
            assert response.status_code == 200, f"Failed to read file: {filename}"
            
            data = response.json()
            assert data['path'] == filename
    
    def test_unicode_in_filename(self, test_client, auth_headers, temp_repo):
        """Test operations with Unicode characters in filenames."""
        unicode_names = [
            "файл.txt",  # Cyrillic
            "文件.txt",   # Chinese
            "ファイル.txt", # Japanese
            "ملف.txt",   # Arabic
            "archivo.txt"  # Spanish (normal ASCII)
        ]
        
        for filename in unicode_names:
            test_file = temp_repo / filename
            test_file.write_text(f"Content for {filename}")
            
            # Test read
            response = test_client.get(f"/files/{filename}", headers=auth_headers)
            assert response.status_code == 200, f"Failed to read Unicode file: {filename}"
            
            data = response.json()
            assert data['path'] == filename
    
    def test_concurrent_operations_on_different_files(self, test_client, auth_headers, temp_repo):
        """Test concurrent operations on different files (should not conflict)."""
        # Create multiple files
        num_files = 20
        files = []
        etags = {}
        
        for i in range(num_files):
            filename = f"concurrent-file-{i}.txt"
            test_file = temp_repo / filename
            test_file.write_text(f"Content for file {i}")
            files.append(filename)
            
            # Get ETag for each file
            response = test_client.get(f"/files/{filename}", headers=auth_headers)
            etag = response.headers.get("etag") or response.headers.get("ETag")
            etags[filename] = etag
        
        results = []
        
        def update_file(filename):
            try:
                content = f"Updated content for {filename}"
                content_base64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
                
                request_data = {
                    "message": f"Update {filename}",
                    "content_base64": content_base64
                }
                
                headers = {**auth_headers, "If-Match": etags[filename]}
                response = test_client.put(f"/files/{filename}", json=request_data, headers=headers)
                results.append({'filename': filename, 'status': response.status_code})
            except Exception as e:
                results.append({'filename': filename, 'status': 'error', 'error': str(e)})
        
        # Start concurrent updates on different files
        threads = []
        start_time = time.time()
        
        for filename in files:
            thread = threading.Thread(target=update_file, args=(filename,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # All operations should succeed (no conflicts between different files)
        assert len(results) == num_files, "All operations should complete"
        
        success_count = sum(1 for r in results if r['status'] == 200)
        assert success_count == num_files, f"All updates should succeed: {success_count}/{num_files}"
        
        # Performance should be good (no conflicts)
        assert total_time < 10.0, f"Total execution time too high: {total_time}s"


@pytest.mark.slow
class TestStressScenarios:
    """Slow stress tests that take longer to run."""
    
    def test_extended_concurrency_stress(self, test_client, auth_headers, temp_repo):
        """Extended stress test with continuous concurrent operations."""
        # Create test file
        test_file = temp_repo / "stress-test.txt"
        test_file.write_text("Initial stress test content")
        
        # Get initial ETag
        response = test_client.get("/files/stress-test.txt", headers=auth_headers)
        etag = response.headers.get("etag") or response.headers.get("ETag")
        
        results = []
        errors = []
        
        def stress_operation(operation_id):
            try:
                # Mix of operations
                if operation_id % 4 == 0:
                    # Write operation
                    content = f"Stress write {operation_id}"
                    content_base64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
                    
                    request_data = {
                        "message": f"Stress write {operation_id}",
                        "content_base64": content_base64
                    }
                    
                    headers = {**auth_headers, "If-Match": etag}
                    response = test_client.put("/files/stress-test.txt", json=request_data, headers=headers)
                    results.append(('write', response.status_code, operation_id))
                
                else:
                    # Read operation
                    response = test_client.get("/files/stress-test.txt", headers=auth_headers)
                    results.append(('read', response.status_code, operation_id))
                    
            except Exception as e:
                errors.append(f"Operation {operation_id}: {e}")
        
        # Run stress test for extended period
        num_operations = 200
        threads = []
        
        start_time = time.time()
        for i in range(num_operations):
            thread = threading.Thread(target=stress_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Verify results
        assert len(errors) == 0, f"Errors in stress test: {errors[:5]}"
        assert len(results) == num_operations, "All operations should complete"
        
        # Analyze results
        read_results = [r for r in results if r[0] == 'read']
        write_results = [r for r in results if r[0] == 'write']
        
        # All reads should succeed
        read_successes = sum(1 for r in read_results if r[1] == 200)
        assert read_successes == len(read_results), "All reads should succeed"
        
        # Most writes should fail due to ETag conflicts
        write_successes = sum(1 for r in write_results if r[1] == 200)
        assert write_successes <= 1, f"At most one write should succeed: {write_successes}"
        
        # Performance should be reasonable
        assert total_time < 30.0, f"Total execution time too high: {total_time}s"
        
        # Verify final file state is consistent
        response = test_client.get("/files/stress-test.txt", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        decoded_content = base64.b64decode(data['content']).decode('utf-8')
        assert len(decoded_content) > 0, "File should not be empty or corrupted"

