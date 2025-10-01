"""
Files API Service
Handles file operations, content management, and file locking.
"""

import datetime
import logging
import os
import sys
from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

# Import file editing utilities
from src.cage.utils.file_editing_utils import PathValidator
from src.cage.utils.jsonl_logger import log_with_context, setup_jsonl_logger
from src.cage.utils.openapi_schema import (
    FILES_API_EXAMPLES,
    add_examples_to_openapi,
    add_response_headers_to_openapi,
    get_standard_openapi_schema,
)
from src.cage.utils.problem_details import setup_problem_detail_handlers
from src.cage.utils.request_id_middleware import EnhancedRequestIDMiddleware
from src.cage.utils.status_codes import validate_pod_token

# Configure JSONL logging
logger = setup_jsonl_logger("files-api", level=logging.INFO)


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
    title="Files API Service",
    description="File operations, content management, and file locking",
    version="1.0.0",
)


# Custom OpenAPI schema with Problem Details and examples
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_standard_openapi_schema(
        app=app,
        title="Files API Service",
        version="1.0.0",
        description="File operations, content management, and file locking",
        tags=[
            {"name": "files", "description": "File operations and management"},
            {"name": "health", "description": "Health check endpoints"},
        ],
    )

    # Add response headers and examples
    openapi_schema = add_response_headers_to_openapi(openapi_schema)
    openapi_schema = add_examples_to_openapi(openapi_schema, FILES_API_EXAMPLES)

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Add middleware
app.add_middleware(RequestIDMiddleware, service_name="files-api")

# Set up Problem Details exception handlers
setup_problem_detail_handlers(app)

# Initialize path validator with restricted container access
repo_path = os.environ.get("REPO_PATH", "/work/repo")
path_validator = PathValidator(repo_path)
logger.info(f"Files API initialized with repo path: {repo_path}")


# Request/Response models
class FileEditRequest(BaseModel):
    operation: str
    path: str
    selector: Optional[str] = None
    payload: Optional[dict] = None
    intent: Optional[str] = None
    dry_run: bool = False
    author: Optional[str] = None
    correlation_id: Optional[str] = None


class FileEditResponse(BaseModel):
    ok: bool
    file: str
    operation: str
    lock_id: Optional[str] = None
    pre_hash: Optional[str] = None
    post_hash: Optional[str] = None
    diff: Optional[str] = None
    warnings: list = []
    conflicts: list = []
    error: Optional[str] = None


# Health check endpoint
@app.get("/health")
def health():
    """Health check endpoint."""
    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        return {
            "status": "success",
            "service": "files-api",
            "date": current_date,
            "version": "1.0.0",
        }
    except Exception as e:
        return {
            "status": "error",
            "service": "files-api",
            "date": current_date,
            "error": str(e),
        }


# Kubernetes-style health endpoints
@app.get("/healthz")
def healthz():
    """Kubernetes-style health check endpoint."""
    try:
        # Basic health check - service is running
        return {"status": "healthy", "service": "files-api"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/readyz")
def readyz():
    """Kubernetes-style readiness check endpoint."""
    try:
        # Readiness check - service is ready to accept traffic
        # For files-api, we just need to verify the service is running
        return {"status": "ready", "service": "files-api"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


# File operations endpoints
@app.post("/edit", response_model=FileEditResponse)
def edit_file(
    request: FileEditRequest, http_request: Request, token: str = Depends(get_pod_token)
):
    """Structured file operations with locking."""
    try:
        # TODO: Implement actual file operations using EditorTool
        log_with_context(
            logger,
            logging.INFO,
            f"File operation requested: {request.operation} on {request.path}",
            request_id=getattr(http_request.state, "request_id", None),
            route="/files/edit",
            operation=request.operation,
            path=request.path,
        )

        # Placeholder response
        return FileEditResponse(
            ok=True,
            file=request.path,
            operation=request.operation,
            lock_id="placeholder-lock-id",
            pre_hash="placeholder-pre-hash",
            post_hash="placeholder-post-hash",
            diff="placeholder-diff",
        )

    except Exception as e:
        import traceback

        log_with_context(
            logger,
            logging.ERROR,
            f"Error in edit_file: {e}",
            request_id=getattr(http_request.state, "request_id", None),
            route="/files/edit",
            error=str(e),
            stack=traceback.format_exc(),
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/commit")
def commit_file_changes(
    message: str,
    http_request: Request,
    task_id: Optional[str] = None,
    author: Optional[str] = None,
    token: str = Depends(get_pod_token),
):
    """Commit file changes."""
    try:
        # TODO: Implement actual commit logic
        log_with_context(
            logger,
            logging.INFO,
            f"Commit requested: {message}",
            request_id=getattr(http_request.state, "request_id", None),
            route="/files/commit",
            message=message,
            task_id=task_id,
            author=author,
        )

        return {
            "status": "success",
            "message": "Files committed successfully",
            "commit_sha": "placeholder-commit-sha",
        }

    except Exception as e:
        import traceback

        log_with_context(
            logger,
            logging.ERROR,
            f"Error in commit_file_changes: {e}",
            request_id=getattr(http_request.state, "request_id", None),
            route="/files/commit",
            error=str(e),
            stack=traceback.format_exc(),
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sha")
def get_file_sha(path: str, http_request: Request, token: str = Depends(get_pod_token)):
    """Get file SHA for validation."""
    try:
        # TODO: Implement actual SHA calculation
        log_with_context(
            logger,
            logging.INFO,
            f"SHA requested for: {path}",
            request_id=getattr(http_request.state, "request_id", None),
            route="/files/sha",
            path=path,
        )

        return {"path": path, "sha": "placeholder-sha", "size": 0}

    except Exception as e:
        import traceback

        log_with_context(
            logger,
            logging.ERROR,
            f"Error in get_file_sha: {e}",
            request_id=getattr(http_request.state, "request_id", None),
            route="/files/sha",
            error=str(e),
            stack=traceback.format_exc(),
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/diff")
def get_diff(
    http_request: Request,
    branch: Optional[str] = None,
    token: str = Depends(get_pod_token),
):
    """Get diff for change validation."""
    try:
        # TODO: Implement actual diff generation
        log_with_context(
            logger,
            logging.INFO,
            f"Diff requested for branch: {branch}",
            request_id=getattr(http_request.state, "request_id", None)
            if http_request
            else None,
            route="/diff",
            branch=branch,
        )

        return {
            "branch": branch or "main",
            "diff": "placeholder-diff",
            "files_changed": 0,
        }

    except Exception as e:
        import traceback

        log_with_context(
            logger,
            logging.ERROR,
            f"Error in get_diff: {e}",
            request_id=getattr(http_request.state, "request_id", None),
            route="/diff",
            error=str(e),
            stack=traceback.format_exc(),
        )
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8001)),
        reload=os.environ.get("RELOAD", "false").lower() == "true",
    )
