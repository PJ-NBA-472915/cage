"""Cage tools for MCP Streamable HTTP server."""

import argparse
import logging
import os
from typing import Any, Optional

import httpx
import uvicorn
from mcp.server.fastmcp import Context, FastMCP

# Configure logging
logger = logging.getLogger(__name__)

mcp = FastMCP(name="cage", json_response=False, stateless_http=False)

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")
POD_TOKEN = os.getenv("POD_TOKEN", "test-mcp-token")


async def make_api_request(
    endpoint: str, method: str = "GET", data: Optional[dict] = None
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
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(
            f"API request failed with status {e.response.status_code}: {e.response.text}"
        )
        raise Exception(
            f"API request failed: {e.response.status_code} - {e.response.text}"
        )
    except httpx.RequestError as e:
        logger.error(f"API request error: {e}")
        raise Exception(f"API request error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in API request: {e}")
        raise


@mcp.tool()
async def rag_query(
    query: str,
    top_k: int = 8,
    filters: Optional[dict[str, Any]] = None,
    ctx: Context = None,
) -> str:
    """Query the RAG (Retrieval-Augmented Generation) system for relevant code and documentation.

    Args:
        query: The search query to find relevant content
        top_k: Maximum number of results to return (default: 8)
        filters: Optional filters to apply (e.g., {"language": "python", "path": "src/"})
    """
    ctx.info(f"RAG query: {query}, top_k: {top_k}, filters: {filters}")
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
                return f"No results found for query: '{query}'"

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

            return f"""Found {total} results for query: '{query}'

{chr(10).join(formatted_results)}"""

        else:
            return f"RAG query failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"Error in rag_query: {e}")
        return f"Error querying RAG system: {str(e)}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run MCP Streamable HTTP based server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to listen on")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on")
    args = parser.parse_args()

    # Start the server with Streamable HTTP transport
    uvicorn.run(mcp.streamable_http_app, host=args.host, port=args.port)
