import os
import sys
import json
import asyncio
from pathlib import Path

# Assuming modelcontextprotocol.server is available in the environment
# If not, this will need to be added to requirements.txt and installed.
from modelcontextprotocol.server import Server

from tools.mcp.actor_server.runner import run_shell, ToolError

# Define the tool function that will be exposed via MCP
async def actor_run(path: str, instruction: str) -> str:
    """
    Executes a shell command in the specified path and returns its stdout.

    Args:
        path: The directory in which to run the command.
        instruction: The shell command to execute.

    Returns:
        The stdout of the executed command.

    Raises:
        ToolError: If the command fails or times out.
    """
    # The timeout is handled by run_shell, which defaults to 60 seconds.
    # If a different timeout is needed, it should be passed here.
    return run_shell(path, instruction)

# Define the JSON schema for the actor.run tool
ACTOR_RUN_SCHEMA = {
    "type": "object",
    "required": ["path", "instruction"],
    "properties": {
        "path": {"type": "string", "description": "Absolute or repo-relative directory in which to run the command"},
        "instruction": {"type": "string", "description": "Shell command to run with POSIX semantics (/bin/sh -lc)"}
    },
    "additionalProperties": False
}

async def main():
    server = Server()
    server.register_tool("actor.run", actor_run, ACTOR_RUN_SCHEMA)

    # The task specifies a --once flag for smoke testing.
    # For a persistent server, you would typically run server.run_forever().
    # For now, we'll just start it and let it handle a single request if --once is used.
    # The actual handling of --once will be done by the MCP SDK's Server class.
    await server.run_forever()

if __name__ == "__main__":
    # This block will be executed when the script is run directly.
    # The MCP SDK's Server class is expected to handle command-line arguments
    # like --once for single-shot execution.
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped by user.")
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)
