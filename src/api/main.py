import datetime
import json
import logging
import os
import sys
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from cage import repo

class RepoInitRequest(BaseModel):
    origin: str
    agent_id: str | None = None
    branch: str | None = None
    task_slug: str | None = None
    no_shallow: bool = False

class RepoCloseRequest(BaseModel):
    path: str
    message: str
    agent_id: str | None = None
    task_id: str | None = None
    remote: str = "origin"
    allow_empty: bool = False
    require_changes: bool = False
    signoff: bool = False
    no_verify: bool = False
    merge: bool = False
    target_branch: str = "main"

app = FastAPI()

# Configure logging
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "api.log")
os.makedirs(LOG_DIR, exist_ok=True)

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "file": record.filename,
            "line": record.lineno,
        }
        if hasattr(record, 'json_data'):
            log_record.update(record.json_data)
        return json.dumps(log_record)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(JsonFormatter())
logger.addHandler(file_handler)

@app.get("/health")
def health():
    """Perform a health check."""
    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    response = {"status": "success", "date": current_date}
    logger.info("Health check performed", extra={'json_data': response})
    return response

@app.get("/repos")
def repo_list(status: str = None):
    """List open repositories, optionally filtered by status."""
    try:
        if status:
            repositories = repo.get_open_repositories(status_filter=status.split(','))
        else:
            repositories = repo.get_open_repositories()
        
        if repositories:
            return repositories
        else:
            return {"message": "No repositories found matching the criteria."}
    except Exception as e:
        return {"error": str(e)}

@app.post("/repos")
def repo_init(request: RepoInitRequest):
    """Initialise a working copy of a repository."""
    try:
        metadata = repo.init(
            origin=request.origin,
            agent_id=request.agent_id,
            branch=request.branch,
            shallow=not request.no_shallow,
            task_slug=request.task_slug
        )
        return metadata
    except Exception as e:
        return {"error": str(e)}

@app.post("/repos/close")
def repo_close(request: RepoCloseRequest):
    """Finalise a clone's work, commit, and push."""
    try:
        repo.close(
            path=request.path,
            message=request.message,
            agent_id=request.agent_id,
            task_id=request.task_id,
            remote=request.remote,
            allow_empty=request.allow_empty,
            require_changes=request.require_changes,
            signoff=request.signoff,
            no_verify=request.no_verify,
            merge=request.merge,
            target_branch=request.target_branch
        )
        return {"status": "success", "message": "Repository closed successfully."}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
