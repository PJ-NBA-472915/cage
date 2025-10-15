"""
Cage MCP Server

Model Context Protocol server for Cage API integration.
"""

import argparse
import json
import logging
import sys
import time
import uuid
from typing import Any, Dict, Optional

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from mcp.server import Server

from src.cage.mcp.settings import settings

# Global MCP server instance
mcp_server: Optional[Server] = None

# Global ASGI app (for uvicorn)
app: Optional[FastAPI] = None


class JsonlFormatter(logging.Formatter):
    """JSONL formatter for structured logging."""

    def __init__(self, service_name: str = "cage-mcp"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSONL."""
        log_entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime(record.created)),
            "level": record.levelname,
            "service": self.service_name,
            "msg": record.getMessage(),
        }

        # Add optional fields if present
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "actor"):
            log_entry["actor"] = record.actor
        if hasattr(record, "tool"):
            log_entry["tool"] = record.tool
        if hasattr(record, "route"):
            log_entry["route"] = record.route
        if hasattr(record, "status"):
            log_entry["status"] = record.status
        if hasattr(record, "error"):
            log_entry["error"] = record.error

        return json.dumps(log_entry)


def setup_logging():
    """Setup JSONL logging configuration."""
    import os
    from pathlib import Path
    from logging.handlers import TimedRotatingFileHandler

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create JSONL formatter
    formatter = JsonlFormatter(service_name=settings.service_name)

    # Setup file logging (to be picked up by Promtail)
    log_dir = Path(os.environ.get("LOG_DIR", "/app/logs"))
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create service subdirectory
    service_dir = log_dir / "mcp"
    service_dir.mkdir(parents=True, exist_ok=True)

    # Create log file with .jsonl extension
    log_file = service_dir / "mcp.jsonl"

    # Create rotating file handler (daily rotation)
    file_handler = TimedRotatingFileHandler(
        filename=str(log_file),
        when="midnight",
        interval=1,
        backupCount=30,  # Keep 30 days of logs
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Also keep stdout handler for container logs
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)


def create_cli_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Cage MCP Server - Model Context Protocol server for Cage API integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m cage.mcp.server                    # Run with defaults
  python -m cage.mcp.server --port 8766        # Run on custom port
  python -m cage.mcp.server --host 127.0.0.1   # Run on localhost only
        """,
    )

    parser.add_argument(
        "--host",
        default=settings.host,
        help=f"Host to bind to (default: {settings.host})",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=settings.port,
        help=f"Port to bind to (default: {settings.port})",
    )

    parser.add_argument(
        "--log-level",
        default=settings.log_level,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help=f"Log level (default: {settings.log_level})",
    )

    return parser


def create_mcp_server() -> Server:
    """Create and configure the MCP server."""
    logger = logging.getLogger(__name__)

    try:
        # Create MCP server instance
        mcp = Server("cage")

        # Register MCP tools
        register_mcp_tools(mcp)

        logger.info("MCP server instance created successfully with tools registered")
        return mcp

    except Exception as e:
        logger.error(f"Failed to create MCP server: {e}")
        raise


