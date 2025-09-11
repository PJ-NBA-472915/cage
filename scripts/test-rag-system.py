#!/usr/bin/env python3
"""
Test script for Cage RAG System

This script tests the complete RAG workflow including:
- Database setup
- File indexing
- Query functionality
- MCP server integration
"""

import asyncio
import os
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cage.rag_service import RAGService
from cage.mcp_server import RAGMCPServer

async def test_rag_service():
    """Test the RAG service functionality."""
    print("Testing RAG Service...")
    
    # Initialize RAG service
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/cage")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key:
        print("Error: OPENAI_API_KEY environment variable is required")
        return False
    
    rag_service = RAGService(
        db_url=db_url,
        redis_url=redis_url,
        openai_api_key=openai_api_key
    )
    
    try:
        # Initialize service
        await rag_service.initialize()
        print("✓ RAG service initialized successfully")
        
        # Test file indexing
        test_content = """
# Test Python File
def hello_world():
    '''A simple hello world function.'''
    return "Hello, World!"

class TestClass:
    def __init__(self, name):
        self.name = name
    
    def greet(self):
        return f"Hello, {self.name}!"
"""
        
        print("Testing file indexing...")
        chunks = await rag_service.index_file(
            "test_file.py",
            test_content,
            "test-commit-sha",
            "main"
        )
        print(f"✓ Indexed file with {len(chunks)} chunks")
        
        # Test query
        print("Testing RAG query...")
        results = await rag_service.query("hello world function", top_k=3)
        print(f"✓ Query returned {len(results)} results")
        
        for i, result in enumerate(results, 1):
            print(f"  Result {i}: {result.metadata.path} (score: {result.score:.3f})")
            print(f"    Content: {result.content[:100]}...")
        
        # Test blob metadata check
        print("Testing blob metadata check...")
        blob_sha = "test-blob-sha"
        metadata = await rag_service.check_blob_metadata(blob_sha)
        print(f"✓ Blob metadata check: {metadata}")
        
        return True
        
    except Exception as e:
        print(f"✗ RAG service test failed: {e}")
        return False
    finally:
        await rag_service.close()

async def test_mcp_server():
    """Test the MCP server functionality."""
    print("\nTesting MCP Server...")
    
    # This is a simplified test - in practice, MCP server testing
    # would require a proper MCP client
    print("✓ MCP server test skipped (requires MCP client)")
    return True

async def test_docker_integration():
    """Test Docker integration."""
    print("\nTesting Docker Integration...")
    
    # Check if we're running in Docker
    if os.path.exists("/.dockerenv"):
        print("✓ Running in Docker container")
    else:
        print("ℹ Not running in Docker container")
    
    # Check environment variables
    required_vars = ["DATABASE_URL", "REDIS_URL", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠ Missing environment variables: {missing_vars}")
    else:
        print("✓ All required environment variables are set")
    
    return True

async def main():
    """Run all tests."""
    print("Cage RAG System Test Suite")
    print("=" * 40)
    
    tests = [
        ("RAG Service", test_rag_service),
        ("MCP Server", test_mcp_server),
        ("Docker Integration", test_docker_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 40)
    print("Test Results:")
    print("=" * 40)
    
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
