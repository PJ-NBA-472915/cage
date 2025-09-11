"""
MCP (Model Context Protocol) Server for RAG functionality

This module exposes the RAG system as an MCP server for external AI tool integration.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource
)

from .rag_service import RAGService

logger = logging.getLogger(__name__)

class RAGMCPServer:
    """MCP Server that exposes RAG functionality to external AI tools."""
    
    def __init__(self, rag_service: RAGService):
        """Initialize MCP server with RAG service."""
        self.rag_service = rag_service
        self.server = Server("cage-rag-server")
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up MCP server handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """List available RAG tools."""
            tools = [
                Tool(
                    name="rag_query",
                    description="Query the RAG system for relevant code and documentation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of results to return (default: 8)",
                                "default": 8
                            },
                            "filters": {
                                "type": "object",
                                "description": "Optional filters for the search",
                                "properties": {
                                    "path": {"type": "string", "description": "Filter by file path pattern"},
                                    "language": {"type": "string", "description": "Filter by programming language"},
                                    "branch": {"type": "string", "description": "Filter by git branch"}
                                }
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="rag_reindex",
                    description="Reindex repository content for RAG search",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "scope": {
                                "type": "string",
                                "description": "Scope of reindexing: 'repo', 'tasks', 'chat', or 'all'",
                                "enum": ["repo", "tasks", "chat", "all"],
                                "default": "all"
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="rag_check_blob",
                    description="Check if blob metadata is present in the RAG system",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "blob_sha": {
                                "type": "string",
                                "description": "The blob SHA to check"
                            }
                        },
                        "required": ["blob_sha"]
                    }
                ),
                Tool(
                    name="rag_get_status",
                    description="Get RAG system status and statistics",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]
            return ListToolsResult(tools=tools)
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls."""
            try:
                if name == "rag_query":
                    return await self._handle_rag_query(arguments)
                elif name == "rag_reindex":
                    return await self._handle_rag_reindex(arguments)
                elif name == "rag_check_blob":
                    return await self._handle_rag_check_blob(arguments)
                elif name == "rag_get_status":
                    return await self._handle_rag_get_status(arguments)
                else:
                    return CallToolResult(
                        content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                        isError=True
                    )
            except Exception as e:
                logger.error(f"Error in tool call {name}: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True
                )
    
    async def _handle_rag_query(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle RAG query tool call."""
        query = arguments.get("query", "")
        top_k = arguments.get("top_k", 8)
        filters = arguments.get("filters", {})
        
        if not query:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: Query is required")],
                isError=True
            )
        
        try:
            results = await self.rag_service.query(query, top_k=top_k, filters=filters)
            
            if not results:
                return CallToolResult(
                    content=[TextContent(type="text", text="No results found for the query.")]
                )
            
            # Format results
            formatted_results = []
            for i, result in enumerate(results, 1):
                formatted_result = f"""
Result {i} (Score: {result.score:.3f}):
File: {result.metadata.path}
Language: {result.metadata.language or 'Unknown'}
Branch: {result.metadata.branch or 'Unknown'}
Commit: {result.metadata.commit_sha or 'Unknown'}

Content:
{result.content}

---
"""
                formatted_results.append(formatted_result)
            
            response_text = f"Found {len(results)} results for query: '{query}'\n\n" + "".join(formatted_results)
            
            return CallToolResult(
                content=[TextContent(type="text", text=response_text)]
            )
            
        except Exception as e:
            logger.error(f"Error in RAG query: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error querying RAG system: {str(e)}")],
                isError=True
            )
    
    async def _handle_rag_reindex(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle RAG reindex tool call."""
        scope = arguments.get("scope", "all")
        
        try:
            # Get repository path (simplified - in real implementation, this would be configurable)
            repo_path = Path(".")
            result = await self.rag_service.reindex_repository(repo_path, scope)
            
            response_text = f"""
Reindexing completed successfully!

Scope: {scope}
Indexed files: {result['indexed_files']}
Total chunks: {result['total_chunks']}
Blob SHAs: {len(result['blob_shas'])} processed
"""
            
            return CallToolResult(
                content=[TextContent(type="text", text=response_text)]
            )
            
        except Exception as e:
            logger.error(f"Error in RAG reindex: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error reindexing: {str(e)}")],
                isError=True
            )
    
    async def _handle_rag_check_blob(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle RAG check blob tool call."""
        blob_sha = arguments.get("blob_sha", "")
        
        if not blob_sha:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: Blob SHA is required")],
                isError=True
            )
        
        try:
            result = await self.rag_service.check_blob_metadata(blob_sha)
            
            if result["present"]:
                response_text = f"""
Blob metadata found:

SHA: {result['blob_sha']}
Size: {result['size']} bytes
MIME Type: {result['mime']}
First Seen: {result['first_seen_at']}
"""
            else:
                response_text = f"Blob {blob_sha} not found in the RAG system."
            
            return CallToolResult(
                content=[TextContent(type="text", text=response_text)]
            )
            
        except Exception as e:
            logger.error(f"Error checking blob metadata: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error checking blob: {str(e)}")],
                isError=True
            )
    
    async def _handle_rag_get_status(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle RAG get status tool call."""
        try:
            # Get basic statistics from the database
            async with self.rag_service.db_pool.acquire() as conn:
                # Count total blobs
                blob_count = await conn.fetchval("SELECT COUNT(*) FROM git_blobs")
                
                # Count total embeddings
                embedding_count = await conn.fetchval("SELECT COUNT(*) FROM embeddings")
                
                # Get recent activity
                recent_events = await conn.fetch("""
                    SELECT type, created_at 
                    FROM events 
                    ORDER BY created_at DESC 
                    LIMIT 5
                """)
            
            response_text = f"""
RAG System Status:

Total Blobs: {blob_count}
Total Embeddings: {embedding_count}

Recent Events:
"""
            
            for event in recent_events:
                response_text += f"- {event['type']} at {event['created_at']}\n"
            
            if not recent_events:
                response_text += "- No recent events\n"
            
            return CallToolResult(
                content=[TextContent(type="text", text=response_text)]
            )
            
        except Exception as e:
            logger.error(f"Error getting RAG status: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error getting status: {str(e)}")],
                isError=True
            )
    
    async def run(self):
        """Run the MCP server."""
        try:
            # Initialize RAG service
            await self.rag_service.initialize()
            
            # Run MCP server
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="cage-rag-server",
                        server_version="1.0.0",
                        capabilities=self.server.get_capabilities(
                            notification_options=None,
                            experimental_capabilities={}
                        )
                    )
                )
        except Exception as e:
            logger.error(f"Error running MCP server: {e}")
            raise
        finally:
            await self.rag_service.close()

async def main():
    """Main entry point for MCP server."""
    import os
    
    # Get configuration from environment
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/cage")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    # Create RAG service
    rag_service = RAGService(
        db_url=db_url,
        redis_url=redis_url,
        openai_api_key=openai_api_key
    )
    
    # Create and run MCP server
    mcp_server = RAGMCPServer(rag_service)
    await mcp_server.run()

if __name__ == "__main__":
    asyncio.run(main())
