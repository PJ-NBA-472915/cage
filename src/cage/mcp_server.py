"""Cage tools for MCP Streamable HTTP server."""

import argparse
import logging
import os
from typing import Any

import httpx
from mcp.server import Server
from mcp.types import CallToolResult, ListToolsResult, Tool

# Configure logging
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")
POD_TOKEN = os.getenv("POD_TOKEN", "test-mcp-token")

# Create MCP server instance
mcp = Server("cage")


async def make_api_request(
    endpoint: str, method: str = "GET", data: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Make authenticated API request to Cage API service."""
    url = f"{API_BASE_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {POD_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method.upper() == "POST":
                response = await client.post(url, headers=headers, json=data)
            else:
                response = await client.get(url, headers=headers)

            response.raise_for_status()
            result = response.json()
            return result if isinstance(result, dict) else {}

    except httpx.HTTPStatusError as e:
        logger.error(
            f"API request failed with status {e.response.status_code}: {e.response.text}"
        )
        raise Exception(
            f"API request failed: {e.response.status_code} - {e.response.text}"
        ) from e
    except httpx.RequestError as e:
        logger.error(f"API request error: {e}")
        raise Exception(f"API request error: {str(e)}") from e
    except Exception as e:
        logger.error(f"Unexpected error in API request: {e}")
        raise


@mcp.list_tools()  # type: ignore[misc]
async def list_tools() -> ListToolsResult:
    """List available MCP tools."""
    tools = [
        Tool(
            name="rag_query",
            description="Query the RAG (Retrieval-Augmented Generation) system for relevant code and documentation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant content",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 8,
                    },
                    "filters": {
                        "type": "object",
                        "description": 'Optional filters to apply (e.g., {"language": "python", "path": "src/"})',
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="rag_reindex",
            description="Reindex the RAG (Retrieval-Augmented Generation) system with specified paths.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": 'List of paths to reindex (e.g., ["src/", "docs/"]). If None, reindexes all content.',
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Whether to force reindexing even if content is already indexed",
                        "default": False,
                    },
                },
                "required": [],
            },
        ),
    ]
    return ListToolsResult(tools=tools)


@mcp.call_tool()  # type: ignore[misc]
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Handle tool calls."""
    if name == "rag_query":
        return await rag_query_tool(arguments)
    elif name == "rag_reindex":
        return await rag_reindex_tool(arguments)
    else:
        return CallToolResult(
            content=[{"type": "text", "text": f"Unknown tool: {name}"}],
            isError=True,
        )


async def rag_query_tool(arguments: dict[str, Any]) -> CallToolResult:
    """Query the RAG system for relevant information."""
    query = arguments.get("query", "")
    top_k = arguments.get("top_k", 8)
    filters = arguments.get("filters")

    logger.info(f"RAG query: {query}, top_k: {top_k}, filters: {filters}")
    try:
        # Prepare request data
        request_data = {"query": query, "top_k": top_k, "filters": filters}

        # Make API request
        result = await make_api_request("/query", "POST", request_data)

        # Format results for user-friendly display
        if result.get("status") == "success":
            hits = result.get("hits", [])
            total = result.get("total", 0)

            if total == 0:
                return CallToolResult(
                    content=[
                        {
                            "type": "text",
                            "text": f"No results found for query: '{query}'",
                        }
                    ]
                )

            # Format each result
            formatted_results = []
            for i, hit in enumerate(hits, 1):
                content = hit.get("content", "")
                metadata = hit.get("metadata", {})
                score = hit.get("score", 0.0)
                path = metadata.get("path", "unknown")
                language = metadata.get("language", "unknown")
                chunk_id = metadata.get("chunk_id", 0)

                # Truncate content if too long
                if len(content) > 200:
                    content = content[:200] + "..."

                formatted_result = f"""
Result {i} (Score: {score:.3f}):
File: {path} (chunk {chunk_id})
Language: {language}
Content: {content}
"""
                formatted_results.append(formatted_result.strip())

            summary = f"""Found {total} results for query: '{query}'

{chr(10).join(formatted_results)}"""
            return CallToolResult(content=[{"type": "text", "text": summary}])

        else:
            return CallToolResult(
                content=[
                    {
                        "type": "text",
                        "text": f"RAG query failed: {result.get('error', 'Unknown error')}",
                    }
                ],
                isError=True,
            )

    except Exception as e:
        logger.error(f"Error in rag_query: {e}")
        return CallToolResult(
            content=[{"type": "text", "text": f"Error querying RAG system: {str(e)}"}],
            isError=True,
        )


async def rag_reindex_tool(arguments: dict[str, Any]) -> CallToolResult:
    """Reindex the RAG system with specified paths."""
    paths = arguments.get("paths")
    force = arguments.get("force", False)

    logger.info(f"RAG reindex requested for paths: {paths}, force: {force}")
    try:
        # Prepare request data
        request_data = {"paths": paths, "force": force}

        # Make API request to reindex endpoint
        result = await make_api_request("/reindex", "POST", request_data)

        # Format response for user-friendly display
        if result.get("status") == "success":
            documents_indexed = result.get("documents_indexed", 0)
            total_chunks = result.get("total_chunks", 0)
            paths_processed = result.get("paths_processed", ["all"])
            force_flag = result.get("force", False)

            summary = f"""RAG reindexing completed successfully!

Paths processed: {', '.join(paths_processed)}
Documents indexed: {documents_indexed}
Total chunks created: {total_chunks}
Force reindex: {force_flag}

The RAG system is now updated with the latest content."""
            return CallToolResult(content=[{"type": "text", "text": summary}])

        else:
            return CallToolResult(
                content=[
                    {
                        "type": "text",
                        "text": f"RAG reindexing failed: {result.get('error', 'Unknown error')}",
                    }
                ],
                isError=True,
            )

    except Exception as e:
        logger.error(f"Error in rag_reindex: {e}")
        return CallToolResult(
            content=[
                {"type": "text", "text": f"Error reindexing RAG system: {str(e)}"}
            ],
            isError=True,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run MCP Streamable HTTP based server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to listen on")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on")
    args = parser.parse_args()

    # Start the server with stdio transport
    import asyncio

    from mcp.server.stdio import stdio_server

    async def main() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await mcp.run(
                read_stream, write_stream, mcp.create_initialization_options()
            )

    asyncio.run(main())
