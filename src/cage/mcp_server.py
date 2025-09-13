"""
MCP (Model Context Protocol) Server for RAG tools

This service implements the official MCP protocol using streamable HTTP transport
to expose RAG tools for use with Claude and other MCP-compatible clients.

Based on: https://github.com/modelcontextprotocol/python-sdk/blob/main/examples/servers/simple-streamablehttp/mcp_simple_streamablehttp/server.py
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

# Debugpy integration for container debugging
if os.getenv("DEBUGPY_ENABLED", "0") == "1":
    import debugpy
    try:
        debugpy.listen(("0.0.0.0", 5679))
        if os.getenv("DEBUGPY_WAIT_FOR_CLIENT", "0") == "1":
            debugpy.wait_for_client()
        print("Debugpy enabled - waiting for debugger to attach on port 5679")
    except RuntimeError as e:
        if "Address already in use" in str(e):
            print("Debugpy port 5679 already in use, skipping debugpy setup")
        else:
            raise

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
import json
import redis.asyncio as redis

from .rag_service import RAGService

# Configure logging
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "mcp.log")
os.makedirs(LOG_DIR, exist_ok=True)

class JsonFormatter(logging.Formatter):
    """JSON formatter for structured MCP server logging"""
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "file": record.filename,
            "line": record.lineno,
            "service": "mcp_server"
        }
        if hasattr(record, 'json_data'):
            log_record.update(record.json_data)
        return json.dumps(log_record)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(JsonFormatter())
logger.addHandler(file_handler)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = datetime.utcnow()
        
        # Skip logging for health endpoint
        if request.url.path == "/health":
            return await call_next(request)
        
        # Log the incoming request
        logger.info("HTTP request received", 
                    extra={"json_data": {
                        "event": "http_request",
                        "method": request.method,
                        "url": str(request.url),
                        "path": request.url.path,
                        "query_params": dict(request.query_params),
                        "client_ip": request.client.host if request.client else "unknown"
                    }})
        
        try:
            response = await call_next(request)
            
            # Log the response
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.info("HTTP response sent", 
                        extra={"json_data": {
                            "event": "http_response",
                            "method": request.method,
                            "url": str(request.url),
                            "status_code": response.status_code,
                            "duration_ms": round(duration_ms, 2)
                        }})
            
            return response
            
        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error("HTTP request failed", 
                        extra={"json_data": {
                            "event": "http_error",
                            "method": request.method,
                            "url": str(request.url),
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "duration_ms": round(duration_ms, 2)
                        }})
            raise

app = FastAPI(title="Cage MCP Server", version="0.1.0")

# Disable uvicorn access logging to avoid duplicate logs
uvicorn_logger = logging.getLogger("uvicorn.access")
uvicorn_logger.disabled = True

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging middleware (excludes health requests)
app.add_middleware(LoggingMiddleware)

# Globals
rag_service: Optional[RAGService] = None
redis_client: Optional[redis.Redis] = None

SESSION_TTL_SECONDS = int(os.getenv("MCP_SESSION_TTL", "3600"))
RATE_LIMIT_MAX_CALLS = int(os.getenv("MCP_RATE_MAX_CALLS", "120"))

# MCP Protocol Models
class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: str
    params: Optional[Dict[str, Any]] = None

class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    
    def dict(self, **kwargs):
        """Override dict to exclude None values for MCP compliance"""
        data = super().dict(**kwargs)
        # Remove None values to comply with MCP spec
        return {k: v for k, v in data.items() if v is not None}
    
    def success_dict(self, **kwargs):
        """Return dict for successful responses (no error field)"""
        data = super().dict(**kwargs)
        # For success responses, only include result, not error
        return {k: v for k, v in data.items() if k != "error" and v is not None}
    
    def error_dict(self, **kwargs):
        """Return dict for error responses (no result field)"""
        data = super().dict(**kwargs)
        # For error responses, only include error, not result
        return {k: v for k, v in data.items() if k != "result" and v is not None}

class MCPError(BaseModel):
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None
    
    def dict(self, **kwargs):
        """Override dict to exclude None values for JSON-RPC compliance"""
        data = super().dict(**kwargs)
        # Remove None values to comply with JSON-RPC 2.0 spec
        return {k: v for k, v in data.items() if v is not None}

def _as_mcp_content(result: Any) -> Dict[str, Any]:
    """Wrap any Python value as MCP ToolResponse content."""
    return {
        "content": [
            {
                "type": "json",
                "json": result,
            }
        ]
    }

def _allowed_tokens() -> List[str]:
    """Get list of allowed authentication tokens."""
    tokens = []
    csv = os.getenv("MCP_TOKENS", "").strip()
    if csv:
        tokens.extend([t.strip() for t in csv.split(",") if t.strip()])
    pod = os.getenv("POD_TOKEN", "").strip()
    if pod:
        tokens.append(pod)
    return list({t for t in tokens if t})

async def _get_auth_token(authorization: str = Header(None)) -> str:
    """Extract and validate Bearer token from Authorization header"""
    if not authorization or not authorization.startswith("Bearer "):
        logger.warning("Authentication failed: Missing or invalid Authorization header")
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.split(" ", 1)[1].strip()
    allowed = _allowed_tokens()

    if not token or (allowed and token not in allowed):
        logger.warning("Authentication failed: Invalid token")
        raise HTTPException(status_code=401, detail="Invalid token")

    logger.info("Authentication successful")
    return token

async def _create_session(token: str, client_info: Optional[Dict[str, Any]] = None) -> str:
    """Create a new MCP session"""
    session_id = str(uuid.uuid4())
    meta = {
        "session_id": session_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "last_seen": datetime.utcnow().isoformat() + "Z",
        "client_info": client_info or {},
        "calls": 0,
        "token_hash": str(hash(token)),
    }
    
    if redis_client:
        await redis_client.setex(f"mcp:sessions:{session_id}", SESSION_TTL_SECONDS, json.dumps(meta))
        await redis_client.setex(f"mcp:token:{hash(token)}", SESSION_TTL_SECONDS, session_id)
    
    return session_id

async def _bump_session(session_id: str):
    """Update session activity"""
    if not redis_client:
        return
    key = f"mcp:sessions:{session_id}"
    data = await redis_client.get(key)
    if not data:
        return
    try:
        meta = json.loads(data)
    except Exception:
        meta = {"session_id": session_id, "calls": 0}
    meta["last_seen"] = datetime.utcnow().isoformat() + "Z"
    meta["calls"] = int(meta.get("calls", 0)) + 1
    await redis_client.setex(key, SESSION_TTL_SECONDS, json.dumps(meta))

async def _check_rate_limit(session_id: str) -> bool:
    """Check if session is within rate limits"""
    if not redis_client or not RATE_LIMIT_MAX_CALLS:
        return True
    key = f"mcp:ratelimit:{session_id}"
    cur = await redis_client.incr(key)
    if cur == 1:
        await redis_client.expire(key, SESSION_TTL_SECONDS)
    return cur <= RATE_LIMIT_MAX_CALLS

def _get_tools() -> List[Dict[str, Any]]:
    """Get available MCP tools."""
    return [
        {
            "name": "rag_query",
            "description": "Query the RAG system for relevant code and documentation",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query string"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 8,
                        "minimum": 1,
                        "maximum": 50
                    },
                    "filters": {
                        "type": "object",
                        "description": "Optional filters for the search",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Filter by file path pattern"
                            },
                            "language": {
                                "type": "string",
                                "description": "Filter by programming language"
                            },
                            "branch": {
                                "type": "string",
                                "description": "Filter by git branch"
                            }
                        }
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "rag_reindex",
            "description": "Reindex repository content for RAG search",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "description": "What to reindex",
                        "enum": ["repo", "tasks", "chat", "all"],
                        "default": "all"
                    }
                }
            }
        },
        {
            "name": "rag_check_blob",
            "description": "Check if blob metadata is present in the RAG system",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "blob_sha": {
                        "type": "string",
                        "description": "The SHA hash of the blob to check"
                    }
                },
                "required": ["blob_sha"]
            }
        },
        {
            "name": "rag_get_status",
            "description": "Get RAG system status and statistics",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        }
    ]

def _get_resources() -> List[Dict[str, Any]]:
    """Get available MCP resources."""
    return [
        {
            "uri": "rag://status",
            "name": "RAG Status",
            "description": "Current status and statistics of the RAG system",
            "mimeType": "application/json"
        }
    ]

async def _handle_rag_query(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle RAG query tool call"""
    query = arguments.get("query", "")
    top_k = int(arguments.get("top_k", 8))
    filters = arguments.get("filters") or {}
    if not query:
        raise ValueError("query is required")
    results = await rag_service.query(query, top_k=top_k, filters=filters)
    hits = []
    for r in results:
        hits.append({
            "content": r.content,
            "metadata": {
                "path": r.metadata.path,
                "language": r.metadata.language,
                "commit_sha": r.metadata.commit_sha,
                "branch": r.metadata.branch,
                "chunk_id": r.metadata.chunk_id,
            },
            "score": r.score,
            "blob_sha": r.blob_sha,
        })
    return {"hits": hits, "total": len(hits)}

