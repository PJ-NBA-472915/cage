"""
Integration tests for MCP JSON-RPC protocol implementation.

Tests verify that the /mcp/rpc endpoint correctly implements the MCP protocol:
- initialize method for server handshake
- tools/list method to discover available tools
- tools/call method to invoke tools

Requirements:
- MCP server must be running on http://localhost:8765
- All backend services (crew-api, postgres, redis) must be running
"""

import pytest
import httpx

# Base URL for MCP server
MCP_BASE_URL = "http://localhost:8765"

# Mark all tests in this module
pytestmark = [pytest.mark.integration]


class TestMCPProtocol:
    """Test suite for MCP JSON-RPC protocol implementation."""

    def test_initialize_handshake(self):
        """Test MCP initialize method returns server capabilities."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }

        response = httpx.post(f"{MCP_BASE_URL}/mcp/rpc", json=request)

        # Should return 200 OK
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Verify JSON-RPC 2.0 structure
        assert data.get("jsonrpc") == "2.0", "Response must have jsonrpc: 2.0"
        assert data.get("id") == 1, "Response must echo request ID"
        assert "result" in data, "Response must have result field"
        assert "error" not in data, "Response should not have error field"

        # Verify initialize result structure
        result = data["result"]
        assert "protocolVersion" in result, "Result must include protocolVersion"
        assert "capabilities" in result, "Result must include capabilities"
        assert "serverInfo" in result, "Result must include serverInfo"

        # Verify server info
        server_info = result["serverInfo"]
        assert server_info.get("name") == "cage-mcp", "Server name should be cage-mcp"
        assert server_info.get("version") == "1.0.0", "Server version should be 1.0.0"

        print(f"✓ Initialize handshake successful: {server_info}")

    def test_tools_list(self):
        """Test tools/list method returns all registered MCP tools."""
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }

        response = httpx.post(f"{MCP_BASE_URL}/mcp/rpc", json=request)

        # Should return 200 OK
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Verify JSON-RPC 2.0 structure
        assert data.get("jsonrpc") == "2.0"
        assert data.get("id") == 2
        assert "result" in data
        assert "error" not in data

        # Verify tools/list result structure
        result = data["result"]
        assert "tools" in result, "Result must include tools array"

        tools = result["tools"]
        assert isinstance(tools, list), "Tools must be an array"
        assert len(tools) == 12, f"Expected 12 tools, got {len(tools)}"

        # Verify each tool has required fields
        tool_names = []
        for tool in tools:
            assert "name" in tool, "Each tool must have a name"
            assert "description" in tool, "Each tool must have a description"
            assert "inputSchema" in tool, "Each tool must have an inputSchema"
            tool_names.append(tool["name"])

        # Verify expected tools are present
        expected_tools = [
            "rag_query",
            "agent_create", "agent_list", "agent_get", "agent_invoke",
            "crew_create", "crew_list", "crew_get", "crew_run",
            "run_list", "run_get", "run_cancel"
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Tool '{expected_tool}' not found in tools list"

        print(f"✓ Tools/list successful: {len(tools)} tools registered")
        print(f"  Available tools: {', '.join(tool_names)}")

    def test_tools_call_agent_create(self):
        """Test tools/call method with agent_create tool."""
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "agent_create",
                "arguments": {
                    "name": "Test Agent",
                    "role": "implementer",
                    "config": {
                        "description": "A test agent for protocol testing"
                    }
                }
            }
        }

        response = httpx.post(f"{MCP_BASE_URL}/mcp/rpc", json=request, timeout=10.0)

        # Should return 200 OK
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Verify JSON-RPC 2.0 structure
        assert data.get("jsonrpc") == "2.0"
        assert data.get("id") == 3
        assert "result" in data
        assert "error" not in data

        # Verify tools/call result structure
        result = data["result"]
        assert "content" in result, "Result must include content array"
        assert isinstance(result["content"], list), "Content must be an array"
        assert len(result["content"]) > 0, "Content must not be empty"

        # Verify content structure
        content_item = result["content"][0]
        assert content_item.get("type") == "text", "Content type must be text"
        assert "text" in content_item, "Content must include text field"

        # Verify agent was created (ID should be in response text)
        text = content_item["text"]
        assert "Agent created successfully" in text or "ID:" in text, f"Expected success message, got: {text}"

        print(f"✓ Tools/call agent_create successful")
        print(f"  Response: {text[:100]}...")

    def test_tools_call_agent_list(self):
        """Test tools/call method with agent_list tool."""
        request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "agent_list",
                "arguments": {
                    "limit": 10
                }
            }
        }

        response = httpx.post(f"{MCP_BASE_URL}/mcp/rpc", json=request, timeout=10.0)

        # Should return 200 OK
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Verify JSON-RPC 2.0 structure
        assert data.get("jsonrpc") == "2.0"
        assert data.get("id") == 4
        assert "result" in data

        # Verify tools/call result structure
        result = data["result"]
        assert "content" in result
        assert isinstance(result["content"], list)
        assert len(result["content"]) > 0

        # Verify content
        content_item = result["content"][0]
        assert content_item.get("type") == "text"
        text = content_item["text"]
        assert "Found" in text or "agents" in text, f"Expected agent list, got: {text}"

        print(f"✓ Tools/call agent_list successful")
        print(f"  Response: {text[:100]}...")

    def test_invalid_method(self):
        """Test that invalid method names return proper JSON-RPC error."""
        request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "invalid/method",
            "params": {}
        }

        response = httpx.post(f"{MCP_BASE_URL}/mcp/rpc", json=request)

        # Should return 200 OK (errors are in JSON-RPC response, not HTTP status)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()

        # Verify JSON-RPC 2.0 error structure
        assert data.get("jsonrpc") == "2.0"
        assert data.get("id") == 5
        assert "error" in data, "Response must have error field"
        assert "result" not in data, "Response should not have result field on error"

        # Verify error structure
        error = data["error"]
        assert "code" in error, "Error must have code field"
        assert "message" in error, "Error must have message field"
        assert "Method not found" in error["message"] or "invalid" in error["message"].lower()

        print(f"✓ Invalid method handled correctly: {error['message']}")

    def test_malformed_request_missing_jsonrpc(self):
        """Test that malformed requests (missing jsonrpc field) return error."""
        request = {
            "id": 6,
            "method": "initialize",
            "params": {}
            # Missing "jsonrpc": "2.0"
        }

        response = httpx.post(f"{MCP_BASE_URL}/mcp/rpc", json=request)

        # Should return 200 OK
        assert response.status_code == 200

        data = response.json()

        # Verify error response
        assert data.get("jsonrpc") == "2.0", "Error response must include jsonrpc: 2.0"
        assert "error" in data
        assert data["error"]["code"] == -32600, "Should return Invalid Request error code"
        assert "jsonrpc version" in data["error"]["message"].lower() or "invalid" in data["error"]["message"].lower()

        print(f"✓ Malformed request handled correctly: {data['error']['message']}")

    def test_malformed_request_missing_method(self):
        """Test that requests missing method field return error."""
        request = {
            "jsonrpc": "2.0",
            "id": 7,
            "params": {}
            # Missing "method"
        }

        response = httpx.post(f"{MCP_BASE_URL}/mcp/rpc", json=request)

        # Should return 200 OK
        assert response.status_code == 200

        data = response.json()

        # Verify error response
        assert data.get("jsonrpc") == "2.0"
        assert "error" in data
        assert data["error"]["code"] == -32600, "Should return Invalid Request error code"
        assert "method" in data["error"]["message"].lower()

        print(f"✓ Missing method handled correctly: {data['error']['message']}")

    def test_json_rpc_batch_not_supported(self):
        """Test that batch requests (arrays) are handled appropriately."""
        # Send an array of requests (batch)
        requests = [
            {"jsonrpc": "2.0", "id": 8, "method": "tools/list", "params": {}},
            {"jsonrpc": "2.0", "id": 9, "method": "tools/list", "params": {}}
        ]

        response = httpx.post(f"{MCP_BASE_URL}/mcp/rpc", json=requests)

        # Should return 200 OK
        assert response.status_code == 200

        data = response.json()

        # Batch requests should return error (not an array request object)
        assert isinstance(data, dict), "Should return single error object for batch"
        assert "error" in data
        assert data["error"]["code"] == -32600, "Should return Invalid Request for batch"

        print(f"✓ Batch request handled correctly: {data['error']['message']}")


# Standalone execution support
if __name__ == "__main__":
    import sys

    print("🚀 Starting MCP Protocol Integration Tests")
    print("=" * 60)
    print()

    # Check if MCP server is available
    try:
        response = httpx.get(f"{MCP_BASE_URL}/mcp/health", timeout=5)
        if response.status_code != 200:
            print("❌ MCP server not responding")
            sys.exit(1)
    except Exception as e:
        print(f"❌ MCP server not available: {e}")
        sys.exit(1)

    print("✅ MCP server is available")
    print()

    # Run tests
    test_instance = TestMCPProtocol()
    tests = [
        ("Initialize Handshake", test_instance.test_initialize_handshake),
        ("Tools List", test_instance.test_tools_list),
        ("Tools Call - Agent Create", test_instance.test_tools_call_agent_create),
        ("Tools Call - Agent List", test_instance.test_tools_call_agent_list),
        ("Invalid Method Error", test_instance.test_invalid_method),
        ("Malformed Request - Missing jsonrpc", test_instance.test_malformed_request_missing_jsonrpc),
        ("Malformed Request - Missing method", test_instance.test_malformed_request_missing_method),
        ("Batch Request Not Supported", test_instance.test_json_rpc_batch_not_supported),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"🧪 Running {name}...")
        try:
            test_func()
            passed += 1
            print()
        except AssertionError as e:
            print(f"❌ {name} FAILED: {e}")
            failed += 1
            print()
        except Exception as e:
            print(f"❌ {name} FAILED with unexpected error: {e}")
            failed += 1
            print()

    print("=" * 60)
    print(f"📊 Test Summary")
    print("=" * 60)
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print()

    if failed == 0:
        print("✅ All MCP protocol tests passed!")
        sys.exit(0)
    else:
        print(f"❌ {failed} test(s) failed.")
        sys.exit(1)