def register_mcp_tools(mcp: Server):
    """Register all MCP tools with the server."""
    logger = logging.getLogger(__name__)

    # Define available tools - ONLY crew/agent/run management (no direct file/git access)
    tools = [
        {
            "name": "rag_query",
            "description": "Query the RAG system for relevant information",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "top_k": {
                        "type": "integer",
                        "description": "Number of top results to return",
                        "default": 8,
                    },
                    "filters": {
                        "type": "object",
                        "description": "Optional filters to apply",
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "agent_create",
            "description": "Create a new AI agent",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the agent"},
                    "role": {
                        "type": "string",
                        "enum": ["planner", "implementer", "verifier", "committer"],
                        "description": "Role of the agent (planner, implementer, verifier, or committer)",
                    },
                    "config": {
                        "type": "object",
                        "description": "Optional configuration for the agent",
                    },
                },
                "required": ["name", "role"],
            },
        },
        {
            "name": "agent_list",
            "description": "List available agents with optional filtering",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "role": {"type": "string", "description": "Filter by agent role"},
                    "q": {
                        "type": "string",
                        "description": "Search query for agent names",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of agents to return",
                        "default": 50,
                    },
                    "cursor": {"type": "string", "description": "Pagination cursor"},
                },
                "required": [],
            },
        },
        {
            "name": "agent_get",
            "description": "Get a specific agent by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "UUID of the agent to retrieve",
                    }
                },
                "required": ["agent_id"],
            },
        },
        {
            "name": "agent_invoke",
            "description": "Invoke a single agent with a task",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "UUID of the agent to invoke",
                    },
                    "task": {
                        "type": "object",
                        "description": "Task specification",
                        "properties": {
                            "title": {"type": "string", "description": "Task title"},
                            "description": {
                                "type": "string",
                                "description": "Task description",
                            },
                            "acceptance": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Acceptance criteria",
                            },
                        },
                        "required": ["title", "description", "acceptance"],
                    },
                    "context": {
                        "type": "object",
                        "description": "Additional context for the task",
                    },
                    "timeout_s": {
                        "type": "integer",
                        "description": "Timeout in seconds",
                        "default": 600,
                    },
                },
                "required": ["agent_id", "task"],
            },
        },
        {
            "name": "crew_create",
            "description": "Create a new crew of AI agents with role assignments. IMPORTANT: Agents must be created first using agent_create, then their UUIDs are mapped to roles here.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the crew"},
                    "roles": {
                        "type": "object",
                        "description": "Mapping of role names (e.g., 'planner', 'implementer', 'verifier') to existing agent UUIDs. Create agents first using agent_create.",
                        "additionalProperties": {"type": "string"},
                    },
                    "labels": {
                        "type": "array",
                        "description": "Optional labels for the crew",
                        "items": {"type": "string"},
                    },
                },
                "required": ["name", "roles"],
            },
        },
        {
            "name": "crew_list",
            "description": "List available crews with optional filtering",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "label": {"type": "string", "description": "Filter by crew label"},
                    "q": {
                        "type": "string",
                        "description": "Search query for crew names",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of crews to return",
                        "default": 50,
                    },
                    "cursor": {"type": "string", "description": "Pagination cursor"},
                },
                "required": [],
            },
        },
        {
            "name": "crew_get",
            "description": "Get a specific crew by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "crew_id": {
                        "type": "string",
                        "description": "UUID of the crew to retrieve",
                    }
                },
                "required": ["crew_id"],
            },
        },
        {
            "name": "crew_run",
            "description": "Run a crew task",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "crew_id": {
                        "type": "string",
                        "description": "UUID of the crew to run",
                    },
                    "task": {
                        "type": "object",
                        "description": "Task specification",
                        "properties": {
                            "title": {"type": "string", "description": "Task title"},
                            "description": {
                                "type": "string",
                                "description": "Task description",
                            },
                            "acceptance": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Acceptance criteria",
                            },
                        },
                        "required": ["title", "description", "acceptance"],
                    },
                    "strategy": {"type": "string", "description": "Execution strategy", "default": "impl_then_verify"},
                    "timeout_s": {
                        "type": "integer",
                        "description": "Timeout in seconds",
                        "default": 1200,
                    },
                },
                "required": ["crew_id", "task"],
            },
        },
        {
            "name": "run_list",
            "description": "List runs with optional filtering",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter by run status"},
                    "agent_id": {"type": "string", "description": "Filter by agent ID"},
                    "crew_id": {"type": "string", "description": "Filter by crew ID"},
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of runs to return",
                        "default": 50,
                    },
                    "cursor": {"type": "string", "description": "Pagination cursor"},
                },
                "required": [],
            },
        },
        {
            "name": "run_get",
            "description": "Get a specific run by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "string",
                        "description": "UUID of the run to retrieve",
                    }
                },
                "required": ["run_id"],
            },
        },
        {
            "name": "run_cancel",
            "description": "Cancel a running task",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "string",
                        "description": "UUID of the run to cancel",
                    }
                },
                "required": ["run_id"],
            },
        },
    ]

    async def handle_list_tools(request):
        """Handle list tools request."""
        from mcp.types import ListToolsResult, Tool

        mcp_tools = [Tool(**tool) for tool in tools]
        return ListToolsResult(tools=mcp_tools)

    async def handle_call_tool(request):
        """Handle call tool request."""
        from mcp.types import CallToolResult

        tool_name = request.params.name
        arguments = request.params.arguments or {}

        if tool_name == "rag_query":
            return await rag_query_tool(arguments)
        elif tool_name == "agent_create":
            return await agent_create_tool(arguments)
        elif tool_name == "agent_list":
            return await agent_list_tool(arguments)
        elif tool_name == "agent_get":
            return await agent_get_tool(arguments)
        elif tool_name == "agent_invoke":
            return await agent_invoke_tool(arguments)
        elif tool_name == "crew_create":
            return await crew_create_tool(arguments)
        elif tool_name == "crew_list":
            return await crew_list_tool(arguments)
        elif tool_name == "crew_get":
            return await crew_get_tool(arguments)
        elif tool_name == "crew_run":
            return await crew_run_tool(arguments)
        elif tool_name == "run_list":
            return await run_list_tool(arguments)
        elif tool_name == "run_get":
            return await run_get_tool(arguments)
        elif tool_name == "run_cancel":
            return await run_cancel_tool(arguments)
        else:
            return CallToolResult(
                content=[{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                isError=True,
            )

    async def rag_query_tool(arguments: Dict[str, Any]):
        """Query the RAG system for relevant information."""
        from mcp.types import CallToolResult

        request_id = _request_id()
        query = arguments.get("query", "")
        top_k = arguments.get("top_k", 8)
        filters = arguments.get("filters")

        logger.info(
            "RAG query tool called",
            extra={
                "request_id": request_id,
                "tool": "rag_query",
                "query": query,
                "top_k": top_k,
            },
        )

        try:
            # Prepare request data
            data = {"query": query, "top_k": top_k}
            if filters:
                data["filters"] = filters

            # Call RAG API
            result = await make_api_request(
                "/rag/query", method="POST", data=data, request_id=request_id, base_url=settings.rag_api_base_url
            )

            # Format response as human-readable summary
            if "results" in result and result["results"]:
                summary_parts = [
                    f"Found {len(result['results'])} relevant results for query: '{query}'"
                ]

                for i, hit in enumerate(result["results"][:top_k], 1):
                    file_path = hit.get("file_path", "unknown")
                    score = hit.get("score", 0.0)
                    snippet = hit.get("snippet", "No snippet available")

                    summary_parts.append(
                        f"{i}. {file_path} (score: {score:.3f})\n   {snippet}"
                    )

                summary = "\n\n".join(summary_parts)
            else:
                summary = f"No results found for query: '{query}'"

            logger.info(
                "RAG query completed successfully",
                extra={
                    "request_id": request_id,
                    "tool": "rag_query",
                    "results_count": len(result.get("results", [])),
                },
            )

            return CallToolResult(content=[{"type": "text", "text": summary}])

        except Exception as e:
            logger.error(
                "RAG query tool failed",
                extra={"request_id": request_id, "tool": "rag_query", "error": str(e)},
            )

            return create_mcp_error_response(e, "rag_query", request_id)

    async def agent_create_tool(arguments: Dict[str, Any]):
        """Create a new AI agent."""
        from mcp.types import CallToolResult

        request_id = _request_id()
        name = arguments.get("name", "")
        role = arguments.get("role", "")
        config = arguments.get("config", {})

        logger.info(
            "Agent create tool called",
            extra={
                "request_id": request_id,
                "tool": "agent_create",
                "agent_name": name,
                "agent_role": role,
            },
        )

        try:
            # Prepare request data
            data = {"name": name, "role": role}
            if config:
                data["config"] = config

            # Call crew API
            result = await make_api_request(
                "/agents", method="POST", data=data, request_id=request_id
            )

            logger.info(
                "Agent created successfully",
                extra={
                    "request_id": request_id,
                    "tool": "agent_create",
                    "agent_id": result.get("id"),
                },
            )

            return CallToolResult(
                content=[
                    {
                        "type": "text",
                        "text": f"Agent created successfully:\nID: {result.get('id')}\nName: {result.get('name')}\nRole: {result.get('role')}",
                    }
                ]
            )

        except Exception as e:
            logger.error(
                "Agent create tool failed",
                extra={
                    "request_id": request_id,
                    "tool": "agent_create",
                    "error": str(e),
                },
            )

            return CallToolResult(
                content=[{"type": "text", "text": f"Agent creation failed: {str(e)}"}],
                isError=True,
            )

    async def agent_list_tool(arguments: Dict[str, Any]):
        """List available agents with optional filtering."""
        from mcp.types import CallToolResult

        request_id = _request_id()
        role = arguments.get("role")
        q = arguments.get("q")
        limit = arguments.get("limit", 50)
        cursor = arguments.get("cursor")

        logger.info(
            "Agent list tool called",
            extra={
                "request_id": request_id,
                "tool": "agent_list",
                "role": role,
                "limit": limit,
            },
        )

        try:
            # Build query parameters
            params = {}
            if role:
                params["role"] = role
            if q:
                params["q"] = q
            if limit:
                params["limit"] = limit
            if cursor:
                params["cursor"] = cursor

            # Build URL with query parameters
            endpoint = "/agents"
            if params:
                query_string = "&".join([f"{k}={v}" for k, v in params.items()])
                endpoint = f"{endpoint}?{query_string}"

            # Call crew API
            result = await make_api_request(
                endpoint, method="GET", request_id=request_id
            )

            # Format response
            agents = result.get("items", [])
            summary_parts = [f"Found {len(agents)} agents"]

            for agent in agents:
                summary_parts.append(
                    f"- {agent.get('name')} ({agent.get('role')}) - ID: {agent.get('id')}"
                )

            summary = "\n".join(summary_parts)

            logger.info(
                "Agent list completed successfully",
                extra={
                    "request_id": request_id,
                    "tool": "agent_list",
                    "count": len(agents),
                },
            )

            return CallToolResult(
                content=[{"type": "text", "text": summary, "_meta": {}}]
            )

        except Exception as e:
            logger.error(
                "Agent list tool failed",
                extra={"request_id": request_id, "tool": "agent_list", "error": str(e)},
            )

            return CallToolResult(
                content=[{"type": "text", "text": f"Agent listing failed: {str(e)}"}],
                isError=True,
            )

    async def agent_get_tool(arguments: Dict[str, Any]):
        """Get a specific agent by ID."""
        from mcp.types import CallToolResult

        request_id = _request_id()
        agent_id = arguments.get("agent_id", "")

        logger.info(
            "Agent get tool called",
            extra={"request_id": request_id, "tool": "agent_get", "agent_id": agent_id},
        )

        try:
            # Call crew API
            result = await make_api_request(
                f"/agents/{agent_id}", method="GET", request_id=request_id
            )

            logger.info(
                "Agent retrieved successfully",
                extra={
                    "request_id": request_id,
                    "tool": "agent_get",
                    "agent_id": agent_id,
                },
            )

            return CallToolResult(
                content=[
                    {
                        "type": "text",
                        "text": f"Agent Details:\nID: {result.get('id')}\nName: {result.get('name')}\nRole: {result.get('role')}\nCapabilities: {', '.join(result.get('capabilities', []))}",
                    }
                ]
            )

        except Exception as e:
            logger.error(
                "Agent get tool failed",
                extra={"request_id": request_id, "tool": "agent_get", "error": str(e)},
            )

            return CallToolResult(
                content=[{"type": "text", "text": f"Agent retrieval failed: {str(e)}"}],
                isError=True,
            )

    async def agent_invoke_tool(arguments: Dict[str, Any]):
        """Invoke a single agent with a task."""
        from mcp.types import CallToolResult

        request_id = _request_id()
        agent_id = arguments.get("agent_id", "")
        task = arguments.get("task", {})
        context = arguments.get("context", {})
        timeout_s = arguments.get("timeout_s", 600)

        logger.info(
            "Agent invoke tool called",
            extra={
                "request_id": request_id,
                "tool": "agent_invoke",
                "agent_id": agent_id,
                "task_title": task.get("title"),
            },
        )

        try:
            # Prepare request data
            data = {"task": task}
            if context:
                data["context"] = context
            if timeout_s:
                data["timeout_s"] = timeout_s

            # Call crew API
            result = await make_api_request(
                f"/agents/{agent_id}/invoke",
                method="POST",
                data=data,
                request_id=request_id,
            )

            logger.info(
                "Agent invoked successfully",
                extra={
                    "request_id": request_id,
                    "tool": "agent_invoke",
                    "run_id": result.get("id"),
                },
            )

            return CallToolResult(
                content=[
                    {
                        "type": "text",
                        "text": f"Agent invoked successfully:\nRun ID: {result.get('id')}\nStatus: {result.get('status')}\nKind: {result.get('kind')}",
                    }
                ]
            )

        except Exception as e:
            logger.error(
                "Agent invoke tool failed",
                extra={
                    "request_id": request_id,
                    "tool": "agent_invoke",
                    "error": str(e),
                },
            )

            return CallToolResult(
                content=[
                    {"type": "text", "text": f"Agent invocation failed: {str(e)}"}
                ],
                isError=True,
            )

    async def crew_create_tool(arguments: Dict[str, Any]):
        """Create a new crew of AI agents."""
        from mcp.types import CallToolResult

        request_id = _request_id()
        name = arguments.get("name", "")
        roles = arguments.get("roles", {})
        labels = arguments.get("labels", [])

        logger.info(
            "Crew create tool called",
            extra={
                "request_id": request_id,
                "tool": "crew_create",
                "crew_name": name,
                "role_count": len(roles),
            },
        )

        try:
            # Prepare request data
            data = {"name": name, "roles": roles}
            if labels:
                data["labels"] = labels

            # Call crew API
            result = await make_api_request(
                "/crews", method="POST", data=data, request_id=request_id
            )

            logger.info(
                "Crew created successfully",
                extra={
                    "request_id": request_id,
                    "tool": "crew_create",
                    "crew_id": result.get("id"),
                },
            )

            return CallToolResult(
                content=[
                    {
                        "type": "text",
                        "text": f"Crew created successfully:\nID: {result.get('id')}\nName: {result.get('name')}\nRoles: {list(result.get('roles', {}).keys())}",
                    }
                ]
            )

        except Exception as e:
            logger.error(
                "Crew create tool failed",
                extra={
                    "request_id": request_id,
                    "tool": "crew_create",
                    "error": str(e),
                },
            )

            return CallToolResult(
                content=[{"type": "text", "text": f"Crew creation failed: {str(e)}"}],
                isError=True,
            )

    async def crew_list_tool(arguments: Dict[str, Any]):
        """List available crews with optional filtering."""
        from mcp.types import CallToolResult

        request_id = _request_id()
        label = arguments.get("label")
        q = arguments.get("q")
        limit = arguments.get("limit", 50)
        cursor = arguments.get("cursor")

        logger.info(
            "Crew list tool called",
            extra={
                "request_id": request_id,
                "tool": "crew_list",
                "label": label,
                "limit": limit,
            },
        )

        try:
            # Build query parameters
            params = {}
            if label:
                params["label"] = label
            if q:
                params["q"] = q
            if limit:
                params["limit"] = limit
            if cursor:
                params["cursor"] = cursor

            # Build URL with query parameters
            endpoint = "/crews"
            if params:
                query_string = "&".join([f"{k}={v}" for k, v in params.items()])
                endpoint = f"{endpoint}?{query_string}"

            # Call crew API
            result = await make_api_request(
                endpoint, method="GET", request_id=request_id
            )

            # Format response
            crews = result.get("items", [])
            summary_parts = [f"Found {len(crews)} crews"]

            for crew in crews:
                summary_parts.append(
                    f"- {crew.get('name')} ({len(crew.get('agent_ids', []))} agents) - ID: {crew.get('id')}"
                )

            summary = "\n".join(summary_parts)

            logger.info(
                "Crew list completed successfully",
                extra={
                    "request_id": request_id,
                    "tool": "crew_list",
                    "count": len(crews),
                },
            )

            return CallToolResult(content=[{"type": "text", "text": summary}])

        except Exception as e:
            logger.error(
                "Crew list tool failed",
                extra={"request_id": request_id, "tool": "crew_list", "error": str(e)},
            )

            return CallToolResult(
                content=[{"type": "text", "text": f"Crew listing failed: {str(e)}"}],
                isError=True,
            )

    async def crew_get_tool(arguments: Dict[str, Any]):
        """Get a specific crew by ID."""
        from mcp.types import CallToolResult

        request_id = _request_id()
        crew_id = arguments.get("crew_id", "")

        logger.info(
            "Crew get tool called",
            extra={"request_id": request_id, "tool": "crew_get", "crew_id": crew_id},
        )

        try:
            # Call crew API
            result = await make_api_request(
                f"/crews/{crew_id}", method="GET", request_id=request_id
            )

            logger.info(
                "Crew retrieved successfully",
                extra={
                    "request_id": request_id,
                    "tool": "crew_get",
                    "crew_id": crew_id,
                },
            )

            return CallToolResult(
                content=[
                    {
                        "type": "text",
                        "text": f"Crew Details:\nID: {result.get('id')}\nName: {result.get('name')}\nDescription: {result.get('description')}\nAgents: {len(result.get('agent_ids', []))}\nLabels: {', '.join(result.get('labels', []))}",
                    }
                ]
            )

        except Exception as e:
            logger.error(
                "Crew get tool failed",
                extra={"request_id": request_id, "tool": "crew_get", "error": str(e)},
            )

            return CallToolResult(
                content=[{"type": "text", "text": f"Crew retrieval failed: {str(e)}"}],
                isError=True,
            )

    async def crew_run_tool(arguments: Dict[str, Any]):
        """Run a crew task."""
        from mcp.types import CallToolResult

        request_id = _request_id()
        crew_id = arguments.get("crew_id", "")
        task = arguments.get("task", {})
        strategy = arguments.get("strategy", "impl_then_verify")
        timeout_s = arguments.get("timeout_s", 1200)

        logger.info(
            "Crew run tool called",
            extra={
                "request_id": request_id,
                "tool": "crew_run",
                "crew_id": crew_id,
                "task_title": task.get("title"),
            },
        )

        try:
            # Prepare request data
            data = {"task": task}
            if strategy:
                data["strategy"] = strategy
            if timeout_s:
                data["timeout_s"] = timeout_s

            # Call crew API
            result = await make_api_request(
                f"/crews/{crew_id}/run", method="POST", data=data, request_id=request_id
            )

            logger.info(
                "Crew run started successfully",
                extra={
                    "request_id": request_id,
                    "tool": "crew_run",
                    "run_id": result.get("id"),
                },
            )

            return CallToolResult(
                content=[
                    {
                        "type": "text",
                        "text": f"Crew run started successfully:\nRun ID: {result.get('id')}\nStatus: {result.get('status')}\nKind: {result.get('kind')}",
                    }
                ]
            )

        except Exception as e:
            logger.error(
                "Crew run tool failed",
                extra={"request_id": request_id, "tool": "crew_run", "error": str(e)},
            )

            return CallToolResult(
                content=[{"type": "text", "text": f"Crew run failed: {str(e)}"}],
                isError=True,
            )

    async def run_list_tool(arguments: Dict[str, Any]):
        """List runs with optional filtering."""
        from mcp.types import CallToolResult

        request_id = _request_id()
        status = arguments.get("status")
        agent_id = arguments.get("agent_id")
        crew_id = arguments.get("crew_id")
        limit = arguments.get("limit", 50)
        cursor = arguments.get("cursor")

        logger.info(
            "Run list tool called",
            extra={
                "request_id": request_id,
                "tool": "run_list",
                "status": status,
                "limit": limit,
            },
        )

        try:
            # Build query parameters
            params = {}
            if status:
                params["status"] = status
            if agent_id:
                params["agent_id"] = agent_id
            if crew_id:
                params["crew_id"] = crew_id
            if limit:
                params["limit"] = limit
            if cursor:
                params["cursor"] = cursor

            # Build URL with query parameters
            endpoint = "/runs"
            if params:
                query_string = "&".join([f"{k}={v}" for k, v in params.items()])
                endpoint = f"{endpoint}?{query_string}"

            # Call crew API
            result = await make_api_request(
                endpoint, method="GET", request_id=request_id
            )

            # Format response
            runs = result.get("items", [])
            summary_parts = [f"Found {len(runs)} runs"]

            for run in runs:
                summary_parts.append(
                    f"- {run.get('kind')} run (status: {run.get('status')}) - ID: {run.get('id')}"
                )

            summary = "\n".join(summary_parts)

            logger.info(
                "Run list completed successfully",
                extra={
                    "request_id": request_id,
                    "tool": "run_list",
                    "count": len(runs),
                },
            )

            return CallToolResult(content=[{"type": "text", "text": summary}])

        except Exception as e:
            logger.error(
                "Run list tool failed",
                extra={"request_id": request_id, "tool": "run_list", "error": str(e)},
            )

            return CallToolResult(
                content=[{"type": "text", "text": f"Run listing failed: {str(e)}"}],
                isError=True,
            )

    async def run_get_tool(arguments: Dict[str, Any]):
        """Get a specific run by ID."""
        from mcp.types import CallToolResult

        request_id = _request_id()
        run_id = arguments.get("run_id", "")

        logger.info(
            "Run get tool called",
            extra={"request_id": request_id, "tool": "run_get", "run_id": run_id},
        )

        try:
            # Call crew API
            result = await make_api_request(
                f"/runs/{run_id}", method="GET", request_id=request_id
            )

            logger.info(
                "Run retrieved successfully",
                extra={"request_id": request_id, "tool": "run_get", "run_id": run_id},
            )

            return CallToolResult(
                content=[
                    {
                        "type": "text",
                        "text": f"Run Details:\nID: {result.get('id')}\nKind: {result.get('kind')}\nStatus: {result.get('status')}\nAgent ID: {result.get('agent_id', 'N/A')}\nCrew ID: {result.get('crew_id', 'N/A')}\nStarted: {result.get('started_at', 'N/A')}\nCompleted: {result.get('completed_at', 'N/A')}",
                    }
                ]
            )

        except Exception as e:
            logger.error(
                "Run get tool failed",
                extra={"request_id": request_id, "tool": "run_get", "error": str(e)},
            )

            return CallToolResult(
                content=[{"type": "text", "text": f"Run retrieval failed: {str(e)}"}],
                isError=True,
            )

    async def run_cancel_tool(arguments: Dict[str, Any]):
        """Cancel a running task."""
        from mcp.types import CallToolResult

        request_id = _request_id()
        run_id = arguments.get("run_id", "")

        logger.info(
            "Run cancel tool called",
            extra={"request_id": request_id, "tool": "run_cancel", "run_id": run_id},
        )

        try:
            # Call crew API
            result = await make_api_request(
                f"/runs/{run_id}/cancel", method="POST", request_id=request_id
            )

            logger.info(
                "Run cancelled successfully",
                extra={
                    "request_id": request_id,
                    "tool": "run_cancel",
                    "run_id": run_id,
                },
            )

            return CallToolResult(
                content=[
                    {
                        "type": "text",
                        "text": f"Run cancelled successfully:\nRun ID: {run_id}\nStatus: {result.get('status')}",
                    }
                ]
            )

        except Exception as e:
            logger.error(
                "Run cancel tool failed",
                extra={"request_id": request_id, "tool": "run_cancel", "error": str(e)},
            )

            return CallToolResult(
                content=[
                    {"type": "text", "text": f"Run cancellation failed: {str(e)}"}
                ],
                isError=True,
            )

    # Register the handlers
    from mcp.types import CallToolRequest, ListToolsRequest

    mcp.request_handlers[ListToolsRequest] = handle_list_tools
    mcp.request_handlers[CallToolRequest] = handle_call_tool

    logger.info("MCP tools registered successfully")


def create_asgi_app() -> FastAPI:
    """Create the FastAPI ASGI app with MCP integration."""
    logger = logging.getLogger(__name__)

    # Create FastAPI app
    app = FastAPI(
        title="Cage MCP Server",
        description="Model Context Protocol server for Cage API integration",
        version="1.0.0",
    )

    @app.get("/mcp/health")
    async def health_check(request: Request):
        """Health check endpoint."""
        request_id = extract_request_id(request)

        logger.info(
            "Health check requested",
            extra={"request_id": request_id, "route": "/mcp/health", "status": "ok"},
        )

        return {"status": "ok"}

    @app.get("/mcp/about")
    async def about(request: Request):
        """About endpoint with server information."""
        request_id = extract_request_id(request)

        logger.info(
            "About endpoint requested",
            extra={"request_id": request_id, "route": "/mcp/about"},
        )

        return {"server": "cage-mcp", "version": "1.0.0"}

    @app.post("/mcp/rpc")
    async def mcp_rpc_endpoint(request: Request):
        """MCP JSON-RPC endpoint."""
        global mcp_server

        request_id = extract_request_id(request)

        logger.info(
            "MCP RPC request received",
            extra={"request_id": request_id, "route": "/mcp/rpc"},
        )

        if not mcp_server:
            raise HTTPException(status_code=500, detail="MCP server not initialized")

        try:
            # Get request body
            body = await request.json()

            # Validate JSON-RPC 2.0 structure
            if not isinstance(body, dict):
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32600,
                        "message": "Invalid Request: request must be an object",
                    },
                    "id": None,
                }

            if body.get("jsonrpc") != "2.0":
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32600,
                        "message": "Invalid Request: jsonrpc version must be 2.0",
                    },
                    "id": body.get("id"),
                }

            method = body.get("method")
            params = body.get("params", {})
            rpc_id = body.get("id")

            if not method:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32600,
                        "message": "Invalid Request: method field is required",
                    },
                    "id": rpc_id,
                }

            logger.info(
                "Processing MCP RPC method",
                extra={"request_id": request_id, "method": method, "rpc_id": rpc_id},
            )

            # Dispatch to appropriate handler
            result = await dispatch_mcp_request(mcp_server, method, params, request_id)

            return {"jsonrpc": "2.0", "result": result, "id": rpc_id}

        except Exception as e:
            logger.error(
                "MCP RPC error", extra={"request_id": request_id, "error": str(e)}
            )

            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                "id": body.get("id") if isinstance(body, dict) else None,
            }

    logger.info("ASGI app created with MCP RPC and ops endpoints")
    return app


