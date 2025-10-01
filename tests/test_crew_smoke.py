"""
Smoke tests for CrewAI service.

Basic happy path tests for all endpoints.
"""

from fastapi.testclient import TestClient

from src.crew_service.main import app

client = TestClient(app)


class TestCrewSmoke:
    """Smoke tests for CrewAI service."""

    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "x-request-id" in response.headers

    def test_about_endpoint(self):
        """Test about endpoint."""
        response = client.get("/about")
        assert response.status_code == 200
        data = response.json()
        assert "pod_id" in data
        assert "version" in data
        assert "labels" in data
        assert data["version"] == "1.0.0"
        assert "x-request-id" in response.headers

    def test_create_agent(self):
        """Test agent creation."""
        agent_data = {
            "name": "test-agent",
            "role": "implementer",
            "config": {"language": "python"},
        }
        response = client.post("/agents", json=agent_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-agent"
        assert data["role"] == "implementer"
        assert "id" in data
        assert "created_at" in data
        assert "x-request-id" in response.headers
        return data["id"]

    def test_list_agents(self):
        """Test agent listing."""
        response = client.get("/agents")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "next_cursor" in data
        assert isinstance(data["items"], list)
        assert "x-request-id" in response.headers

    def test_get_agent(self):
        """Test getting a specific agent."""
        # First create an agent
        agent_data = {
            "name": "test-get-agent",
            "role": "planner",
            "config": {"language": "python"},
        }
        create_response = client.post("/agents", json=agent_data)
        agent_id = create_response.json()["id"]

        # Then get it
        response = client.get(f"/agents/{agent_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == agent_id
        assert data["name"] == "test-get-agent"
        assert data["role"] == "planner"
        assert "x-request-id" in response.headers

    def test_get_nonexistent_agent(self):
        """Test getting a non-existent agent returns 404."""
        from uuid import uuid4

        fake_id = str(uuid4())
        response = client.get(f"/agents/{fake_id}")
        assert response.status_code == 404
        assert "x-request-id" in response.headers

    def test_create_crew(self):
        """Test crew creation."""
        # First create an agent
        agent_data = {
            "name": "crew-test-agent",
            "role": "implementer",
            "config": {"language": "python"},
        }
        agent_response = client.post("/agents", json=agent_data)
        agent_id = agent_response.json()["id"]

        # Then create a crew
        crew_data = {
            "name": "test-crew",
            "roles": {"implementer": agent_id},
            "labels": ["test", "smoke"],
        }
        response = client.post("/crews", json=crew_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-crew"
        assert "id" in data
        assert "created_at" in data
        assert "x-request-id" in response.headers
        return data["id"]

    def test_list_crews(self):
        """Test crew listing."""
        response = client.get("/crews")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "next_cursor" in data
        assert isinstance(data["items"], list)
        assert "x-request-id" in response.headers

    def test_get_crew(self):
        """Test getting a specific crew."""
        # First create a crew
        crew_id = self.test_create_crew()

        # Then get it
        response = client.get(f"/crews/{crew_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == crew_id
        assert data["name"] == "test-crew"
        assert "x-request-id" in response.headers

    def test_list_runs(self):
        """Test run listing."""
        response = client.get("/runs")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "next_cursor" in data
        assert isinstance(data["items"], list)
        assert "x-request-id" in response.headers

    def test_agent_invoke(self):
        """Test invoking an agent."""
        # First create an agent
        agent_data = {
            "name": "invoke-test-agent",
            "role": "implementer",
            "config": {"language": "python"},
        }
        agent_response = client.post("/agents", json=agent_data)
        agent_id = agent_response.json()["id"]

        # Then invoke it
        invoke_data = {
            "task": {
                "title": "Test task",
                "description": "A test task for smoke testing",
                "acceptance": ["Task completed successfully"],
            },
            "context": {"test": True},
            "timeout_s": 300,
        }
        response = client.post(f"/agents/{agent_id}/invoke", json=invoke_data)
        assert response.status_code == 200
        data = response.json()
        assert data["kind"] == "agent"
        assert data["agent_id"] == agent_id
        assert data["status"] == "queued"
        assert "id" in data
        assert "x-request-id" in response.headers
        return data["id"]

    def test_crew_run(self):
        """Test running a crew."""
        # First create a crew
        crew_id = self.test_create_crew()

        # Then run it
        run_data = {
            "task": {
                "title": "Crew test task",
                "description": "A test task for crew smoke testing",
                "acceptance": ["Crew task completed successfully"],
            },
            "strategy": "impl_then_verify",
            "timeout_s": 600,
        }
        response = client.post(f"/crews/{crew_id}/run", json=run_data)
        assert response.status_code == 200
        data = response.json()
        assert data["kind"] == "crew"
        assert data["crew_id"] == crew_id
        assert data["status"] == "queued"
        assert "id" in data
        assert "x-request-id" in response.headers
        return data["id"]

    def test_get_run(self):
        """Test getting a specific run."""
        # First create a run
        run_id = self.test_agent_invoke()

        # Then get it
        response = client.get(f"/runs/{run_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == run_id
        assert data["kind"] == "agent"
        assert data["status"] == "queued"
        assert "x-request-id" in response.headers

    def test_cancel_run(self):
        """Test cancelling a run."""
        # First create a run
        run_id = self.test_agent_invoke()

        # Then cancel it
        response = client.post(f"/runs/{run_id}/cancel")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert "x-request-id" in response.headers

    def test_openapi_schema(self):
        """Test OpenAPI schema generation."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()

        # Check that all expected paths are present
        expected_paths = [
            "/",
            "/health",
            "/about",
            "/agents",
            "/agents/{agent_id}",
            "/agents/{agent_id}/invoke",
            "/crews",
            "/crews/{crew_id}",
            "/crews/{crew_id}/run",
            "/runs",
            "/runs/{run_id}",
            "/runs/{run_id}/cancel",
        ]

        for path in expected_paths:
            assert path in schema["paths"], f"Missing path: {path}"

        assert "x-request-id" in response.headers
