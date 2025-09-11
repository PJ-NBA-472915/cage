#!/usr/bin/env python3
"""
Startup script for Cage MCP Server

This script starts the MCP server for RAG functionality.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cage.mcp_server import main

if __name__ == "__main__":
    # Set default environment variables if not set
    if not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = "postgresql://postgres:password@localhost:5432/cage"
    if not os.getenv("REDIS_URL"):
        os.environ["REDIS_URL"] = "redis://localhost:6379"
    
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is required")
        sys.exit(1)
    
    # Run the MCP server
    asyncio.run(main())
