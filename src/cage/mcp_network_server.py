"""
Network-based MCP-like server over WebSocket for RAG tools

This service exposes the same RAG tools as the stdio MCP server, but over
WebSocket with Bearer-token authentication and Redis-backed session tracking.

Protocol (simple JSON-RPC style):
  Client sends JSON text frames:
    {"id": "1", "method": "list_tools"}
    {"id": "2", "method": "call_tool", "params": {"name": "rag_query", "arguments": {...}}}

  Server replies:
    {"id": "1", "result": {...}}
    {"id": "2", "result": {...}} or {"id": "2", "error": {"message": "..."}}

Auth:
  - Provide Bearer token via `Authorization` header or `?token=...` query.
  - Valid tokens come from env: `MCP_TOKENS` (CSV), or fallback to `POD_TOKEN`.

Sessions:
  - On connect, server creates a session_id and stores metadata in Redis with TTL.
  - Per-call, server bumps last_seen and increments call counters.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis

from .rag_service import RAGService

logger = logging.getLogger(__name__)

app = FastAPI(title="Cage MCP Network Server", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Globals
rag_service: Optional[RAGService] = None
redis_client: Optional[redis.Redis] = None

SESSION_TTL_SECONDS = int(os.getenv("MCP_SESSION_TTL", "3600"))
RATE_LIMIT_MAX_CALLS = int(os.getenv("MCP_RATE_MAX_CALLS", "120"))  # per session per TTL


def _allowed_tokens() -> List[str]:
    tokens = []
    csv = os.getenv("MCP_TOKENS", "").strip()
    if csv:
        tokens.extend([t.strip() for t in csv.split(",") if t.strip()])
    pod = os.getenv("POD_TOKEN", "").strip()
    if pod:
        tokens.append(pod)
    return list({t for t in tokens if t})


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


async def _auth_and_create_session(websocket: WebSocket) -> str:
    # Extract token from Authorization header or query param
    token = None
    auth_header = websocket.headers.get("authorization") or websocket.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    if not token:
        token = websocket.query_params.get("token")

    allowed = _allowed_tokens()
    if not token or (allowed and token not in allowed):
        # If allowed list is empty, treat as open? No—require token.
        raise PermissionError("Unauthorized: missing or invalid token")

    # Create session
    session_id = str(uuid.uuid4())
    meta = {
        "session_id": session_id,
        "created_at": _now_iso(),
        "last_seen": _now_iso(),
        "client": websocket.client.host if websocket.client else None,
        "calls": 0,
        "token_hash": str(hash(token)),
    }
    if redis_client:
        await redis_client.setex(f"mcp:sessions:{session_id}", SESSION_TTL_SECONDS, json.dumps(meta))
        # store token->latest session (optional)
        await redis_client.setex(f"mcp:token:{hash(token)}", SESSION_TTL_SECONDS, session_id)
    return session_id


async def _bump_session(session_id: str):
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
    meta["last_seen"] = _now_iso()
    meta["calls"] = int(meta.get("calls", 0)) + 1
    await redis_client.setex(key, SESSION_TTL_SECONDS, json.dumps(meta))


async def _check_rate_limit(session_id: str) -> bool:
    if not redis_client:
        return True
    key = f"mcp:ratelimit:{session_id}"
    cur = await redis_client.incr(key)
    if cur == 1:
        await redis_client.expire(key, SESSION_TTL_SECONDS)
    return cur <= RATE_LIMIT_MAX_CALLS


def _tool_schemas() -> List[Dict[str, Any]]:
    return [
        {
            "name": "rag_query",
            "description": "Query the RAG system for relevant code and documentation",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "default": 8},
                    "filters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "language": {"type": "string"},
                            "branch": {"type": "string"}
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
                    "scope": {"type": "string", "enum": ["repo", "tasks", "chat", "all"], "default": "all"}
                }
            }
        },
        {
            "name": "rag_check_blob",
            "description": "Check if blob metadata is present in the RAG system",
            "inputSchema": {
                "type": "object",
                "properties": {"blob_sha": {"type": "string"}},
                "required": ["blob_sha"]
            }
        },
        {
            "name": "rag_get_status",
            "description": "Get RAG system status and statistics",
            "inputSchema": {"type": "object", "properties": {}}
        }
    ]


async def _handle_rag_query(arguments: Dict[str, Any]) -> Dict[str, Any]:
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
    scope = arguments.get("scope", "all")
    repo_path_env = os.getenv("REPO_PATH", "/work/repo")
    from pathlib import Path
    result = await rag_service.reindex_repository(Path(repo_path_env), scope)
    return result


async def _handle_rag_check_blob(arguments: Dict[str, Any]) -> Dict[str, Any]:
    blob_sha = arguments.get("blob_sha")
    if not blob_sha:
        raise ValueError("blob_sha is required")
    return await rag_service.check_blob_metadata(blob_sha)


async def _handle_rag_get_status(arguments: Dict[str, Any]) -> Dict[str, Any]:
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
    global rag_service, redis_client
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/cage")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not openai_key:
        logger.error("OPENAI_API_KEY not set; RAG disabled. Network MCP cannot start.")
        # Still start app to show health, but without RAG functionality it will return 503 on ws
    else:
        rag_service = RAGService(db_url=db_url, redis_url=redis_url, openai_api_key=openai_key)
        await rag_service.initialize()

    redis_client = redis.from_url(redis_url, decode_responses=True)
    try:
        await redis_client.ping()
    except Exception as e:
        logger.error(f"Redis not reachable: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    global rag_service, redis_client
    if rag_service:
        await rag_service.close()
    if redis_client:
        await redis_client.close()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "rag": bool(rag_service is not None),
        "redis": bool(redis_client is not None),
        "time": _now_iso(),
    }


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    # Require RAG initialized
    if rag_service is None:
        await websocket.close(code=1013)  # Try again later
        return

    await websocket.accept()
    try:
        session_id = await _auth_and_create_session(websocket)
    except PermissionError as e:
        await websocket.send_text(json.dumps({"error": {"message": str(e)}}))
        await websocket.close(code=1008)
        return
    except Exception as e:
        await websocket.send_text(json.dumps({"error": {"message": f"Auth error: {e}"}}))
        await websocket.close(code=1011)
        return

    # Send welcome with tools
    await websocket.send_text(json.dumps({
        "type": "session_started",
        "session_id": session_id,
        "tools": _tool_schemas(),
    }))

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": {"message": "invalid JSON"}}))
                continue

            req_id = msg.get("id")
            method = msg.get("method")
            params = msg.get("params") or {}

            # Rate-limit per session
            if not await _check_rate_limit(session_id):
                await websocket.send_text(json.dumps({
                    "id": req_id,
                    "error": {"message": "rate limit exceeded"}
                }))
                continue

            await _bump_session(session_id)

            try:
                if method == "list_tools":
                    result = {"tools": _tool_schemas()}
                elif method == "call_tool":
                    name = (params.get("name") or "").strip()
                    arguments = params.get("arguments") or {}
                    handler = TOOL_DISPATCH.get(name)
                    if not handler:
                        raise ValueError(f"unknown tool: {name}")
                    result = await handler(arguments)
                else:
                    raise ValueError("unknown method")

                await websocket.send_text(json.dumps({"id": req_id, "result": result}))
            except Exception as e:
                await websocket.send_text(json.dumps({"id": req_id, "error": {"message": str(e)}}))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Cleanup session
        if redis_client:
            try:
                await redis_client.delete(f"mcp:sessions:{session_id}")
            except Exception:
                pass