async def _handle_rag_reindex(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle RAG reindex tool call"""
    scope = arguments.get("scope", "all")
    repo_path_env = os.getenv("REPO_PATH", "/work/repo")
    from pathlib import Path
    result = await rag_service.reindex_repository(Path(repo_path_env), scope)
    return result

async def _handle_rag_check_blob(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle RAG check blob tool call"""
    blob_sha = arguments.get("blob_sha")
    if not blob_sha:
        raise ValueError("blob_sha is required")
    return await rag_service.check_blob_metadata(blob_sha)

async def _handle_rag_get_status(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle RAG get status tool call"""
    async with rag_service.db_pool.acquire() as conn:
        blob_count = await conn.fetchval("SELECT COUNT(*) FROM git_blobs")
        embedding_count = await conn.fetchval("SELECT COUNT(*) FROM embeddings")
        recent_events = await conn.fetch(
            "SELECT type, created_at FROM events ORDER BY created_at DESC LIMIT 5"
        )
    return {
        "blobs": int(blob_count or 0),
        "embeddings": int(embedding_count or 0),
        "recent_events": [
            {"type": e["type"], "created_at": e["created_at"].isoformat()} for e in recent_events
        ],
    }

TOOL_DISPATCH = {
    "rag_query": _handle_rag_query,
    "rag_reindex": _handle_rag_reindex,
    "rag_check_blob": _handle_rag_check_blob,
    "rag_get_status": _handle_rag_get_status,
}

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global rag_service, redis_client
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/cage")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not openai_key:
        logger.warning("OPENAI_API_KEY not set; RAG disabled. MCP server will start without RAG functionality.")
        rag_service = None
    else:
        try:
            rag_service = RAGService(db_url=db_url, redis_url=redis_url, openai_api_key=openai_key)
            await rag_service.initialize()
        except Exception as e:
            logger.warning(f"Failed to initialize RAG service: {e}. MCP server will start without RAG functionality.")
            rag_service = None

    try:
        redis_client = redis.from_url(redis_url, decode_responses=True)
        await redis_client.ping()
    except Exception as e:
        logger.warning(f"Redis not reachable, continuing without rate limiting/session persistence: {e}")
        redis_client = None

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global rag_service, redis_client
    if rag_service:
        await rag_service.close()
    if redis_client:
        await redis_client.close()

@app.get("/health")
async def health():
    """Health check endpoint"""
    info = {
        "status": "ok",
        "rag": bool(rag_service is not None),
        "redis": bool(redis_client is not None),
        "time": datetime.utcnow().isoformat() + "Z",
    }
    if rag_service is not None:
        info["tools_count"] = len(_get_tools())
        info["resources_count"] = len(_get_resources())
    return info

@app.get("/mcp")
async def mcp_get_endpoint(token: str = Depends(_get_auth_token)):
    """Handle GET requests to MCP endpoint - return server info."""
    logger.info("MCP GET request received")
    
    if rag_service is None:
        logger.warning("MCP GET request rejected: RAG service not available")
        raise HTTPException(status_code=503, detail="RAG service not available")
    
    return {
        "name": "Cage RAG MCP Server",
        "version": "0.1.0",
        "protocol": "mcp",
        "capabilities": {
            "tools": len(_get_tools()),
            "resources": len(_get_resources())
        }
    }

@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest, token: str = Depends(_get_auth_token)):
    """Main MCP endpoint handling all MCP protocol requests."""
    logger.info(f"MCP request received: {request.method}")
    
    if rag_service is None:
        response = MCPResponse(
            id=request.id,
            error=MCPError(code=-32603, message="RAG service not available").dict()
        )
        return JSONResponse(content=response.error_dict())
    
    # Rate limiting
    session_id = f"session_{hash(token)}"
    if not await _check_rate_limit(session_id):
        logger.warning("Rate limit exceeded")
        response = MCPResponse(
            id=request.id,
            error=MCPError(code=-32600, message="Rate limit exceeded").dict()
        )
        return JSONResponse(content=response.error_dict())
    
    await _bump_session(session_id)
    
    try:
        if request.method == "initialize":
            logger.info("MCP initialize request processed")
            client_capabilities = request.params.get("capabilities", {}) if request.params else {}
            
            response = MCPResponse(
                id=request.id,
                result={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {
                            "listChanged": True
                        },
                        "resources": {
                            "listChanged": True
                        },
                        "prompts": {} if client_capabilities.get("prompts") else None,
                        "logging": {} if client_capabilities.get("logging") else None
                    },
                    "serverInfo": {
                        "name": "Cage RAG MCP Server",
                        "version": "0.1.0"
                    }
                }
            )
            response_dict = response.success_dict()
            logger.info(f"Response dict: {response_dict}")
            return JSONResponse(content=response_dict)

        elif request.method == "tools/list":
            tools = _get_tools()
            logger.info(f"MCP tools/list request processed: {len(tools)} tools")
            response = MCPResponse(
                id=request.id,
                result={"tools": tools}
            )
            return JSONResponse(content=response.success_dict())
        
        elif request.method == "tools/call":
            params = request.params or {}
            name = params.get("name", "").strip()
            arguments = params.get("arguments") or {}

            logger.info(f"MCP tool call request: {name}")

            handler = TOOL_DISPATCH.get(name)
            if not handler:
                logger.warning(f"MCP tool call failed: Unknown tool {name}")
                response = MCPResponse(
                    id=request.id,
                    error=MCPError(code=-32601, message=f"Unknown tool: {name}").dict()
                )
                return JSONResponse(content=response.error_dict())

            result = await handler(arguments)
            logger.info(f"MCP tool call completed successfully: {name}")
            response = MCPResponse(id=request.id, result=_as_mcp_content(result))
            return JSONResponse(content=response.success_dict())
        
        elif request.method == "resources/list":
            resources = _get_resources()
            logger.info(f"MCP resources/list request processed: {len(resources)} resources")
            response = MCPResponse(
                id=request.id,
                result={"resources": resources}
            )
            return JSONResponse(content=response.success_dict())
        
        elif request.method == "resources/read":
            params = request.params or {}
            uri = params.get("uri", "")

            logger.info(f"MCP resource read request: {uri}")

            if uri == "rag://status":
                status = await _handle_rag_get_status({})
                logger.info(f"MCP resource read completed successfully: {uri}")
                response = MCPResponse(
                    id=request.id,
                    result={
                        "contents": [
                            {
                                "uri": uri,
                                "mimeType": "application/json",
                                "text": json.dumps(status, separators=(",", ":"))
                            }
                        ]
                    }
                )
                return JSONResponse(content=response.success_dict())
            else:
                logger.warning(f"MCP resource read failed: Unknown resource {uri}")
                response = MCPResponse(
                    id=request.id,
                    error=MCPError(code=-32602, message=f"Unknown resource: {uri}").dict()
                )
                return JSONResponse(content=response.error_dict())

        elif request.method in {"ping", "notifications/initialized"}:
            logger.info(f"MCP no-op request processed: {request.method}")
            response = MCPResponse(id=request.id, result={})
            return JSONResponse(content=response.success_dict())
        
        else:
            logger.warning(f"MCP request failed: Unknown method {request.method}")
            response = MCPResponse(
                id=request.id,
                error=MCPError(code=-32601, message=f"Unknown method: {request.method}").dict()
            )
            return JSONResponse(content=response.error_dict())
    
    except Exception as e:
        logger.error(f"MCP request failed with exception: {str(e)}")
        response = MCPResponse(
            id=request.id,
            error=MCPError(code=-32603, message=str(e)).dict()
        )
        return JSONResponse(content=response.error_dict())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
