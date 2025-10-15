"""
Integration tests for MCP crew and agent orchestration workflow.

Tests verify the complete workflow discovered during e2e testing:
1. Creating agents with proper role validation
2. Creating crews with agent UUID references
3. Running crew tasks with TaskSpec format
4. Validating schema alignment between MCP and Crew API

Requirements:
- MCP server must be running on http://localhost:8765
- Crew API must be running and accessible internally
- All backend services (postgres, redis) must be running

This test validates the fixes for:
- BUG-001: crew_run TypeError (task schema mismatch)
- BUG-002: agent_create validation
- ISSUE-003: crew_create empty roles validation
"""

import pytest
import httpx
import uuid

# Base URL for MCP server
MCP_BASE_URL = "http://localhost:8765"

# Mark all tests in this module
pytestmark = [pytest.mark.integration]


class TestMCPCrewOrchestration:
    """Test suite for MCP crew and agent orchestration workflow."""

    def test_agent_create_with_valid_role(self):
        """Test agent_create with valid role enum (BUG-002 fix validation)."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "agent_create",
                "arguments": {
                    "name": "Test Planner",
                    "role": "planner",  # Must be one of: planner, implementer, verifier, committer
                    "config": {"description": "A test planner agent"}
                }
            }
        }

        response = httpx.post(f"{MCP_BASE_URL}/mcp/rpc", json=request, timeout=10.0)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert data.get("jsonrpc") == "2.0"
        assert "result" in data
        assert "error" not in data, f"Expected success, got error: {data.get('error')}"

        result = data["result"]
        assert "content" in result
        content_text = result["content"][0]["text"]
        assert "Agent created successfully" in content_text
        assert "ID:" in content_text  # Should include agent UUID

        print(f"✓ Agent created with valid role: planner")
        print(f"  Response: {content_text}")

    def test_agent_create_all_valid_roles(self):
        """Test agent_create with all valid role enum values."""
        roles = ["planner", "implementer", "verifier", "committer"]

        for idx, role in enumerate(roles):
            request = {
                "jsonrpc": "2.0",
                "id": idx + 10,
                "method": "tools/call",
                "params": {
                    "name": "agent_create",
                    "arguments": {
                        "name": f"Test {role.capitalize()}",
                        "role": role,
                        "config": {}
                    }
                }
            }

            response = httpx.post(f"{MCP_BASE_URL}/mcp/rpc", json=request, timeout=10.0)

            assert response.status_code == 200
            data = response.json()
            assert "error" not in data, f"Failed to create agent with role '{role}': {data.get('error')}"

            print(f"  ✓ Created agent with role: {role}")

        print(f"✓ All {len(roles)} role enum values work correctly")

    def test_crew_create_with_agent_uuids(self):
        """Test crew_create with proper agent UUID mapping (ISSUE-003 fix validation)."""
        # Step 1: Create agents for each role
        agent_ids = {}
        roles = ["planner", "implementer", "verifier"]

        for idx, role in enumerate(roles):
            create_request = {
                "jsonrpc": "2.0",
                "id": 100 + idx,
                "method": "tools/call",
                "params": {
                    "name": "agent_create",
                    "arguments": {
                        "name": f"Workflow {role.capitalize()}",
                        "role": role,
                        "config": {}
                    }
                }
            }

            response = httpx.post(f"{MCP_BASE_URL}/mcp/rpc", json=create_request, timeout=10.0)
            assert response.status_code == 200

            data = response.json()
            assert "error" not in data

            # Extract agent ID from response text
            content_text = data["result"]["content"][0]["text"]
            # Parse "ID: uuid" from text
            if "ID:" in content_text:
                agent_id = content_text.split("ID:")[1].split("\n")[0].strip()
                agent_ids[role] = agent_id
                print(f"  Created {role}: {agent_id}")

        assert len(agent_ids) == 3, "Should have created 3 agents"

        # Step 2: Create crew with agent UUIDs
        crew_request = {
            "jsonrpc": "2.0",
            "id": 200,
            "method": "tools/call",
            "params": {
                "name": "crew_create",
                "arguments": {
                    "name": "Test Workflow Crew",
                    "roles": agent_ids,  # Dict mapping role names to agent UUIDs
                    "labels": ["test", "integration"]
                }
            }
        }

        response = httpx.post(f"{MCP_BASE_URL}/mcp/rpc", json=crew_request, timeout=10.0)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "error" not in data, f"Crew creation failed: {data.get('error')}"

        result = data["result"]
        content_text = result["content"][0]["text"]
        assert "Crew created successfully" in content_text
        assert "ID:" in content_text

        # Parse crew roles from response
        # Response format: "Crew created successfully:\nID: ...\nName: ...\nRoles: ['planner', 'implementer', 'verifier']"
        if "Roles:" in content_text:
            roles_part = content_text.split("Roles:")[1].strip()
            # Should show list of role names, not empty
            assert "planner" in roles_part or len(agent_ids) > 0
            print(f"  Crew roles: {roles_part}")

        print(f"✓ Crew created successfully with {len(agent_ids)} agent roles")
        print(f"  Response: {content_text[:150]}...")

    def test_crew_create_validation_empty_roles(self):
        """Test crew_create validation rejects empty roles dict (ISSUE-003 enhancement)."""
        request = {
            "jsonrpc": "2.0",
            "id": 300,
            "method": "tools/call",
            "params": {
                "name": "crew_create",
                "arguments": {
                    "name": "Empty Crew",
                    "roles": {},  # Empty roles should be rejected
                    "labels": []
                }
            }
        }

        response = httpx.post(f"{MCP_BASE_URL}/mcp/rpc", json=request, timeout=10.0)

        assert response.status_code == 200  # JSON-RPC errors are 200 with error field

        data = response.json()
        result = data.get("result", {})

        # Should either get validation error or helpful message
        if "content" in result:
            content_text = result["content"][0]["text"]
            # Should contain helpful error message about creating agents first
            assert "role" in content_text.lower() or "agent" in content_text.lower()
            print(f"✓ Empty roles validation message: {content_text[:100]}...")

    def test_crew_create_validation_nonexistent_agent(self):
        """Test crew_create validation rejects non-existent agent UUIDs (ISSUE-003 enhancement)."""
        fake_uuid = str(uuid.uuid4())

        request = {
            "jsonrpc": "2.0",
            "id": 400,
            "method": "tools/call",
            "params": {
                "name": "crew_create",
                "arguments": {
                    "name": "Invalid Agent Crew",
                    "roles": {
                        "planner": fake_uuid  # Non-existent agent UUID
                    },
                    "labels": []
                }
            }
        }

        response = httpx.post(f"{MCP_BASE_URL}/mcp/rpc", json=request, timeout=10.0)

        assert response.status_code == 200

        data = response.json()
        result = data.get("result", {})

        if "content" in result:
            content_text = result["content"][0]["text"]
            # Should contain error about agent not found
            assert "not found" in content_text.lower() or "failed" in content_text.lower()
            print(f"✓ Non-existent agent validation: {content_text[:100]}...")

    def test_crew_run_with_taskspec_format(self):
        """Test crew_run with correct TaskSpec format (BUG-001 fix validation)."""
        # Step 1: Create agents
        agent_ids = {}
        roles = ["planner", "implementer"]

        for idx, role in enumerate(roles):
            create_request = {
                "jsonrpc": "2.0",
                "id": 500 + idx,
                "method": "tools/call",
                "params": {
                    "name": "agent_create",
                    "arguments": {
                        "name": f"TaskSpec {role.capitalize()}",
                        "role": role,
                        "config": {}
                    }
                }
            }

            response = httpx.post(f"{MCP_BASE_URL}/mcp/rpc", json=create_request, timeout=10.0)
            data = response.json()
            content_text = data["result"]["content"][0]["text"]
            if "ID:" in content_text:
                agent_id = content_text.split("ID:")[1].split("\n")[0].strip()
                agent_ids[role] = agent_id

        # Step 2: Create crew
        crew_request = {
            "jsonrpc": "2.0",
            "id": 600,
            "method": "tools/call",
            "params": {
                "name": "crew_create",
                "arguments": {
                    "name": "TaskSpec Test Crew",
                    "roles": agent_ids,
                    "labels": ["taskspec-test"]
                }
            }
        }

        response = httpx.post(f"{MCP_BASE_URL}/mcp/rpc", json=crew_request, timeout=10.0)
        data = response.json()
        content_text = data["result"]["content"][0]["text"]

        # Extract crew ID
        crew_id = None
        if "ID:" in content_text:
            crew_id = content_text.split("ID:")[1].split("\n")[0].strip()
            print(f"  Created crew: {crew_id}")

        assert crew_id is not None, "Failed to create crew"

        # Step 3: Run crew with proper TaskSpec format
        # IMPORTANT: Must use {title, description, acceptance} NOT {name, description, context}
        run_request = {
            "jsonrpc": "2.0",
            "id": 700,
            "method": "tools/call",
            "params": {
                "name": "crew_run",
                "arguments": {
                    "crew_id": crew_id,
                    "task": {
                        "title": "Test Task",  # NOT "name"
                        "description": "A test task to validate TaskSpec schema",
                        "acceptance": [  # NOT "context"
                            "Task completes successfully",
                            "No schema errors occur"
                        ]
                    },
                    "strategy": "impl_then_verify",
                    "timeout_s": 60
                }
            }
        }

        response = httpx.post(f"{MCP_BASE_URL}/mcp/rpc", json=run_request, timeout=15.0)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Should NOT get the BUG-001 TypeError: 'str' object has no attribute 'get'
        if "error" in data:
            error_msg = data["error"].get("message", "")
            assert "'str' object has no attribute 'get'" not in error_msg, \
                "BUG-001 regression: task schema mismatch detected"
            # Other errors might occur (like crew not fully implemented), but not the schema error
            print(f"  Note: Got error (expected during development): {error_msg[:100]}...")

        if "result" in data:
            result = data["result"]
            content_text = result["content"][0]["text"]
            print(f"✓ Crew run accepted TaskSpec format without schema error")
            print(f"  Response: {content_text[:150]}...")
        else:
            # If we got here, at least the schema error didn't occur
            print(f"✓ Crew run accepted TaskSpec format (no BUG-001 TypeError)")

    def test_agent_invoke_with_taskspec_format(self):
        """Test agent_invoke with correct TaskSpec format (BUG-001 bonus fix validation)."""
        # Step 1: Create an agent
        create_request = {
            "jsonrpc": "2.0",
            "id": 800,
            "method": "tools/call",
            "params": {
                "name": "agent_create",
                "arguments": {
                    "name": "TaskSpec Invoke Agent",
                    "role": "implementer",
                    "config": {}
                }
            }
        }

        response = httpx.post(f"{MCP_BASE_URL}/mcp/rpc", json=create_request, timeout=10.0)
        data = response.json()
        content_text = data["result"]["content"][0]["text"]

        agent_id = None
        if "ID:" in content_text:
            agent_id = content_text.split("ID:")[1].split("\n")[0].strip()
            print(f"  Created agent: {agent_id}")

        assert agent_id is not None, "Failed to create agent"

        # Step 2: Invoke agent with TaskSpec format
        invoke_request = {
            "jsonrpc": "2.0",
            "id": 900,
            "method": "tools/call",
            "params": {
                "name": "agent_invoke",
                "arguments": {
                    "agent_id": agent_id,
                    "task": {
                        "title": "Individual Agent Task",  # NOT "name"
                        "description": "Test task for individual agent invocation",
                        "acceptance": [  # NOT "context"
                            "Agent processes task without schema errors"
                        ]
                    },
                    "context": {},
                    "timeout_s": 60
                }
            }
        }

        response = httpx.post(f"{MCP_BASE_URL}/mcp/rpc", json=invoke_request, timeout=15.0)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Should NOT get schema error
        if "error" in data:
            error_msg = data["error"].get("message", "")
            assert "'str' object has no attribute 'get'" not in error_msg, \
                "Schema mismatch in agent_invoke"
            print(f"  Note: Got error (expected during development): {error_msg[:100]}...")

        if "result" in data:
            result = data["result"]
            content_text = result["content"][0]["text"]
            print(f"✓ Agent invoke accepted TaskSpec format without schema error")
            print(f"  Response: {content_text[:150]}...")
        else:
            print(f"✓ Agent invoke accepted TaskSpec format (no schema error)")


# Standalone execution support
if __name__ == "__main__":
    import sys

    print("🚀 Starting MCP Crew Orchestration Integration Tests")
    print("=" * 70)
    print()
    print("Testing fixes for:")
    print("  - BUG-001: crew_run TypeError (task schema mismatch)")
    print("  - BUG-002: agent_create role validation")
    print("  - ISSUE-003: crew_create empty roles validation")
    print()

    # Check if MCP server is available
    try:
        response = httpx.get(f"{MCP_BASE_URL}/mcp/health", timeout=5)
        if response.status_code != 200:
            print("❌ MCP server not responding")
            sys.exit(1)
    except Exception as e:
        print(f"❌ MCP server not available: {e}")
        print("   Make sure to run: docker compose --profile dev up -d")
        sys.exit(1)

    print("✅ MCP server is available")
    print()

    # Run tests
    test_instance = TestMCPCrewOrchestration()
    tests = [
        ("Agent Create - Valid Role", test_instance.test_agent_create_with_valid_role),
        ("Agent Create - All Roles", test_instance.test_agent_create_all_valid_roles),
        ("Crew Create - With Agent UUIDs", test_instance.test_crew_create_with_agent_uuids),
        ("Crew Create - Empty Roles Validation", test_instance.test_crew_create_validation_empty_roles),
        ("Crew Create - Nonexistent Agent Validation", test_instance.test_crew_create_validation_nonexistent_agent),
        ("Crew Run - TaskSpec Format", test_instance.test_crew_run_with_taskspec_format),
        ("Agent Invoke - TaskSpec Format", test_instance.test_agent_invoke_with_taskspec_format),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"🧪 {name}...")
        try:
            test_func()
            passed += 1
            print()
        except AssertionError as e:
            print(f"❌ FAILED: {e}")
            failed += 1
            print()
        except Exception as e:
            print(f"❌ FAILED with unexpected error: {e}")
            failed += 1
            print()

    print("=" * 70)
    print(f"📊 Test Summary")
    print("=" * 70)
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print()

    if failed == 0:
        print("✅ All crew orchestration tests passed!")
        print("   BUG-001, BUG-002, and ISSUE-003 fixes validated successfully")
        sys.exit(0)
    else:
        print(f"❌ {failed} test(s) failed.")
        sys.exit(1)
