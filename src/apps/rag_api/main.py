"""
RAG API Service
Handles Retrieval-Augmented Generation, document search, and knowledge base operations.
"""

import datetime
import logging
import os
import sys
from typing import Any, Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

# Import JSONL logging utilities
from src.cage.utils.jsonl_logger import setup_jsonl_logger
from src.cage.utils.openapi_schema import (
    RAG_API_EXAMPLES,
    add_examples_to_openapi,
    add_response_headers_to_openapi,
    get_standard_openapi_schema,
)
from src.cage.utils.problem_details import setup_problem_detail_handlers
from src.cage.utils.request_id_middleware import EnhancedRequestIDMiddleware
from src.cage.utils.status_codes import validate_pod_token

# Configure JSONL logging
logger = setup_jsonl_logger("rag-api", level=logging.INFO)


# Use enhanced RequestID middleware
RequestIDMiddleware = EnhancedRequestIDMiddleware


# Security
security = HTTPBearer()


def get_pod_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate POD_TOKEN for authentication."""
    expected_token = os.environ.get("POD_TOKEN")
    return validate_pod_token(credentials.credentials, expected_token)


# FastAPI app
app = FastAPI(
    title="RAG API Service",
    description="Retrieval-Augmented Generation, document search, and knowledge base operations",
    version="1.0.0",
)


# Custom OpenAPI schema with Problem Details and examples
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_standard_openapi_schema(
        app=app,
        title="RAG API Service",
        version="1.0.0",
        description="Retrieval-Augmented Generation, document search, and knowledge base operations",
        tags=[
            {"name": "rag", "description": "RAG operations and document search"},
            {"name": "health", "description": "Health check endpoints"},
        ],
    )

    # Add response headers and examples
    openapi_schema = add_response_headers_to_openapi(openapi_schema)
    openapi_schema = add_examples_to_openapi(openapi_schema, RAG_API_EXAMPLES)

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Add middleware
app.add_middleware(RequestIDMiddleware, service_name="rag-api")

# Set up Problem Details exception handlers
setup_problem_detail_handlers(app)


# Request/Response models
class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = 8
    filters: Optional[dict[str, Any]] = None


class RAGReindexRequest(BaseModel):
    paths: Optional[list[str]] = None
    force: bool = False


class SearchHit(BaseModel):
    content: str
    metadata: dict[str, Any]
    score: float
    blob_sha: str


class RAGQueryResponse(BaseModel):
    status: str
    hits: list[SearchHit]
    total: int
    query: str


# Health check endpoint
@app.get("/health")
def health():
    """Health check endpoint."""
    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # TODO: Check database and Redis connections
        return {
            "status": "success",
            "service": "rag-api",
            "date": current_date,
            "version": "1.0.0",
            "database": "connected",  # placeholder
            "redis": "connected",  # placeholder
        }
    except Exception as e:
        return {
            "status": "error",
            "service": "rag-api",
            "date": current_date,
            "error": str(e),
        }


# Kubernetes-style health endpoints
@app.get("/healthz")
def healthz():
    """Kubernetes-style health check endpoint."""
    try:
        # Basic health check - service is running
        return {"status": "healthy", "service": "rag-api"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/readyz")
def readyz():
    """Kubernetes-style readiness check endpoint."""
    try:
        # Readiness check - service is ready to accept traffic
        # For rag-api, we should check database connectivity
        # TODO: Add actual database health check
        return {"status": "ready", "service": "rag-api"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


# RAG operations endpoints
@app.post("/query", response_model=RAGQueryResponse)
async def rag_query(request: RAGQueryRequest, token: str = Depends(get_pod_token)):
    """Query RAG system for relevant documents."""
    try:
        # TODO: Implement actual RAG query using RAGService
        logger.info(f"RAG query requested: {request.query}")

        # Placeholder response
        hits = [
            SearchHit(
                content="Placeholder content for query: " + request.query,
                metadata={
                    "path": "placeholder/path.md",
                    "language": "markdown",
                    "commit_sha": "placeholder-sha",
                    "branch": "main",
                    "chunk_id": "chunk-1",
                },
                score=0.95,
                blob_sha="placeholder-blob-sha",
            )
        ]

        return RAGQueryResponse(
            status="success", hits=hits, total=len(hits), query=request.query
        )

    except Exception as e:
        logger.error(f"Error in rag_query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reindex")
async def rag_reindex(request: RAGReindexRequest, token: str = Depends(get_pod_token)):
    """Reindex documents in the RAG system."""
    try:
        # TODO: Implement actual reindexing using RAGService
        logger.info(f"RAG reindex requested for paths: {request.paths}")

        return {
            "status": "success",
            "message": "Reindexing completed",
            "paths_processed": request.paths or ["all"],
            "documents_indexed": 0,
            "force": request.force,
        }

    except Exception as e:
        logger.error(f"Error in rag_reindex: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/blobs/{sha}")
def get_blob_content(sha: str, token: str = Depends(get_pod_token)):
    """Get blob content by SHA."""
    try:
        # TODO: Implement actual blob retrieval
        logger.info(f"Blob content requested for SHA: {sha}")

        return {
            "sha": sha,
            "content": "Placeholder blob content",
            "size": 0,
            "type": "text",
            "encoding": "utf-8",
        }

    except Exception as e:
        logger.error(f"Error in get_blob_content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
def get_rag_stats(token: str = Depends(get_pod_token)):
    """Get RAG system statistics."""
    try:
        # TODO: Implement actual stats collection
        logger.info("RAG stats requested")

        return {
            "status": "success",
            "total_documents": 0,
            "total_chunks": 0,
            "index_size_mb": 0,
            "last_indexed": datetime.datetime.now().isoformat(),
            "database_status": "connected",
            "redis_status": "connected",
        }

    except Exception as e:
        logger.error(f"Error in get_rag_stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health-detailed")
def rag_health_check(token: str = Depends(get_pod_token)):
    """Detailed health check for RAG system components."""
    try:
        # TODO: Implement actual health checks for database and Redis
        logger.info("RAG health check requested")

        return {
            "status": "healthy",
            "components": {
                "database": {"status": "connected", "response_time_ms": 10},
                "redis": {"status": "connected", "response_time_ms": 5},
                "embedding_service": {
                    "status": "available",
                    "model": "text-embedding-3-small",
                },
            },
            "timestamp": datetime.datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in rag_health_check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8003)),
        reload=os.environ.get("RELOAD", "false").lower() == "true",
    )
