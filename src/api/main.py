import datetime
import json
import logging
import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import task management
from src.cage.task_models import TaskManager, TaskFile
from src.cage.editor_tool import EditorTool, FileOperation, OperationType

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

app = FastAPI(
    title="Cage Pod API",
    description="Pod-based Multi-Agent Repository Service",
    version="0.1.0"
)

# Initialize task manager
task_manager = TaskManager(Path("tasks"))

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

def get_repository_path():
    """Get the repository path from environment variable."""
    repo_path = os.environ.get("REPO_PATH", "/work/repo")
    return Path(repo_path)

# Initialize editor tool
editor_tool = EditorTool(get_repository_path(), task_manager=task_manager)

# Pydantic models for new Cage specification

class TaskConfirmRequest(BaseModel):
    task_id: str
    status: str = "confirmed"

class TaskUpdateRequest(BaseModel):
    status: str | None = None
    progress_percent: int | None = None
    logs: list[str] | None = None

class CrewPlanRequest(BaseModel):
    task_id: str
    plan: dict

class CrewApplyRequest(BaseModel):
    task_id: str
    run_id: str | None = None

class FileEditRequest(BaseModel):
    operation: str  # GET, INSERT, UPDATE, DELETE
    path: str
    selector: dict
    payload: dict | None = None
    intent: str
    dry_run: bool = False
    author: str
    correlation_id: str

class GitBranchRequest(BaseModel):
    name: str
    from_branch: str = "main"

class GitCommitRequest(BaseModel):
    message: str
    include_audits: list[str] | None = None
    coauthors: list[str] | None = None

class GitPushRequest(BaseModel):
    remote: str = "origin"
    branch: str | None = None

class GitPullRequest(BaseModel):
    remote: str = "origin"
    branch: str | None = None

class GitMergeRequest(BaseModel):
    source: str
    target: str | None = None

class RAGQueryRequest(BaseModel):
    query: str
    filters: dict | None = None
    top_k: int = 8

class RAGReindexRequest(BaseModel):
    scope: str  # repo, tasks, chat, all

# API Endpoints according to new Cage specification

@app.get("/health")
def health():
    """Health check endpoint."""
    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        repo_path = get_repository_path()
        
        return {
            "status": "success",
            "date": current_date,
            "repo_path": str(repo_path),
            "branch": "main",  # TODO: implement actual branch detection
            "last_index_at": None  # TODO: implement RAG indexing
        }
    except Exception as e:
        return {
            "status": "error",
            "date": current_date,
            "error": str(e)
        }
    
@app.get("/about")
def about():
    """About endpoint with pod information."""
    return {
        "pod_id": os.environ.get("POD_ID", "dev-pod"),
        "version": "0.1.0",
        "capabilities": ["tasks", "crew", "files", "git", "rag"],
        "repo_remote": "origin",  # TODO: implement actual remote detection
        "labels": []  # TODO: implement labels
    }

# Tasks & Status endpoints
@app.post("/tasks/confirm")
def confirm_task(request: TaskConfirmRequest, token: str = Depends(get_pod_token)):
    """Create/update task file."""
    try:
        # Check if task already exists
        existing_task = task_manager.load_task(request.task_id)
        
        if existing_task:
            # Update existing task status
            updates = {"status": request.status}
            task = task_manager.update_task(request.task_id, updates)
            if task:
                logger.info(f"Updated task {request.task_id} status to {request.status}")
                return {"status": "success", "task_id": request.task_id, "action": "updated"}
            else:
                raise HTTPException(status_code=500, detail="Failed to update task")
        else:
            # Create new task with basic structure
            task_data = {
                "id": request.task_id,
                "title": f"Task {request.task_id}",
                "owner": "system",
                "status": request.status,
                "summary": "Auto-created task",
                "tags": [],
                "success_criteria": [],
                "acceptance_checks": [],
                "subtasks": [],
                "todo": [],
                "decisions": [],
                "issues_risks": [],
                "next_steps": [],
                "references": [],
                "metadata": {}
            }
            
            task = task_manager.create_task(task_data)
            if task:
                logger.info(f"Created new task {request.task_id}")
                return {"status": "success", "task_id": request.task_id, "action": "created"}
            else:
                raise HTTPException(status_code=500, detail="Failed to create task")
                
    except Exception as e:
        logger.error(f"Error in confirm_task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/tasks/{task_id}")
def update_task(task_id: str, request: TaskUpdateRequest, token: str = Depends(get_pod_token)):
    """Update task fields."""
    try:
        # Convert request to update dict, filtering out None values
        updates = {k: v for k, v in request.dict().items() if v is not None}
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        task = task_manager.update_task(task_id, updates)
        if task:
            logger.info(f"Updated task {task_id}")
            return {"status": "success", "task_id": task_id, "updated_fields": list(updates.keys())}
        else:
            raise HTTPException(status_code=404, detail="Task not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/{task_id}")
def get_task(task_id: str, token: str = Depends(get_pod_token)):
    """Get full task JSON."""
    try:
        task = task_manager.load_task(task_id)
        if task:
            return task.dict()
        else:
            raise HTTPException(status_code=404, detail="Task not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks")
