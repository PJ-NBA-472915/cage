"""Cage tools for MCP Streamable HTTP server."""

import argparse
import uvicorn

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(name="cage", json_response=False, stateless_http=False)

@mcp.tool()
async def get_tasks(state: str) -> str:
    """Get a list of tasks with the specified state

    Args:
        state: Options are: "open", "in-progress", "done"
    """
    return [
        "Task 1",
        "Task 2",
        "Task 3"
    ]

if __name__ == "__main__":
    import os
    
    parser = argparse.ArgumentParser(description="MCP Server")
    parser.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", 8765)), help="Port to run the server on")
    parser.add_argument("--host", type=str, default=os.getenv("MCP_HOST", "localhost"), help="Host to run the server on")

    args = parser.parse_args()

    # Start the server with Streamable HTTP transport
    uvicorn.run(mcp.streamable_http_app, host=args.host, port=args.port)