async def dispatch_mcp_request(
    mcp: Server, method: str, params: Dict[str, Any], request_id: str
) -> Any:
    """
    Dispatch MCP JSON-RPC request to appropriate handler.

    Args:
        mcp: MCP server instance
        method: JSON-RPC method name
        params: Method parameters
        request_id: Request ID for logging

    Returns:
        Method result

    Raises:
        Exception: On method execution errors
    """
    from mcp.types import (
        CallToolRequest,
        InitializeRequest,
        ListToolsRequest,
    )

    logger = logging.getLogger(__name__)

    # Handle initialize method
    if method == "initialize":
        logger.info("Handling initialize request", extra={"request_id": request_id})

        # Create InitializeRequest from params
        init_request = InitializeRequest(
            method="initialize",
            params={
                "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                "capabilities": params.get("capabilities", {}),
                "clientInfo": params.get(
                    "clientInfo", {"name": "cage-mcp-client", "version": "1.0.0"}
                ),
            },
        )

        # Return server capabilities
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
            "serverInfo": {"name": "cage-mcp", "version": "1.0.0"},
        }

    # Handle tools/list method
    elif method == "tools/list":
        logger.info("Handling tools/list request", extra={"request_id": request_id})

        # Create request object
        list_tools_request = ListToolsRequest(method="tools/list", params=params or {})

        # Get handler from MCP server
        handler = mcp.request_handlers.get(ListToolsRequest)
        if not handler:
            raise Exception("tools/list handler not registered")

        # Call handler
        result = await handler(list_tools_request)

        # Convert to dict
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema,
                }
                for tool in result.tools
            ]
        }

    # Handle tools/call method
    elif method == "tools/call":
        logger.info(
            "Handling tools/call request",
            extra={"request_id": request_id, "tool": params.get("name")},
        )

        # Import the proper params class
        from mcp.types import CallToolRequestParams

        # Create request object with proper structure
        call_tool_request = CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(
                name=params.get("name"), arguments=params.get("arguments", {})
            ),
        )

        # Get handler from MCP server
        handler = mcp.request_handlers.get(CallToolRequest)
        if not handler:
            raise Exception("tools/call handler not registered")

        # Call handler
        result = await handler(call_tool_request)

        # Convert to dict
        return {"content": result.content, "isError": getattr(result, "isError", False)}

    # Handle resources/list method
    elif method == "resources/list":
        logger.info("Handling resources/list request", extra={"request_id": request_id})

        # Return empty resources list for now
        return {"resources": []}

    # Handle prompts/list method
    elif method == "prompts/list":
        logger.info("Handling prompts/list request", extra={"request_id": request_id})

        # Return empty prompts list for now
        return {"prompts": []}

    # Unknown method
    else:
        logger.warning(
            "Unknown MCP method", extra={"request_id": request_id, "method": method}
        )
        raise Exception(f"Method not found: {method}")


