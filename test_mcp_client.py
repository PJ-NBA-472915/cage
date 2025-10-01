#!/usr/bin/env python3
"""
Simple MCP Client Test
Tests the Cage MCP server by listing agents and creating a simple agent.
"""

import json
import sys

import httpx


def test_mcp_health():
    """Test the health endpoint."""
    print("Testing MCP health endpoint...")
    response = httpx.get("http://localhost:8765/mcp/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()
    return response.status_code == 200


def test_mcp_about():
    """Test the about endpoint."""
    print("Testing MCP about endpoint...")
    response = httpx.get("http://localhost:8765/mcp/about")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()
    return response.status_code == 200


def test_mcp_rpc_initialize():
    """Test MCP RPC initialize."""
    print("Testing MCP RPC initialize...")
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    }

    response = httpx.post(
        "http://localhost:8765/mcp/rpc",
        json=request,
        headers={"Content-Type": "application/json"},
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()
    return response.status_code == 200


def test_list_agents():
    """Test listing agents via the crew API."""
    print("Testing agent listing via crew API directly...")
    response = httpx.get(
        "http://crew-api:8000/agents",
        headers={
            "Authorization": "Bearer test-mcp-token",
            "Content-Type": "application/json",
        },
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()
    return response.status_code == 200


def test_create_agent():
    """Test creating an agent via the crew API."""
    print("Testing agent creation via crew API directly...")
    request = {
        "name": "HelloWorld Agent",
        "role": "implementer",
        "config": {"description": "A simple hello world test agent"},
    }

    response = httpx.post(
        "http://crew-api:8000/agents",
        json=request,
        headers={
            "Authorization": "Bearer test-mcp-token",
            "Content-Type": "application/json",
        },
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

    if response.status_code == 200 or response.status_code == 201:
        return response.json()
    return None


def main():
    """Main test runner."""
    print("=" * 60)
    print("MCP Server Test Suite")
    print("=" * 60)
    print()

    tests_passed = 0
    tests_failed = 0

    # Test 1: Health check
    if test_mcp_health():
        tests_passed += 1
        print("✓ Health check passed")
    else:
        tests_failed += 1
        print("✗ Health check failed")
    print()

    # Test 2: About endpoint
    if test_mcp_about():
        tests_passed += 1
        print("✓ About endpoint passed")
    else:
        tests_failed += 1
        print("✗ About endpoint failed")
    print()

    # Test 3: MCP RPC initialize
    if test_mcp_rpc_initialize():
        tests_passed += 1
        print("✓ MCP RPC initialize passed")
    else:
        tests_failed += 1
        print("✗ MCP RPC initialize failed")
    print()

    # Test 4: List agents
    if test_list_agents():
        tests_passed += 1
        print("✓ List agents passed")
    else:
        tests_failed += 1
        print("✗ List agents failed")
    print()

    # Test 5: Create agent
    agent = test_create_agent()
    if agent:
        tests_passed += 1
        print(f"✓ Create agent passed - Agent ID: {agent.get('id')}")
    else:
        tests_failed += 1
        print("✗ Create agent failed")
    print()

    # Summary
    print("=" * 60)
    print(f"Tests Passed: {tests_passed}")
    print(f"Tests Failed: {tests_failed}")
    print("=" * 60)

    return 0 if tests_failed == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
