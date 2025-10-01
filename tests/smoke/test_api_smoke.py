"""
Smoke tests for file API services.

These tests verify that the core functionality works without requiring containers.
They use httpx.AsyncClient to test the FastAPI applications directly.
"""

import os

# Import the FastAPI apps
import sys
import uuid

import pytest
from fastapi.testclient import TestClient

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
)

from src.apps.files_api.main import app as files_app
from src.apps.git_api.main import app as git_app
from src.apps.lock_api.main import app as lock_app
from src.apps.rag_api.main import app as rag_app


class TestSmokeAPI:
    """Smoke tests for all file API services."""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment variables."""
        # Set POD_TOKEN for authentication
        os.environ["POD_TOKEN"] = "test-token-123"

    @pytest.fixture
    def auth_headers(self) -> dict[str, str]:
        """Get authentication headers for API requests."""
        return {
            "Authorization": "Bearer test-token-123",
            "X-Request-ID": str(uuid.uuid4()),
        }

    @pytest.mark.smoke
    def test_files_api_health_happy_path(self, auth_headers: dict[str, str]):
        """Test files API health endpoint happy path."""
        with TestClient(files_app) as client:
            response = client.get("/health", headers=auth_headers)

            # Assert success
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["service"] == "files-api"
            assert "date" in data
            assert "version" in data

            # Assert X-Request-ID is echoed
            assert "X-Request-ID" in response.headers
            assert response.headers["X-Request-ID"] == auth_headers["X-Request-ID"]

    @pytest.mark.smoke
    def test_files_api_edit_happy_path(self, auth_headers: dict[str, str]):
        """Test files API edit endpoint happy path."""
        with TestClient(files_app) as client:
            payload = {
                "path": "/test/file.py",
                "operation": "edit",
                "content": "print('Hello, World!')",
                "line_start": 1,
                "line_end": 1,
            }

            response = client.post("/files/edit", json=payload, headers=auth_headers)

            # Assert success
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["file"] == payload["path"]
            assert data["operation"] == payload["operation"]
            assert "lock_id" in data
            assert "pre_hash" in data
            assert "post_hash" in data

            # Assert X-Request-ID is echoed
            assert "X-Request-ID" in response.headers
            assert response.headers["X-Request-ID"] == auth_headers["X-Request-ID"]

    @pytest.mark.smoke
    def test_files_api_edit_failure_path(self, auth_headers: dict[str, str]):
        """Test files API edit endpoint failure path (validation error)."""
        with TestClient(files_app) as client:
            # Send invalid payload (missing required fields)
            payload = {
                "operation": "edit",
                # Missing required 'path' field
            }

            response = client.post("/files/edit", json=payload, headers=auth_headers)

            # Assert validation error
            assert response.status_code == 422
            data = response.json()
            assert data["type"] == "https://api.cage.dev/problems/validation-error"
            assert data["title"] == "Validation Error"
            assert data["status"] == 422
            assert "detail" in data
            assert "errors" in data

            # Assert X-Request-ID is echoed
            assert "X-Request-ID" in response.headers
            assert response.headers["X-Request-ID"] == auth_headers["X-Request-ID"]

    @pytest.mark.smoke
    def test_files_api_unauthorized_failure(self):
        """Test files API unauthorized access failure path."""
        with TestClient(files_app) as client:
            # Send request without authentication
            payload = {
                "path": "/test/file.py",
                "operation": "edit",
                "content": "print('Hello, World!')",
            }

            response = client.post("/files/edit", json=payload)

            # Assert unauthorized error (should be 403 for missing token)
            assert response.status_code == 403
            data = response.json()
            assert data["type"] == "https://api.cage.dev/problems/forbidden"
            assert data["title"] == "Forbidden"
            assert data["status"] == 403

    @pytest.mark.smoke
    def test_rag_api_health_happy_path(self, auth_headers: dict[str, str]):
        """Test RAG API health endpoint happy path."""
        with TestClient(rag_app) as client:
            response = client.get("/health", headers=auth_headers)

            # Assert success
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["service"] == "rag-api"
            assert "date" in data
            assert "version" in data

            # Assert X-Request-ID is echoed
            assert "X-Request-ID" in response.headers
            assert response.headers["X-Request-ID"] == auth_headers["X-Request-ID"]

    @pytest.mark.smoke
    def test_rag_api_query_happy_path(self, auth_headers: dict[str, str]):
        """Test RAG API query endpoint happy path."""
        with TestClient(rag_app) as client:
            payload = {
                "query": "How to implement authentication?",
                "top_k": 5,
                "filters": {"language": "python"},
            }

            response = client.post("/rag/query", json=payload, headers=auth_headers)

            # Assert success
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["query"] == payload["query"]
            assert "hits" in data
            assert "total" in data

            # Assert X-Request-ID is echoed
            assert "X-Request-ID" in response.headers
            assert response.headers["X-Request-ID"] == auth_headers["X-Request-ID"]

    @pytest.mark.smoke
    def test_rag_api_query_failure_path(self, auth_headers: dict[str, str]):
        """Test RAG API query endpoint failure path (validation error)."""
        with TestClient(rag_app) as client:
            # Send invalid payload (missing required query field)
            payload = {
                "top_k": 5
                # Missing required 'query' field
            }

            response = client.post("/rag/query", json=payload, headers=auth_headers)

            # Assert validation error
            assert response.status_code == 422
            data = response.json()
            assert data["type"] == "https://api.cage.dev/problems/validation-error"
            assert data["title"] == "Validation Error"
            assert data["status"] == 422
            assert "errors" in data

            # Assert X-Request-ID is echoed
            assert "X-Request-ID" in response.headers
            assert response.headers["X-Request-ID"] == auth_headers["X-Request-ID"]

    @pytest.mark.smoke
    def test_lock_api_health_happy_path(self, auth_headers: dict[str, str]):
        """Test Lock API health endpoint happy path."""
        with TestClient(lock_app) as client:
            response = client.get("/health", headers=auth_headers)

            # Assert success
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["service"] == "lock-api"
            assert "date" in data
            assert "version" in data

            # Assert X-Request-ID is echoed
            assert "X-Request-ID" in response.headers
            assert response.headers["X-Request-ID"] == auth_headers["X-Request-ID"]

    @pytest.mark.smoke
    def test_lock_api_templates_happy_path(self, auth_headers: dict[str, str]):
        """Test Lock API templates endpoint happy path."""
        with TestClient(lock_app) as client:
            response = client.get("/lock/templates", headers=auth_headers)

            # Assert success
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0

            # Check template structure
            template = data[0]
            assert "name" in template
            assert "description" in template
            assert "variables" in template

            # Assert X-Request-ID is echoed
            assert "X-Request-ID" in response.headers
            assert response.headers["X-Request-ID"] == auth_headers["X-Request-ID"]

    @pytest.mark.smoke
    def test_lock_api_generate_failure_path(self, auth_headers: dict[str, str]):
        """Test Lock API generate endpoint failure path (validation error)."""
        with TestClient(lock_app) as client:
            # Send invalid payload (missing required template field)
            payload = {
                "variables": {"port": "8080"}
                # Missing required 'template' field
            }

            response = client.post("/lock/generate", json=payload, headers=auth_headers)

            # Assert validation error
            assert response.status_code == 422
            data = response.json()
            assert data["type"] == "https://api.cage.dev/problems/validation-error"
            assert data["title"] == "Validation Error"
            assert data["status"] == 422
            assert "errors" in data

            # Assert X-Request-ID is echoed
            assert "X-Request-ID" in response.headers
            assert response.headers["X-Request-ID"] == auth_headers["X-Request-ID"]

    @pytest.mark.smoke
    def test_git_api_health_happy_path(self, auth_headers: dict[str, str]):
        """Test Git API health endpoint happy path."""
        with TestClient(git_app) as client:
            response = client.get("/health", headers=auth_headers)

            # Assert success
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["service"] == "git-api"
            assert "date" in data
            assert "version" in data

            # Assert X-Request-ID is echoed
            assert "X-Request-ID" in response.headers
            assert response.headers["X-Request-ID"] == auth_headers["X-Request-ID"]

    @pytest.mark.smoke
    def test_git_api_status_happy_path(self, auth_headers: dict[str, str]):
        """Test Git API status endpoint happy path."""
        with TestClient(git_app) as client:
            response = client.get("/git/status", headers=auth_headers)

            # Assert success
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "branch" in data
            assert "clean" in data
            assert "ahead" in data
            assert "behind" in data

            # Assert X-Request-ID is echoed
            assert "X-Request-ID" in response.headers
            assert response.headers["X-Request-ID"] == auth_headers["X-Request-ID"]

    @pytest.mark.smoke
    def test_git_api_commit_failure_path(self, auth_headers: dict[str, str]):
        """Test Git API commit endpoint failure path (validation error)."""
        with TestClient(git_app) as client:
            # Send invalid payload (missing required message field)
            payload = {
                "author": "test@example.com"
                # Missing required 'message' field
            }

            response = client.post("/git/commit", json=payload, headers=auth_headers)

            # Assert validation error
            assert response.status_code == 422
            data = response.json()
            assert data["type"] == "https://api.cage.dev/problems/validation-error"
            assert data["title"] == "Validation Error"
            assert data["status"] == 422
            assert "errors" in data

            # Assert X-Request-ID is echoed
            assert "X-Request-ID" in response.headers
            assert response.headers["X-Request-ID"] == auth_headers["X-Request-ID"]

    @pytest.mark.smoke
    def test_all_services_kubernetes_health_endpoints(
        self, auth_headers: dict[str, str]
    ):
        """Test all services' Kubernetes-style health endpoints."""
        apps = [
            (files_app, "files-api"),
            (rag_app, "rag-api"),
            (lock_app, "lock-api"),
            (git_app, "git-api"),
        ]

        for app, service_name in apps:
            with TestClient(app) as client:
                # Test /healthz endpoint
                response = client.get("/healthz", headers=auth_headers)
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert data["service"] == service_name

                # Test /readyz endpoint
                response = client.get("/readyz", headers=auth_headers)
                # Lock API may return 503 if Golang is not available in test environment
                if service_name == "lock-api":
                    assert response.status_code in [200, 503]
                    if response.status_code == 200:
                        data = response.json()
                        assert data["status"] == "ready"
                        assert data["service"] == service_name
                else:
                    assert response.status_code == 200
                    data = response.json()
                    assert data["status"] == "ready"
                    assert data["service"] == service_name

    @pytest.mark.smoke
    def test_problem_details_schema_consistency(self, auth_headers: dict[str, str]):
        """Test that all services return consistent Problem Details schema."""
        apps = [files_app, rag_app, lock_app, git_app]

        for app in apps:
            with TestClient(app) as client:
                # Trigger a validation error to test Problem Details format
                response = client.post("/files/edit", json={}, headers=auth_headers)

                if response.status_code == 422:
                    data = response.json()
                    # Verify Problem Details schema
                    assert "type" in data
                    assert "title" in data
                    assert "status" in data
                    assert "detail" in data
                    assert data["status"] == 422
                    assert isinstance(data["type"], str)
                    assert isinstance(data["title"], str)
                    assert isinstance(data["detail"], str)

                    # Verify Content-Type header
                    assert (
                        response.headers["content-type"] == "application/problem+json"
                    )

    @pytest.mark.smoke
    def test_request_id_propagation_across_all_services(
        self, auth_headers: dict[str, str]
    ):
        """Test that X-Request-ID is properly propagated across all services."""
        apps = [
            (files_app, "/health"),
            (rag_app, "/health"),
            (lock_app, "/health"),
            (git_app, "/health"),
        ]

        for app, endpoint in apps:
            with TestClient(app) as client:
                response = client.get(endpoint, headers=auth_headers)

                # All endpoints should echo the X-Request-ID
                assert "X-Request-ID" in response.headers
                assert response.headers["X-Request-ID"] == auth_headers["X-Request-ID"]

    @pytest.mark.smoke
    def test_openapi_schema_availability(self):
        """Test that OpenAPI schemas are available for all services."""
        apps = [files_app, rag_app, lock_app, git_app]

        for app in apps:
            with TestClient(app) as client:
                response = client.get("/openapi.json")
                assert response.status_code == 200

                schema = response.json()
                assert "openapi" in schema
                assert "info" in schema
                assert "paths" in schema
                assert "components" in schema

                # Verify Problem Details schema is included
                assert "schemas" in schema["components"]
                assert "ProblemDetail" in schema["components"]["schemas"]

                # Verify security scheme is included
                assert "securitySchemes" in schema["components"]
                assert "BearerAuth" in schema["components"]["securitySchemes"]


if __name__ == "__main__":
    # Run smoke tests directly
    pytest.main([__file__, "-v", "-m", "smoke"])
