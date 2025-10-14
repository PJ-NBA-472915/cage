"""
End-to-end integration test for MCP file operations.

Tests the complete workflow:
1. MCP client → tools/call to create/invoke agent
2. Agent executes task → uses internal files-api
3. Files created/edited in isolated test repository
4. Verify isolation: NO changes to main Cage repository

This test enforces the testing protocol constraint:
- All changes MUST go through MCP server
- NO direct file manipulation allowed
- Test repo is isolated in .scratchpad/

Requirements:
- MCP server running on http://localhost:8765
- All backend services (crew-api, files-api, git-api, postgres, redis) running
- POD_TOKEN environment variable set
"""

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional

import pytest
import httpx

# Base URLs
MCP_BASE_URL = "http://localhost:8765"
FILES_API_BASE_URL = "http://localhost:8010"

# Test repository path
TEST_REPO_PATH = Path(".scratchpad/mcp-e2e-test")

# Mark all tests in this module
pytestmark = [pytest.mark.integration, pytest.mark.e2e]


@pytest.fixture(scope="module")
def test_repo():
    """Create isolated test repository in .scratchpad/."""
    # Create test repo directory
    test_repo = Path(TEST_REPO_PATH)
    if test_repo.exists():
        shutil.rmtree(test_repo)

    test_repo.mkdir(parents=True, exist_ok=True)

    # Initialize git repository
    subprocess.run(["git", "init"], cwd=test_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@cage.local"],
        cwd=test_repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Cage Test"],
        cwd=test_repo,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    readme_path = test_repo / "README.md"
    readme_path.write_text("# Test Repository\n\nFor MCP E2E testing\n")
    subprocess.run(["git", "add", "."], cwd=test_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=test_repo,
        check=True,
        capture_output=True,
    )

    print(f"✓ Created test repository: {test_repo.absolute()}")

    yield test_repo

    # Cleanup after tests
    if test_repo.exists():
        shutil.rmtree(test_repo)
        print(f"✓ Cleaned up test repository")


@pytest.fixture(scope="module")
def main_repo_snapshot():
    """Capture main repository state before tests."""
    # Get git status of main repo
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=True,
    )

    initial_status = result.stdout

    yield initial_status

    # Verify main repo is unchanged after tests
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=True,
    )

    final_status = result.stdout

    # Filter out .scratchpad changes (expected)
    initial_filtered = [line for line in initial_status.split("\n") if ".scratchpad" not in line]
    final_filtered = [line for line in final_status.split("\n") if ".scratchpad" not in line]

    assert initial_filtered == final_filtered, (
        f"Main repository was modified during E2E test!\n"
        f"Initial: {initial_filtered}\n"
        f"Final: {final_filtered}"
    )

    print("✓ Main repository isolation verified - no unexpected changes")


def mcp_rpc_call(method: str, params: Dict[str, Any], rpc_id: int = 1, timeout: float = 10.0) -> Dict[str, Any]:
    """
    Make an MCP JSON-RPC call.

    Args:
        method: RPC method name
        params: Method parameters
        rpc_id: JSON-RPC request ID
        timeout: Request timeout in seconds

    Returns:
        Result from JSON-RPC response

    Raises:
        AssertionError: If RPC call fails
    """
    request = {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "method": method,
        "params": params
    }

    response = httpx.post(f"{MCP_BASE_URL}/mcp/rpc", json=request, timeout=timeout)

    assert response.status_code == 200, f"RPC call failed: {response.status_code} - {response.text}"

    data = response.json()

    assert data.get("jsonrpc") == "2.0", "Invalid JSON-RPC response"
    assert "error" not in data, f"RPC error: {data.get('error')}"
    assert "result" in data, "No result in RPC response"

    return data["result"]


