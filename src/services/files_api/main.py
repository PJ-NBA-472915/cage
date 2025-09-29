"""
Files API Service
Handles file operations, content management, and file locking.
"""

import datetime
import logging
import os
import sys
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
import uvicorn

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Import file editing utilities
from src.cage.utils.file_editing_utils import PathValidator
from src.cage.utils.file_logging import file_logger

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID to all requests."""
    
    async def dispatch(self, request: Request, call_next):
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Set up logging context
        old_factory = logging.getLogRecordFactory()
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.request_id = request_id
            return record
        logging.setLogRecordFactory(record_factory)
        
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            # Restore original factory
            logging.setLogRecordFactory(old_factory)

# Security
security = HTTPBearer()

def get_pod_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate POD_TOKEN for authentication."""
    expected_token = os.environ.get("POD_TOKEN")
    if not expected_token:
        raise HTTPException(status_code=500, detail="POD_TOKEN not configured")
    if credentials.credentials != expected_token:
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials.credentials

# FastAPI app
app = FastAPI(
    title="Files API Service",
    description="File operations, content management, and file locking",
    version="1.0.0"
)

# Add middleware
app.add_middleware(RequestIDMiddleware)

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
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "error",
            "service": "files-api",
            "date": current_date,
            "error": str(e)
        }

# File operations endpoints
@app.post("/files/edit", response_model=FileEditResponse)
def edit_file(request: FileEditRequest, token: str = Depends(get_pod_token)):
    """Structured file operations with locking."""
    try:
        # TODO: Implement actual file operations using EditorTool
        logger.info(f"File operation requested: {request.operation} on {request.path}")
        
        # Placeholder response
        return FileEditResponse(
            ok=True,
            file=request.path,
            operation=request.operation,
            lock_id="placeholder-lock-id",
            pre_hash="placeholder-pre-hash",
            post_hash="placeholder-post-hash",
            diff="placeholder-diff"
        )
        
    except Exception as e:
        logger.error(f"Error in edit_file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/files/commit")
def commit_file_changes(
    message: str,
    task_id: Optional[str] = None,
    author: Optional[str] = None,
    token: str = Depends(get_pod_token)
):
    """Commit file changes."""
    try:
        # TODO: Implement actual commit logic
        logger.info(f"Commit requested: {message}")
        
        return {
            "status": "success",
            "message": "Files committed successfully",
            "commit_sha": "placeholder-commit-sha"
        }
        
    except Exception as e:
        logger.error(f"Error in commit_file_changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/sha")
def get_file_sha(path: str, token: str = Depends(get_pod_token)):
    """Get file SHA for validation."""
    try:
        # TODO: Implement actual SHA calculation
        logger.info(f"SHA requested for: {path}")
        
        return {
            "path": path,
            "sha": "placeholder-sha",
            "size": 0
        }
        
    except Exception as e:
        logger.error(f"Error in get_file_sha: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/diff")
def get_diff(branch: Optional[str] = None, token: str = Depends(get_pod_token)):
    """Get diff for change validation."""
    try:
        # TODO: Implement actual diff generation
        logger.info(f"Diff requested for branch: {branch}")
        
        return {
            "branch": branch or "main",
            "diff": "placeholder-diff",
            "files_changed": 0
        }
        
    except Exception as e:
        logger.error(f"Error in get_diff: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8001)),
        reload=os.environ.get("RELOAD", "false").lower() == "true"
    )
