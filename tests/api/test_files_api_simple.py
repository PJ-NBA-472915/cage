"""
Simple File Editing API Tests
Basic tests that make HTTP requests to the running files-api service.
"""

import os

import pytest
import requests

# Mark all tests in this module as API tests
pytestmark = pytest.mark.api

# Set up environment
os.environ["POD_TOKEN"] = "test-token"
os.environ["REPO_PATH"] = "/tmp/test_repo"

# Base URL for the files-api service
BASE_URL = "http://localhost:8001"


@pytest.fixture(scope="session")
def files_api_available():
    """Check if files-api service is available."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


@pytest.fixture
def auth_headers():
    """Get authentication headers."""
    return {"Authorization": "Bearer test-token"}


class TestFilesAPISimple:
    """Simple tests for the file editing API."""

    @pytest.mark.smoke
    def test_health_endpoint(self, files_api_available):
        """Test the health endpoint works."""
        if not files_api_available:
            pytest.skip("Files API service not available")

        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert data["service"] == "files-api"
        assert "version" in data
        assert data["version"] == "1.0.0"

    @pytest.mark.smoke
    def test_file_edit_endpoint_structure(self, auth_headers, files_api_available):
        """Test that the file edit endpoint accepts the expected structure."""
        if not files_api_available:
            pytest.skip("Files API service not available")

        payload = {
            "operation": "replace_content",
            "path": "/test/file.txt",
            "payload": {"content": "test content"},
            "author": "test-user",
            "correlation_id": "test-123",
        }

        response = requests.post(
            f"{BASE_URL}/files/edit", json=payload, headers=auth_headers
        )

        # Should not get authentication error
        assert response.status_code != 401, "Should not get authentication error"
        assert response.status_code != 403, "Should not get forbidden error"

        # Should get some response (even if it's an error due to file not existing)
        assert response.status_code in [
            200,
            400,
            404,
            500,
        ], f"Unexpected status code: {response.status_code}"

        data = response.json()
        assert "file" in data
        assert data["file"] == "/test/file.txt"
        assert "operation" in data
        assert data["operation"] == "replace_content"

    def test_file_edit_dry_run(self, auth_headers, files_api_available):
        """Test dry run mode."""
        if not files_api_available:
            pytest.skip("Files API service not available")

        payload = {
            "operation": "replace_content",
            "path": "/test/file.txt",
            "payload": {"content": "test content"},
            "author": "test-user",
            "correlation_id": "test-123",
            "dry_run": True,
        }

        response = requests.post(
            f"{BASE_URL}/files/edit", json=payload, headers=auth_headers
        )

        # Should not get authentication error
        assert response.status_code != 401, "Should not get authentication error"
        assert response.status_code != 403, "Should not get forbidden error"

        # Should get some response
        assert response.status_code in [
            200,
            400,
            404,
            500,
        ], f"Unexpected status code: {response.status_code}"

        data = response.json()
        assert "file" in data
        assert "operation" in data

    def test_request_id_header(self, auth_headers, files_api_available):
        """Test that request ID is returned in headers."""
        if not files_api_available:
            pytest.skip("Files API service not available")

        payload = {
            "operation": "replace_content",
            "path": "/test/file.txt",
            "payload": {"content": "test content"},
            "author": "test-user",
            "correlation_id": "test-123",
        }

        response = requests.post(
            f"{BASE_URL}/files/edit", json=payload, headers=auth_headers
        )

        # Should have request ID header
        assert "X-Request-ID" in response.headers, "Should include X-Request-ID header"
        request_id = response.headers["X-Request-ID"]
        assert request_id is not None, "Request ID should not be None"

        # Request ID should be a valid UUID format
        import re

        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        assert re.match(
            uuid_pattern, request_id, re.IGNORECASE
        ), f"Request ID should be valid UUID format, got: {request_id}"

    def test_file_sha_endpoint(self, auth_headers, files_api_available):
        """Test the file SHA endpoint."""
        if not files_api_available:
            pytest.skip("Files API service not available")

        response = requests.get(
            f"{BASE_URL}/files/sha?path=/test/file.txt", headers=auth_headers
        )

        # Should not get authentication error
        assert response.status_code != 401, "Should not get authentication error"
        assert response.status_code != 403, "Should not get forbidden error"

        # Should get some response
        assert response.status_code in [
            200,
            400,
            404,
            500,
        ], f"Unexpected status code: {response.status_code}"

        data = response.json()
        assert "path" in data
        assert data["path"] == "/test/file.txt"
        assert "sha" in data
        assert "size" in data

    def test_commit_endpoint(self, auth_headers, files_api_available):
        """Test the commit endpoint."""
        if not files_api_available:
            pytest.skip("Files API service not available")

        response = requests.post(
            f"{BASE_URL}/files/commit",
            params={
                "message": "Test commit",
                "author": "test-user",
                "task_id": "test-task-123",
            },
            headers=auth_headers,
        )

        # Should not get authentication error
        assert response.status_code != 401, "Should not get authentication error"
        assert response.status_code != 403, "Should not get forbidden error"

        # Should get some response
        assert response.status_code in [
            200,
            400,
            500,
        ], f"Unexpected status code: {response.status_code}"

        data = response.json()
        assert "status" in data
        assert "message" in data
        assert "commit_sha" in data

    def test_diff_endpoint(self, auth_headers, files_api_available):
        """Test the diff endpoint."""
        if not files_api_available:
            pytest.skip("Files API service not available")

        response = requests.get(f"{BASE_URL}/diff", headers=auth_headers)

        # Should not get authentication error
        assert response.status_code != 401, "Should not get authentication error"
        assert response.status_code != 403, "Should not get forbidden error"

        # Should get some response
        assert response.status_code in [
            200,
            400,
            500,
        ], f"Unexpected status code: {response.status_code}"

        data = response.json()
        assert "branch" in data
        assert "diff" in data
        assert "files_changed" in data

    def test_authentication_required(self, files_api_available):
        """Test that authentication is required."""
        if not files_api_available:
            pytest.skip("Files API service not available")

        payload = {
            "operation": "replace_content",
            "path": "/test/file.txt",
            "payload": {"content": "test content"},
            "author": "test-user",
            "correlation_id": "test-123",
        }

        # Request without authentication
        response = requests.post(f"{BASE_URL}/files/edit", json=payload)
        assert response.status_code == 403, "Should require authentication"

    def test_invalid_token_rejected(self, files_api_available):
        """Test that invalid tokens are rejected."""
        if not files_api_available:
            pytest.skip("Files API service not available")

        payload = {
            "operation": "replace_content",
            "path": "/test/file.txt",
            "payload": {"content": "test content"},
            "author": "test-user",
            "correlation_id": "test-123",
        }

        # Request with invalid token
        headers = {"Authorization": "Bearer invalid-token"}
        response = requests.post(
            f"{BASE_URL}/files/edit", json=payload, headers=headers
        )
        assert response.status_code == 401, "Should reject invalid token"


# Standalone execution support
if __name__ == "__main__":
    import sys

    # Set up environment
    os.environ["POD_TOKEN"] = "test-token"
    os.environ["REPO_PATH"] = "/tmp/test_repo"

    print("🚀 Starting File Editing API Simple Tests")
    print("==================================================")

    # Check if service is available
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Files API service not responding")
            sys.exit(1)
    except requests.exceptions.RequestException:
        print("❌ Files API service not available")
        sys.exit(1)

    print("✅ Files API service is available")

    # Run tests manually
    auth_headers = {"Authorization": "Bearer test-token"}

    def run_test(name, test_func, *args, **kwargs):
        print(f"🧪 Running {name}...")
        try:
            test_func(*args, **kwargs)
            print(f"✅ {name} PASSED")
            return True
        except AssertionError as e:
            print(f"❌ {name} FAILED: {e}")
            return False
        except Exception as e:
            print(f"❌ {name} FAILED with unexpected error: {e}")
            return False

    # Create a mock files_api_available fixture
    class MockFilesApiAvailable:
        def __init__(self):
            self.available = True

    mock_fixture = MockFilesApiAvailable()

    results = []
    test_instance = TestFilesAPISimple()

    results.append(
        run_test("Health Endpoint", test_instance.test_health_endpoint, mock_fixture)
    )
    results.append(
        run_test(
            "File Edit Endpoint Structure",
            test_instance.test_file_edit_endpoint_structure,
            auth_headers,
            mock_fixture,
        )
    )
    results.append(
        run_test(
            "File Edit Dry Run",
            test_instance.test_file_edit_dry_run,
            auth_headers,
            mock_fixture,
        )
    )
    results.append(
        run_test(
            "Request ID Header",
            test_instance.test_request_id_header,
            auth_headers,
            mock_fixture,
        )
    )
    results.append(
        run_test(
            "File SHA Endpoint",
            test_instance.test_file_sha_endpoint,
            auth_headers,
            mock_fixture,
        )
    )
    results.append(
        run_test(
            "Commit Endpoint",
            test_instance.test_commit_endpoint,
            auth_headers,
            mock_fixture,
        )
    )
    results.append(
        run_test(
            "Diff Endpoint",
            test_instance.test_diff_endpoint,
            auth_headers,
            mock_fixture,
        )
    )
    results.append(
        run_test(
            "Authentication Required",
            test_instance.test_authentication_required,
            mock_fixture,
        )
    )
    results.append(
        run_test(
            "Invalid Token Rejected",
            test_instance.test_invalid_token_rejected,
            mock_fixture,
        )
    )

    print("\n==================================================")
    print("📊 Test Summary")
    print("==================================================")
    total_tests = len(results)
    passed_tests = sum(results)
    failed_tests = total_tests - passed_tests
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")

    if failed_tests == 0:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed.")
        sys.exit(1)