def _request_id() -> str:
    """Generate a new request ID."""
    return str(uuid.uuid4())


def extract_request_id(request: Request) -> str:
    """Extract request ID from HTTP headers or generate a new one."""
    # Check for X-Request-ID header
    request_id = request.headers.get("X-Request-ID")
    if request_id:
        return request_id

    # Generate new request ID if not present
    return _request_id()


async def make_api_request(
    endpoint: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Make an HTTP request to the Cage API.

    Args:
        endpoint: API endpoint (e.g., "/health")
        method: HTTP method (GET, POST, etc.)
        data: Request body data (for POST/PUT)
        request_id: Request ID for correlation
        base_url: Base URL for the API (defaults to crew-api)

    Returns:
        Response JSON data

    Raises:
        httpx.HTTPStatusError: On HTTP errors with status mapping
        Exception: On other errors
    """
    logger = logging.getLogger(__name__)

    # Use provided request_id or generate one
    if not request_id:
        request_id = _request_id()

    # Use provided base_url or default to crew-api
    if not base_url:
        base_url = settings.api_base_url

    # Build URL
    url = base_url.rstrip("/") + "/" + endpoint.lstrip("/")

    # Prepare headers
    headers = {
        "Authorization": f"Bearer {settings.pod_token}",
        "Content-Type": "application/json",
        "X-Request-ID": request_id,
    }

    logger.info(
        f"Making API request: {method} {url}",
        extra={"request_id": request_id, "method": method, "url": url},
    )

    try:
        # Create HTTP client with timeout
        async with httpx.AsyncClient(timeout=settings.api_timeout_s) as client:
            # Make request
            response = await client.request(
                method=method, url=url, headers=headers, json=data
            )

            # Check for non-2xx status codes and handle Problem Details
            if not (200 <= response.status_code < 300):
                await handle_http_error(response, request_id)

            # Parse JSON response
            result = response.json()

            logger.info(
                f"API request successful: {response.status_code}",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "response_size": len(str(result)),
                },
            )

            return result

    except httpx.HTTPStatusError:
        # This will be raised by handle_http_error
        raise
    except Exception as e:
        logger.error(
            f"Unexpected API request error: {e}",
            extra={"request_id": request_id, "error": str(e)},
        )
        raise


async def handle_http_error(response: httpx.Response, request_id: str):
    """
    Handle HTTP errors and map them to appropriate MCP errors.

    Args:
        response: The HTTP response with error status
        request_id: Request ID for logging

    Raises:
        httpx.HTTPStatusError: With mapped error details
    """
    logger = logging.getLogger(__name__)

    # Try to parse Problem Details response
    problem_detail = None
    try:
        if response.headers.get("content-type", "").startswith(
            "application/problem+json"
        ):
            problem_detail = response.json()
    except Exception:
        # If parsing fails, continue with status code mapping
        pass

    # Map status codes to MCP error types
    status_code = response.status_code

    if status_code in [401, 403]:
        error_type = "forbidden"
    elif status_code == 404:
        error_type = "not_found"
    elif status_code == 409:
        error_type = "conflict"
    elif status_code == 412:
        error_type = "precondition_failed"
    elif status_code == 422:
        error_type = "invalid_params"
    else:
        error_type = "internal_error"

    # Create error message
    if problem_detail:
        error_message = f"{error_type}: {problem_detail.get('title', 'Unknown error')}"
        if problem_detail.get("detail"):
            error_message += f" - {problem_detail['detail']}"
    else:
        error_message = (
            f"{error_type}: HTTP {status_code} - {response.text or 'Unknown error'}"
        )

    logger.error(
        f"API request failed: {error_message}",
        extra={
            "request_id": request_id,
            "status_code": status_code,
            "error_type": error_type,
            "problem_detail": problem_detail,
        },
    )

    # Create HTTPStatusError with enhanced details
    error = httpx.HTTPStatusError(
        message=error_message, request=response.request, response=response
    )

    # Add custom attributes for MCP error handling
    error.error_type = error_type
    error.problem_detail = problem_detail

    raise error


def create_mcp_error_response(
    error: Exception, tool_name: str, request_id: str
) -> Dict[str, Any]:
    """
    Create an MCP error response from an exception.

    Args:
        error: The exception that occurred
        tool_name: Name of the tool that failed
        request_id: Request ID for correlation

    Returns:
        CallToolResult with error information
    """
    from mcp.types import CallToolResult

    # Check if it's an HTTP error with our enhanced attributes
    if isinstance(error, httpx.HTTPStatusError) and hasattr(error, "error_type"):
        error_type = error.error_type
        problem_detail = getattr(error, "problem_detail", None)

        if problem_detail:
            error_message = (
                f"{error_type}: {problem_detail.get('title', 'Unknown error')}"
            )
            if problem_detail.get("detail"):
                error_message += f" - {problem_detail['detail']}"
        else:
            error_message = str(error)
    else:
        # Generic error handling
        error_type = "internal_error"
        error_message = str(error)
        problem_detail = None

    # Create error text with context
    error_text = f"{tool_name} failed: {error_message}"

    # Include original problem detail for transparency if available
    if problem_detail:
        error_text += f"\n\nOriginal error details: {problem_detail}"

    return CallToolResult(content=[{"type": "text", "text": error_text}], isError=True)


def health_ping():
    """Send a health ping log entry."""
    logger = logging.getLogger(__name__)
    request_id = _request_id()

    # Log health ping with structured fields
    logger.info(
        "Health ping",
        extra={"request_id": request_id, "route": "/health", "status": "ok"},
    )


def main():
    """Main entry point for the MCP server."""
    parser = create_cli_parser()
    args = parser.parse_args()

    # Update settings with CLI arguments
    settings.host = args.host
    settings.port = args.port
    settings.log_level = args.log_level

    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info(f"Starting Cage MCP Server on {settings.host}:{settings.port}")
    logger.info(f"API Base URL: {settings.api_base_url}")
    logger.info(f"Log Level: {settings.log_level}")

    # Send a health ping to test JSONL logging
    health_ping()

    # Create MCP server instance
    try:
        global mcp_server
        mcp_server = create_mcp_server()
        logger.info("MCP server created and ready for configuration")
    except Exception as e:
        logger.error(f"Failed to initialize MCP server: {e}")
        sys.exit(1)

    # Create ASGI app
    try:
        global app
        app = create_asgi_app()
        logger.info("ASGI app created successfully")

        # Start the server with uvicorn
        logger.info(f"Starting uvicorn server on {settings.host}:{settings.port}")
        uvicorn.run(
            app,
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level.lower(),
            access_log=False,  # We handle logging ourselves
        )

    except Exception as e:
        logger.error(f"Failed to start ASGI app: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
