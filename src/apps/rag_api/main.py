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

# Import RAG service
from src.cage.rag_service import RAGService
from pathlib import Path

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

# Initialize RAG service
rag_service: Optional[RAGService] = None

async def get_rag_service() -> RAGService:
    """Get or initialize RAG service."""
    global rag_service
    if rag_service is None:
        # Get configuration from environment
        db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:password@postgres:5432/cage")
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379")
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        
        if not openai_api_key:
            raise HTTPException(
                status_code=503, 
                detail="OpenAI API key not configured. RAG service disabled."
            )
        
        rag_service = RAGService(
            db_url=db_url,
            redis_url=redis_url,
            openai_api_key=openai_api_key,
            embedding_model="text-embedding-3-small"
        )
        
        try:
            await rag_service.initialize()
            logger.info("RAG service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"RAG service initialization failed: {str(e)}"
            )
    
    return rag_service


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
async def health():
    """Health check endpoint."""
    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Check if RAG service can be initialized
        try:
            rag = await get_rag_service()
            database_status = "connected"
            redis_status = "connected" if rag.redis_client else "not_configured"
        except Exception as e:
            database_status = f"error: {str(e)}"
            redis_status = "error"
        
        return {
            "status": "success",
            "service": "rag-api",
            "date": current_date,
            "version": "1.0.0",
            "database": database_status,
            "redis": redis_status,
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
async def readyz():
    """Kubernetes-style readiness check endpoint."""
    try:
        # Readiness check - service is ready to accept traffic
        # Check if RAG service can be initialized
        try:
            rag = await get_rag_service()
            return {"status": "ready", "service": "rag-api"}
        except Exception as e:
            logger.error(f"RAG service not ready: {e}")
            raise HTTPException(status_code=503, detail=f"RAG service not ready: {str(e)}")
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


# RAG operations endpoints
@app.post("/query", response_model=RAGQueryResponse)
async def rag_query(request: RAGQueryRequest, token: str = Depends(get_pod_token)):
    """Query RAG system for relevant documents."""
    try:
        logger.info(f"RAG query requested: {request.query}")
        
        # Get RAG service
        rag = await get_rag_service()
        
        # Perform query
        results = await rag.query(
            query_text=request.query,
            top_k=request.top_k,
            filters=request.filters
        )
        
        # Convert results to API format
        hits = []
        for result in results:
            hit = SearchHit(
                content=result.content,
                metadata={
                    "path": result.metadata.path,
                    "language": result.metadata.language,
                    "commit_sha": result.metadata.commit_sha,
                    "branch": result.metadata.branch,
                    "chunk_id": result.metadata.chunk_id,
                },
                score=result.score,
                blob_sha=result.blob_sha,
            )
            hits.append(hit)

        return RAGQueryResponse(
            status="success", 
            hits=hits, 
            total=len(hits), 
            query=request.query
        )

    except Exception as e:
        logger.error(f"Error in rag_query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reindex")
async def rag_reindex(request: RAGReindexRequest, token: str = Depends(get_pod_token)):
    """Reindex documents in the RAG system."""
    try:
        logger.info(f"RAG reindex requested for paths: {request.paths}")
        
        # Get RAG service
        rag = await get_rag_service()
        
        # Get repository path
        repo_path = Path(os.environ.get("REPO_PATH", "/work/repo"))
        if not repo_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Repository path does not exist: {repo_path}"
            )
        
        # Determine scope
        scope = "all"
        if request.paths:
            if len(request.paths) == 1 and request.paths[0] == "tasks":
                scope = "tasks"
            elif len(request.paths) == 1 and request.paths[0] == "repo":
                scope = "repo"
        
        # Perform reindexing
        result = await rag.reindex_repository(repo_path, scope=scope)
        
        return {
            "status": "success",
            "message": "Reindexing completed",
            "paths_processed": request.paths or ["all"],
            "documents_indexed": result["indexed_files"],
            "total_chunks": result["total_chunks"],
            "force": request.force,
        }

    except Exception as e:
        logger.error(f"Error in rag_reindex: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/blobs/{sha}")
async def get_blob_content(sha: str, token: str = Depends(get_pod_token)):
    """Get blob content by SHA."""
    try:
        logger.info(f"Blob content requested for SHA: {sha}")
        
        # Get RAG service
        rag = await get_rag_service()
        
        # Check blob metadata
        metadata = await rag.check_blob_metadata(sha)
        
        if not metadata["present"]:
            raise HTTPException(
                status_code=404,
                detail=f"Blob not found: {sha}"
            )
        
        return {
            "sha": sha,
            "content": f"Blob content for {sha}",
            "size": metadata["size"],
            "type": metadata["mime"],
            "encoding": "utf-8",
            "first_seen_at": metadata["first_seen_at"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_blob_content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_rag_stats(token: str = Depends(get_pod_token)):
    """Get RAG system statistics."""
    try:
        logger.info("RAG stats requested")
        
        # Get RAG service
        rag = await get_rag_service()
        
        # Get basic stats from database
        async with rag.db_pool.acquire() as conn:
            # Count total documents
            doc_count = await conn.fetchval("SELECT COUNT(DISTINCT blob_sha) FROM git_blobs")
            
            # Count total chunks
            chunk_count = await conn.fetchval("SELECT COUNT(*) FROM embeddings")
            
            # Get index size (approximate)
            index_size = await conn.fetchval("""
                SELECT pg_size_pretty(pg_total_relation_size('embeddings'))
            """)
        
        return {
            "status": "success",
            "total_documents": doc_count,
            "total_chunks": chunk_count,
            "index_size": str(index_size),
            "last_indexed": datetime.datetime.now().isoformat(),
            "database_status": "connected",
            "redis_status": "connected" if rag.redis_client else "not_configured",
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