def wait_for_run_completion(run_id: str, timeout: int = 60, poll_interval: int = 2) -> Dict[str, Any]:
    """
    Poll run status until completed or failed.

    Args:
        run_id: Run UUID to monitor
        timeout: Maximum time to wait in seconds
        poll_interval: Time between status checks in seconds

    Returns:
        Final run status

    Raises:
        TimeoutError: If run doesn't complete within timeout
        AssertionError: If run fails
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        result = mcp_rpc_call("tools/call", {
            "name": "run_get",
            "arguments": {"run_id": run_id}
        })

        # Extract status from result
        content = result.get("content", [])
        if content:
            text = content[0].get("text", "")

            # Parse status from text (format: "Status: <status>")
            if "Status:" in text:
                for line in text.split("\n"):
                    if "Status:" in line:
                        status = line.split("Status:")[1].strip()

                        if status in ["completed", "success"]:
                            print(f"✓ Run {run_id} completed successfully")
                            return {"id": run_id, "status": status, "text": text}
                        elif status in ["failed", "error"]:
                            raise AssertionError(f"Run {run_id} failed: {text}")

        time.sleep(poll_interval)

    raise TimeoutError(f"Run {run_id} did not complete within {timeout} seconds")


class TestMCPE2EFiles:
    """End-to-end tests for file operations through MCP."""

    def test_e2e_create_file_via_mcp(self, test_repo, main_repo_snapshot):
        """Test creating a file through MCP workflow."""
        print("\n" + "=" * 60)
        print("TEST: Create File via MCP")
        print("=" * 60)

        # Step 1: Create an agent
        print("\n1. Creating agent...")
        result = mcp_rpc_call("tools/call", {
            "name": "agent_create",
            "arguments": {
                "name": "File Creator Agent",
                "role": "implementer",
                "config": {"description": "Agent for E2E file creation test"}
            }
        })

        # Extract agent ID from result text
        content_text = result["content"][0]["text"]
        assert "ID:" in content_text, f"No agent ID in response: {content_text}"

        # Parse agent ID (format: "ID: <uuid>")
        agent_id = None
        for line in content_text.split("\n"):
            if "ID:" in line:
                agent_id = line.split("ID:")[1].strip()
                break

        assert agent_id, f"Could not parse agent ID from: {content_text}"
        print(f"✓ Created agent: {agent_id}")

        # Step 2: Invoke agent with file creation task
        print("\n2. Invoking agent with file creation task...")

        # Note: This is a simplified test - in reality, agents would need to
        # be configured to use the files-api to create files. For now, we're
        # testing that the invocation workflow works.
        task = {
            "title": "Create test file",
            "description": f"Create a file named 'test-{int(time.time())}.txt' with content 'Hello from MCP E2E test'",
            "acceptance": [
                "File is created in the repository",
                "File contains the specified content"
            ]
        }

        result = mcp_rpc_call("tools/call", {
            "name": "agent_invoke",
            "arguments": {
                "agent_id": agent_id,
                "task": task,
                "timeout_s": 60
            }
        }, timeout=15.0)

        # Extract run ID
        content_text = result["content"][0]["text"]
        assert "Run ID:" in content_text, f"No run ID in response: {content_text}"

        run_id = None
        for line in content_text.split("\n"):
            if "Run ID:" in line:
                run_id = line.split("Run ID:")[1].strip()
                break

        assert run_id, f"Could not parse run ID from: {content_text}"
        print(f"✓ Agent invoked, run ID: {run_id}")

        # Step 3: Verify run was queued (we can't wait for actual file creation
        # without crew-api actually implementing the file operations)
        print("\n3. Verifying run status...")
        result = mcp_rpc_call("tools/call", {
            "name": "run_get",
            "arguments": {"run_id": run_id}
        })

        content_text = result["content"][0]["text"]
        assert "Run ID:" in content_text
        print(f"✓ Run status retrieved: {run_id}")

        print("\n✅ E2E create file workflow completed successfully")
        print("Note: Actual file creation depends on crew-api agent implementation")

    def test_e2e_create_crew_and_run(self, test_repo, main_repo_snapshot):
        """Test creating a crew and running it through MCP."""
        print("\n" + "=" * 60)
        print("TEST: Create Crew and Run via MCP")
        print("=" * 60)

        # Step 1: Create multiple agents for the crew
        print("\n1. Creating agents for crew...")

        # Create planner agent
        result = mcp_rpc_call("tools/call", {
            "name": "agent_create",
            "arguments": {
                "name": "Planner Agent",
                "role": "planner",
                "config": {"description": "Plans file operations"}
            }
        })
        planner_id = None
        for line in result["content"][0]["text"].split("\n"):
            if "ID:" in line:
                planner_id = line.split("ID:")[1].strip()
                break
        assert planner_id
        print(f"✓ Created planner agent: {planner_id}")

        # Create implementer agent
        result = mcp_rpc_call("tools/call", {
            "name": "agent_create",
            "arguments": {
                "name": "Implementer Agent",
                "role": "implementer",
                "config": {"description": "Implements file operations"}
            }
        })
        implementer_id = None
        for line in result["content"][0]["text"].split("\n"):
            if "ID:" in line:
                implementer_id = line.split("ID:")[1].strip()
                break
        assert implementer_id
        print(f"✓ Created implementer agent: {implementer_id}")

        # Step 2: Create crew with role mappings
        print("\n2. Creating crew...")
        result = mcp_rpc_call("tools/call", {
            "name": "crew_create",
            "arguments": {
                "name": "File Operations Crew",
                "roles": {
                    "planner": planner_id,
                    "implementer": implementer_id
                },
                "labels": ["e2e-test", "file-operations"]
            }
        })

        crew_id = None
        for line in result["content"][0]["text"].split("\n"):
            if "ID:" in line:
                crew_id = line.split("ID:")[1].strip()
                break
        assert crew_id
        print(f"✓ Created crew: {crew_id}")

        # Step 3: Run crew with task
        print("\n3. Running crew with task...")
        task = {
            "title": "Create and edit files",
            "description": "Create a new Python file and edit README",
            "acceptance": [
                "New Python file created with proper structure",
                "README updated with project information"
            ]
        }

        result = mcp_rpc_call("tools/call", {
            "name": "crew_run",
            "arguments": {
                "crew_id": crew_id,
                "task": task,
                "strategy": "sequential",
                "timeout_s": 120
            }
        }, timeout=15.0)

        run_id = None
        for line in result["content"][0]["text"].split("\n"):
            if "Run ID:" in line:
                run_id = line.split("Run ID:")[1].strip()
                break
        assert run_id
        print(f"✓ Crew run started: {run_id}")

        # Step 4: Verify run status
        print("\n4. Verifying run status...")
        result = mcp_rpc_call("tools/call", {
            "name": "run_get",
            "arguments": {"run_id": run_id}
        })

        content_text = result["content"][0]["text"]
        assert "Run ID:" in content_text
        assert "Kind: crew" in content_text or "crew" in content_text.lower()
        print(f"✓ Crew run status retrieved")

        print("\n✅ E2E crew workflow completed successfully")

    def test_isolation_enforcement(self, test_repo, main_repo_snapshot):
        """Test that isolation is enforced - main repo is not modified."""
        print("\n" + "=" * 60)
        print("TEST: Isolation Enforcement")
        print("=" * 60)

        # This test primarily relies on the main_repo_snapshot fixture
        # which validates isolation in its teardown

        print("\n1. Checking test repository exists...")
        assert test_repo.exists(), "Test repository should exist"
        assert (test_repo / ".git").exists(), "Test repository should be a git repo"
        print(f"✓ Test repository exists: {test_repo.absolute()}")

        print("\n2. Checking main repository...")
        main_repo = Path.cwd()
        assert main_repo != test_repo, "Main and test repos should be different"
        print(f"✓ Main repository: {main_repo.absolute()}")

        print("\n3. Isolation verification will occur in fixture teardown...")
        print("  - Comparing git status before and after tests")
        print("  - Filtering out expected .scratchpad changes")
        print("  - Asserting no other files modified")

        print("\n✅ Isolation check passed (full verification in teardown)")


# Standalone execution support
if __name__ == "__main__":
    import sys

    print("🚀 Starting MCP E2E File Operations Tests")
    print("=" * 60)
    print()

    # Check MCP server availability
    try:
        response = httpx.get(f"{MCP_BASE_URL}/mcp/health", timeout=5)
        if response.status_code != 200:
            print("❌ MCP server not responding")
            sys.exit(1)
    except Exception as e:
        print(f"❌ MCP server not available: {e}")
        sys.exit(1)

    print("✅ MCP server is available")

    # Check files API availability
    try:
        response = httpx.get(f"{FILES_API_BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Files API not responding")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Files API not available: {e}")
        sys.exit(1)

    print("✅ Files API is available")
    print()

    # Setup test repo
    test_repo = Path(TEST_REPO_PATH)
    if test_repo.exists():
        shutil.rmtree(test_repo)

    test_repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=test_repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@cage.local"], cwd=test_repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Cage Test"], cwd=test_repo, check=True, capture_output=True)

    readme_path = test_repo / "README.md"
    readme_path.write_text("# Test Repository\n\nFor MCP E2E testing\n")
    subprocess.run(["git", "add", "."], cwd=test_repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=test_repo, check=True, capture_output=True)

    print(f"✓ Created test repository: {test_repo.absolute()}")
    print()

    # Capture main repo state
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=True,
    )
    initial_status = result.stdout

    # Run tests
    test_instance = TestMCPE2EFiles()
    tests = [
        ("Create File via MCP", lambda: test_instance.test_e2e_create_file_via_mcp(test_repo, initial_status)),
        ("Create Crew and Run", lambda: test_instance.test_e2e_create_crew_and_run(test_repo, initial_status)),
        ("Isolation Enforcement", lambda: test_instance.test_isolation_enforcement(test_repo, initial_status)),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ {name} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ {name} FAILED with unexpected error: {e}")
            failed += 1

    # Cleanup
    if test_repo.exists():
        shutil.rmtree(test_repo)
        print(f"\n✓ Cleaned up test repository")

    # Verify isolation
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=True,
    )
    final_status = result.stdout

    initial_filtered = [line for line in initial_status.split("\n") if ".scratchpad" not in line and line.strip()]
    final_filtered = [line for line in final_status.split("\n") if ".scratchpad" not in line and line.strip()]

    if initial_filtered != final_filtered:
        print(f"\n❌ ISOLATION VIOLATION: Main repository was modified!")
        print(f"Initial: {initial_filtered}")
        print(f"Final: {final_filtered}")
        failed += 1
    else:
        print("\n✓ Isolation verified - main repository unchanged")

    print("\n" + "=" * 60)
    print(f"📊 Test Summary")
    print("=" * 60)
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print()

    if failed == 0:
        print("✅ All E2E tests passed!")
        sys.exit(0)
    else:
        print(f"❌ {failed} test(s) failed.")
        sys.exit(1)
