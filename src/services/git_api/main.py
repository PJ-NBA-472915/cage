"""
Git API Service
Handles Git operations, version control, and repository management.
"""

import datetime
import logging
import os
import sys
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
import uvicorn

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s'
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
    title="Git API Service",
    description="Git operations, version control, and repository management",
    version="1.0.0"
)

# Add middleware
app.add_middleware(RequestIDMiddleware)

# Request/Response models
class GitBranchRequest(BaseModel):
    name: str
    checkout: bool = True

class GitCommitRequest(BaseModel):
    message: str
    author: Optional[str] = None
    task_id: Optional[str] = None

class GitPushRequest(BaseModel):
    remote: str = "origin"
    branch: Optional[str] = None

class GitMergeRequest(BaseModel):
    source_branch: str
    target_branch: str = "main"

class GitRevertRequest(BaseModel):
    branch: str
    to: str

# Health check endpoint
@app.get("/health")
def health():
    """Health check endpoint."""
    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        return {
            "status": "success",
            "service": "git-api",
            "date": current_date,
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "error",
            "service": "git-api",
            "date": current_date,
            "error": str(e)
        }

# Git operations endpoints
@app.get("/git/status")
def git_status(token: str = Depends(get_pod_token)):
    """Get repository status."""
    try:
        # TODO: Implement actual Git status using GitTool
        logger.info("Git status requested")
        
        return {
            "status": "success",
            "branch": "main",
            "clean": True,
            "ahead": 0,
            "behind": 0,
            "modified_files": [],
            "staged_files": []
        }
        
    except Exception as e:
        logger.error(f"Error in git_status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/git/branch")
def get_current_branch(token: str = Depends(get_pod_token)):
    """Get current branch information."""
    try:
        # TODO: Implement actual branch detection
        logger.info("Current branch requested")
        
        return {
            "current": "main",
            "branches": ["main", "develop"],
            "remote_branches": ["origin/main", "origin/develop"]
        }
        
    except Exception as e:
        logger.error(f"Error in get_current_branch: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/git/branch")
def create_branch(request: GitBranchRequest, token: str = Depends(get_pod_token)):
    """Create or switch to a branch."""
    try:
        # TODO: Implement actual branch creation using GitTool
        logger.info(f"Branch operation requested: {request.name}")
        
        return {
            "status": "success",
            "branch": request.name,
            "created": True,
            "checked_out": request.checkout
        }
        
    except Exception as e:
        logger.error(f"Error in create_branch: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/git/commit")
def git_commit(request: GitCommitRequest, token: str = Depends(get_pod_token)):
    """Commit changes to the repository."""
    try:
        # TODO: Implement actual commit using GitTool
        logger.info(f"Commit requested: {request.message}")
        
        return {
            "status": "success",
            "commit_sha": "placeholder-commit-sha",
            "message": request.message,
            "author": request.author or "system",
            "files_committed": 0
        }
        
    except Exception as e:
        logger.error(f"Error in git_commit: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/git/push")
def git_push(request: GitPushRequest, token: str = Depends(get_pod_token)):
    """Push changes to remote repository."""
    try:
        # TODO: Implement actual push using GitTool
        logger.info(f"Push requested to {request.remote}")
        
        return {
            "status": "success",
            "remote": request.remote,
            "branch": request.branch or "main",
            "pushed_commits": 0
        }
        
    except Exception as e:
        logger.error(f"Error in git_push: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/git/pull")
def git_pull(remote: str = "origin", branch: Optional[str] = None, token: str = Depends(get_pod_token)):
    """Pull changes from remote repository."""
    try:
        # TODO: Implement actual pull using GitTool
        logger.info(f"Pull requested from {remote}")
        
        return {
            "status": "success",
            "remote": remote,
            "branch": branch or "main",
            "pulled_commits": 0
        }
        
    except Exception as e:
        logger.error(f"Error in git_pull: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/git/merge")
def git_merge(request: GitMergeRequest, token: str = Depends(get_pod_token)):
    """Merge branches."""
    try:
        # TODO: Implement actual merge using GitTool
        logger.info(f"Merge requested: {request.source_branch} -> {request.target_branch}")
        
        return {
            "status": "success",
            "source_branch": request.source_branch,
            "target_branch": request.target_branch,
            "merge_commit_sha": "placeholder-merge-sha"
        }
        
    except Exception as e:
        logger.error(f"Error in git_merge: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/git/history")
def git_history(limit: int = 10, token: str = Depends(get_pod_token)):
    """Get commit history."""
    try:
        # TODO: Implement actual history using GitTool
        logger.info(f"History requested with limit: {limit}")
        
        return {
            "status": "success",
            "commits": [
                {
                    "sha": "placeholder-sha",
                    "message": "placeholder commit",
                    "author": "system",
                    "date": datetime.datetime.now().isoformat()
                }
            ],
            "total": 1
        }
        
    except Exception as e:
        logger.error(f"Error in git_history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/git/revert")
def git_revert(request: GitRevertRequest, token: str = Depends(get_pod_token)):
    """Revert changes."""
    try:
        # TODO: Implement actual revert using GitTool
        logger.info(f"Revert requested: {request.branch} to {request.to}")
        
        return {
            "status": "success",
            "branch": request.branch,
            "reverted_to": request.to,
            "revert_commit_sha": "placeholder-revert-sha"
        }
        
    except Exception as e:
        logger.error(f"Error in git_revert: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/git/open_pr")
def open_pull_request(
    title: str,
    body: Optional[str] = None,
    source_branch: Optional[str] = None,
    target_branch: str = "main",
    token: str = Depends(get_pod_token)
):
    """Create a pull request."""
    try:
        # TODO: Implement actual PR creation
        logger.info(f"PR requested: {title}")
        
        return {
            "status": "success",
            "pr_number": 1,
            "title": title,
            "body": body,
            "source_branch": source_branch or "feature-branch",
            "target_branch": target_branch,
            "url": "https://github.com/placeholder/pr/1"
        }
        
    except Exception as e:
        logger.error(f"Error in open_pull_request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8002)),
        reload=os.environ.get("RELOAD", "false").lower() == "true"
    )
