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
    tasks = [
        "Task 1",
        "Task 2", 
        "Task 3"
    ]
    return f"Tasks with state '{state}': {', '.join(tasks)}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run MCP Streamable HTTP based server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to listen on")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on")
    args = parser.parse_args()

    # Start the server with Streamable HTTP transport
    uvicorn.run(mcp.streamable_http_app, host=args.host, port=args.port)