def list_tasks(token: str = Depends(get_pod_token)):
    """List all tasks."""
    try:
        tasks = task_manager.list_tasks()
        return {"status": "success", "tasks": tasks, "count": len(tasks)}
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tracker/rebuild")
def rebuild_tracker(token: str = Depends(get_pod_token)):
    """Rebuild tracker from task files."""
    try:
        status_data = task_manager.rebuild_status()
        logger.info("Rebuilt task tracker")
        return {
            "status": "success", 
            "message": "Tracker rebuilt successfully",
            "active_tasks": len(status_data.get("active_tasks", [])),
            "recently_completed": len(status_data.get("recently_completed", []))
        }
    except Exception as e:
        logger.error(f"Error rebuilding tracker: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Crew endpoints
@app.post("/crew/plan")
def crew_plan(request: CrewPlanRequest, token: str = Depends(get_pod_token)):
    """Write/merge task plan."""
    # TODO: Implement CrewAI planning
    return {"status": "success", "task_id": request.task_id}

@app.post("/crew/apply")
def crew_apply(request: CrewApplyRequest, token: str = Depends(get_pod_token)):
    """Apply crew changes through Editor Tool."""
    # TODO: Implement CrewAI application
    return {"status": "success", "task_id": request.task_id}

@app.get("/crew/runs/{run_id}")
def get_crew_run(run_id: str, token: str = Depends(get_pod_token)):
    """Get crew run status/logs/summary."""
    # TODO: Implement crew run retrieval
    return {"run_id": run_id, "status": "not_implemented"}

@app.post("/crew/runs/{run_id}/artefacts")
def upload_artefacts(run_id: str, token: str = Depends(get_pod_token)):
    """Upload files into .cage/runs/<run_id>/*."""
    # TODO: Implement artefact upload
    return {"status": "success", "run_id": run_id}

# Files (Editor Tool) endpoints
@app.post("/files/edit")
def edit_file(request: FileEditRequest, token: str = Depends(get_pod_token)):
    """Structured file operations with locking."""
    try:
        # Convert operation string to enum
        try:
            operation_type = OperationType(request.operation)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid operation: {request.operation}")
        
        # Create file operation
        operation = FileOperation(
            operation=operation_type,
            path=request.path,
            selector=request.selector,
            payload=request.payload,
            intent=request.intent,
            dry_run=request.dry_run,
            author=request.author,
            correlation_id=request.correlation_id
        )
        
        # Execute operation
        result = editor_tool.execute_operation(operation)
        
        # Convert result to response format
        response = {
            "ok": result.ok,
            "file": result.file,
            "operation": result.operation,
            "lock_id": result.lock_id,
            "pre_hash": result.pre_hash,
            "post_hash": result.post_hash,
            "diff": result.diff,
            "warnings": result.warnings,
            "conflicts": result.conflicts
        }
        
        if not result.ok:
            response["error"] = result.error
            logger.error(f"File operation failed: {result.error}")
            raise HTTPException(status_code=400, detail=result.error)
        
        logger.info(f"File operation completed: {operation_type.value} on {request.path}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in edit_file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Git endpoints
@app.get("/git/status")
def git_status(token: str = Depends(get_pod_token)):
    """Get Git status."""
    # TODO: Implement Git status
    return {"status": "not_implemented"}

@app.post("/git/branch")
def create_branch(request: GitBranchRequest, token: str = Depends(get_pod_token)):
    """Create Git branch."""
    # TODO: Implement Git branch creation
    return {"status": "success", "branch": request.name}

@app.post("/git/commit")
def create_commit(request: GitCommitRequest, token: str = Depends(get_pod_token)):
    """Create Git commit."""
    # TODO: Implement Git commit
    return {"status": "success", "message": "Commit not yet implemented"}

@app.post("/git/push")
def push_changes(request: GitPushRequest, token: str = Depends(get_pod_token)):
    """Push changes to remote."""
    # TODO: Implement Git push
    return {"status": "success", "message": "Push not yet implemented"}

@app.post("/git/pull")
def pull_changes(request: GitPullRequest, token: str = Depends(get_pod_token)):
    """Pull changes from remote."""
    # TODO: Implement Git pull
    return {"status": "success", "message": "Pull not yet implemented"}

@app.post("/git/merge")
def merge_branches(request: GitMergeRequest, token: str = Depends(get_pod_token)):
    """Merge branches."""
    # TODO: Implement Git merge
    return {"status": "success", "message": "Merge not yet implemented"}

# RAG endpoints
@app.post("/rag/query")
def rag_query(request: RAGQueryRequest, token: str = Depends(get_pod_token)):
    """Query RAG system."""
    # TODO: Implement RAG query
    return {"hits": [], "message": "RAG not yet implemented"}

@app.post("/rag/reindex")
def rag_reindex(request: RAGReindexRequest, token: str = Depends(get_pod_token)):
    """Reindex RAG system."""
    # TODO: Implement RAG reindexing
    return {"status": "success", "scope": request.scope}

@app.get("/rag/blobs/{sha}")
def get_rag_blob(sha: str, token: str = Depends(get_pod_token)):
    """Check if blob metadata is present."""
    # TODO: Implement blob metadata check
    return {"present": False, "sha": sha}

# Webhooks endpoint
@app.post("/webhooks")
def register_webhook(token: str = Depends(get_pod_token)):
    """Register webhook."""
    # TODO: Implement webhook registration
    return {"status": "success", "message": "Webhooks not yet implemented"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)