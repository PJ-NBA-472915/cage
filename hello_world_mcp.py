#!/usr/bin/env python3
"""
Hello World MCP Application

This application demonstrates the full workflow of the Cage MCP server:
1. Create an agent
2. Create a crew with that agent
3. Invoke the agent with a simple task
4. Check the run status
"""

import json
import sys

import httpx


class CageMCPClient:
    """Simple client for the Cage MCP server."""

    def __init__(self, base_url="http://crew-api:8000", token="test-mcp-token"):
        self.base_url = base_url
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def create_agent(self, name, role, config=None):
        """Create a new agent."""
        data = {"name": name, "role": role}
        if config:
            data["config"] = config

        response = httpx.post(
            f"{self.base_url}/agents", json=data, headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def list_agents(self, role=None):
        """List agents."""
        params = {}
        if role:
            params["role"] = role

        response = httpx.get(
            f"{self.base_url}/agents", params=params, headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def get_agent(self, agent_id):
        """Get agent by ID."""
        response = httpx.get(f"{self.base_url}/agents/{agent_id}", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def create_crew(self, name, roles, labels=None):
        """Create a new crew.

        Args:
            name: Crew name
            roles: Dict mapping role names to agent UUIDs
            labels: Optional list of labels
        """
        data = {"name": name, "roles": roles}
        if labels:
            data["labels"] = labels

        response = httpx.post(f"{self.base_url}/crews", json=data, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def list_crews(self):
        """List crews."""
        response = httpx.get(f"{self.base_url}/crews", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def invoke_agent(self, agent_id, task):
        """Invoke an agent with a task."""
        data = {"task": task}

        response = httpx.post(
            f"{self.base_url}/agents/{agent_id}/invoke", json=data, headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def get_run(self, run_id):
        """Get run status by ID."""
        response = httpx.get(f"{self.base_url}/runs/{run_id}", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def list_runs(self, status=None, agent_id=None):
        """List runs."""
        params = {}
        if status:
            params["status"] = status
        if agent_id:
            params["agent_id"] = agent_id

        response = httpx.get(
            f"{self.base_url}/runs", params=params, headers=self.headers
        )
        response.raise_for_status()
        return response.json()


def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def print_json(data):
    """Pretty print JSON data."""
    print(json.dumps(data, indent=2))


def main():
    """Main hello world workflow."""
    print("\n🚀 Hello World MCP Application")
    print("=" * 60)
    print("Demonstrating the Cage MCP server workflow")
    print()

    # Initialize client
    client = CageMCPClient()

    # Step 1: Create an agent
    print_section("Step 1: Create an Agent")
    agent = client.create_agent(
        name="Hello World Agent",
        role="implementer",
        config={
            "description": "A simple agent for hello world tasks",
            "capabilities": ["code", "test"],
        },
    )
    print(f"✓ Agent created: {agent['name']} (ID: {agent['id']})")
    print(f"  Role: {agent['role']}")
    print(f"  Created at: {agent['created_at']}")

    agent_id = agent["id"]

    # Step 2: List all agents
    print_section("Step 2: List All Agents")
    agents = client.list_agents()
    print(f"✓ Found {len(agents['items'])} agent(s)")
    for agent in agents["items"]:
        print(f"  - {agent['name']} ({agent['role']}) - ID: {agent['id']}")

    # Step 3: Create a crew
    print_section("Step 3: Create a Crew")
    crew = client.create_crew(
        name="Hello World Crew",
        roles={"implementer": agent_id},
        labels=["demo", "hello-world"],
    )
    print(f"✓ Crew created: {crew['name']} (ID: {crew['id']})")
    print(f"  Roles: {crew.get('roles', {})}")
    print(f"  Labels: {', '.join(crew.get('labels', []))}")

    # Step 4: Invoke the agent with a simple task
    print_section("Step 4: Invoke Agent with Task")
    task = {
        "title": "Hello World Task",
        "description": "Print 'Hello, World!' and demonstrate basic functionality",
        "acceptance": [
            "Output contains 'Hello, World!'",
            "Task completes successfully",
        ],
    }
    print(f"Task: {task['title']}")
    print(f"Description: {task['description']}")
    print(f"Acceptance Criteria: {', '.join(task['acceptance'])}")
    print()

    run = client.invoke_agent(agent_id, task)
    print("✓ Agent invoked successfully")
    print(f"  Run ID: {run['id']}")
    print(f"  Status: {run['status']}")
    print(f"  Kind: {run['kind']}")

    run_id = run["id"]

    # Step 5: Check run status
    print_section("Step 5: Check Run Status")
    run_status = client.get_run(run_id)
    print("✓ Run status retrieved")
    print(f"  Run ID: {run_status['id']}")
    print(f"  Status: {run_status['status']}")
    print(f"  Started at: {run_status.get('started_at', 'N/A')}")
    print(f"  Completed at: {run_status.get('completed_at', 'N/A')}")

    # Step 6: List all runs for this agent
    print_section("Step 6: List All Runs for Agent")
    runs = client.list_runs(agent_id=agent_id)
    print(f"✓ Found {len(runs['items'])} run(s) for agent {agent_id}")
    for run in runs["items"]:
        print(f"  - Run {run['id']}: {run['status']} (kind: {run['kind']})")

    # Summary
    print_section("Summary")
    print("✓ Successfully demonstrated MCP workflow:")
    print(f"  1. Created agent: {agent_id}")
    print("  2. Created crew with 1 agent")
    print("  3. Invoked agent with task")
    print(f"  4. Retrieved run status: {run_status['status']}")
    print()
    print("🎉 Hello World MCP Application completed successfully!")
    print("=" * 60)
    print()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except httpx.HTTPStatusError as e:
        print(f"\n❌ HTTP Error: {e.response.status_code}")
        print(f"Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
