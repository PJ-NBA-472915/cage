import datetime
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Dict
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
import uvicorn

# Debugpy integration for container debugging
if os.getenv("DEBUGPY_ENABLED", "0") == "1":
    import debugpy
    try:
        debugpy.listen(("0.0.0.0", 5678))
        if os.getenv("DEBUGPY_WAIT_FOR_CLIENT", "0") == "1":
            debugpy.wait_for_client()
        print("Debugpy enabled - waiting for debugger to attach on port 5678")
    except RuntimeError as e:
        if "Address already in use" in str(e):
            print("Debugpy port 5678 already in use, skipping debugpy setup")
        else:
            raise

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import task management
from src.cage.models import TaskManager, TaskFile
from src.cage.tools.editor_tool import EditorTool, FileOperation, OperationType
from src.cage.tools.git_tool import GitTool
from src.cage.tools.crew_tool import CrewTool
from src.cage.tools.crew_tool import ModularCrewTool
from src.cage.rag_service import RAGService

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

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = datetime.datetime.utcnow()
        
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
            duration_ms = (datetime.datetime.utcnow() - start_time).total_seconds() * 1000
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
            duration_ms = (datetime.datetime.utcnow() - start_time).total_seconds() * 1000
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

app = FastAPI(
    title="Cage Pod API",
    description="Pod-based Multi-Agent Repository Service",
    version="0.1.0"
)

# Disable uvicorn access logging to avoid duplicate logs
uvicorn_logger = logging.getLogger("uvicorn.access")
uvicorn_logger.disabled = True

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure daily logging
from src.cage.utils.daily_logger import setup_daily_logger

logger = setup_daily_logger("api", level=logging.INFO)

def get_repository_path():
    """Get the repository path from environment variable."""
    repo_path = os.environ.get("REPO_PATH", "/work/repo")
    return Path(repo_path)

# Initialize task manager and git tool
repo_path = get_repository_path()
tasks_dir = repo_path / ".cage" / "tasks"
# Ensure .cage directory exists
(repo_path / ".cage").mkdir(exist_ok=True)
task_manager = TaskManager(tasks_dir)
git_tool = GitTool(repo_path)
crew_tool = CrewTool(repo_path, task_manager)
modular_crew_tool = ModularCrewTool(repo_path, task_manager)

# Initialize RAG service
rag_service = None

# Initialize editor tool
editor_tool = EditorTool(repo_path, task_manager=task_manager)

# Initialize RAG service on startup
@app.on_event("startup")
async def startup_event():
    """Initialize RAG service on startup."""
    global rag_service
    try:
        db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:password@localhost:5432/cage")
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        
        if not openai_api_key:
            logger.warning("OPENAI_API_KEY not set, RAG service disabled. Please set OPENAI_API_KEY to enable RAG.")
            logger.info("DEBUG: OPENAI_API_KEY is not set.")
            return
        
        if openai_api_key == "sk-test":
            logger.error("Invalid OpenAI API key 'sk-test' detected. RAG service disabled. Please provide a valid key.")
            return
        
        logger.info(f"DEBUG: OPENAI_API_KEY is set (masked: {openai_api_key[:5]}...{openai_api_key[-4:]})")

        rag_service = RAGService(
            db_url=db_url,
            redis_url=redis_url,
            openai_api_key=openai_api_key
        )
        await rag_service.initialize()
        logger.info("RAG service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG service: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global rag_service
    if rag_service:
        await rag_service.close()
        logger.info("RAG service closed")

# Pydantic models for new Cage specification

class TaskConfirmRequest(BaseModel):
    task_id: str
    status: str = "confirmed"

class TaskCreateRequest(BaseModel):
    """Request model for creating a complete task."""
    id: str
    title: str
    owner: str
    status: str = "planned"
    progress_percent: int = 0
    tags: list[str] = []
    summary: str = ""
    success_criteria: list[dict] = []
    acceptance_checks: list[dict] = []
    subtasks: list[str] = []
    todo: list[dict] = []
    decisions: list[str] = []
    lessons_learned: list[str] = []
    issues_risks: list[str] = []
    next_steps: list[str] = []
    references: list[str] = []
    metadata: dict = {}

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
    selector: dict | None = None
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

class AgentRequest(BaseModel):
    agent: str
    request: str
    task_id: Optional[str] = None

# Note-taking API models
class NoteCreateRequest(BaseModel):
    title: str
    content: str

class NoteUpdateRequest(BaseModel):
    title: str | None = None
    content: str | None = None

class NoteResponse(BaseModel):
    id: str
    title: str
    content: str
    created_at: str
    updated_at: str
    file_path: str

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
@app.post("/tasks/create")
def create_task(request: TaskCreateRequest, token: str = Depends(get_pod_token)):
    """Create a new task with full data from request body."""
    try:
        # Check if task already exists
        existing_task = task_manager.load_task(request.id)
        
        if existing_task:
            raise HTTPException(status_code=409, detail=f"Task {request.id} already exists")
        
        # Convert request data to task data
        task_data = {
            "id": request.id,
            "title": request.title,
            "owner": request.owner,
            "status": request.status,
            "progress_percent": request.progress_percent,
            "tags": request.tags,
            "summary": request.summary,
            "success_criteria": request.success_criteria,
            "acceptance_checks": request.acceptance_checks,
            "subtasks": request.subtasks,
            "todo": request.todo,
            "decisions": request.decisions,
            "lessons_learned": request.lessons_learned,
            "issues_risks": request.issues_risks,
            "next_steps": request.next_steps,
            "references": request.references,
            "metadata": request.metadata
        }
        
        # Create the task
        task = task_manager.create_task(task_data)
        if task:
            logger.info(f"Created new task {request.id} with full data")
            return {
                "status": "success", 
                "task_id": request.id, 
                "action": "created",
                "task": task.model_dump()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create task")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
            # Map "confirmed" status to "planned" since "confirmed" is not in the allowed pattern
            mapped_status = "planned" if request.status == "confirmed" else request.status
            task_data = {
                "id": request.task_id,
                "title": f"Task {request.task_id}",
                "owner": "system",
                "status": mapped_status,
                "progress_percent": 0,
                "summary": "Auto-created task",
                "tags": [],
                "success_criteria": [],
                "acceptance_checks": [],
                "subtasks": [],
                "todo": [],
                "decisions": [],
                "lessons_learned": [],
                "issues_risks": [],
                "next_steps": [],
                "references": [],
                "prompts": [],
                "locks": [],
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
            return task.model_dump()
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
    try:
        result = crew_tool.create_plan(request.task_id, request.plan)
        
        if result["status"] == "success":
            logger.info(f"Created plan for task {request.task_id}")
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        logger.error(f"Error creating plan for task {request.task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/crew/apply")
def crew_apply(request: CrewApplyRequest, token: str = Depends(get_pod_token)):
    """Apply crew changes through Editor Tool."""
    try:
        result = crew_tool.apply_plan(request.task_id, request.run_id)
        
        if result["status"] == "success":
            logger.info(f"Applied plan for task {request.task_id}")
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        logger.error(f"Error applying plan for task {request.task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/crew/runs/{run_id}")
def get_crew_run(run_id: str, token: str = Depends(get_pod_token)):
    """Get crew run status/logs/summary."""
    try:
        result = crew_tool.get_run_status(run_id)
        
        if result["status"] == "success":
            return result
        else:
            raise HTTPException(status_code=404, detail=result["error"])
            
    except Exception as e:
        logger.error(f"Error getting run status for {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/crew/runs/{run_id}/artefacts")
def upload_artefacts(run_id: str, files: Dict[str, str], token: str = Depends(get_pod_token)):
    """Upload files into .cage/runs/<run_id>/*."""
    try:
        result = crew_tool.upload_artefacts(run_id, files)
        
        if result["status"] == "success":
            logger.info(f"Uploaded artefacts for run {run_id}")
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        logger.error(f"Error uploading artefacts for run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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


@app.post("/files/commit")
def commit_file_changes(
    message: str,
    task_id: Optional[str] = None,
    author: Optional[str] = None,
    token: str = Depends(get_pod_token)
):
    """Commit all file changes using Editor Tool integration."""
    try:
        result = editor_tool.commit_changes(message, task_id, author)
        
        if result["success"]:
            return {
                "status": "success",
                "message": "Changes committed successfully",
                "data": result
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error committing file changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Git endpoints
@app.get("/git/status")
def git_status(token: str = Depends(get_pod_token)):
    """Get Git repository status."""
    try:
        result = git_tool.get_status()
        if result.success:
            return {
                "status": "success",
                "data": result.data
            }
        else:
            raise HTTPException(status_code=400, detail=result.error)
    except Exception as e:
        logger.error(f"Error getting Git status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/git/branch")
def git_branches(token: str = Depends(get_pod_token)):
    """Get Git branches."""
    try:
        result = git_tool.get_branches()
        if result.success:
            return {
                "status": "success",
                "data": result.data
            }
        else:
            raise HTTPException(status_code=400, detail=result.error)
    except Exception as e:
        logger.error(f"Error getting Git branches: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/git/branch")
def create_branch(request: GitBranchRequest, token: str = Depends(get_pod_token)):
    """Create a new Git branch."""
    try:
        result = git_tool.create_branch(request.name)
        if result.success:
            return {
                "status": "success",
                "message": f"Created branch: {request.name}",
                "data": result.data
            }
        else:
            raise HTTPException(status_code=400, detail=result.error)
    except Exception as e:
        logger.error(f"Error creating branch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/git/commit")
def create_commit(request: GitCommitRequest, task_id: str = None, token: str = Depends(get_pod_token)):
    """Create a Git commit."""
    try:
        # First add all changes
        add_result = git_tool.add_files()
        if not add_result.success:
            raise HTTPException(status_code=400, detail=f"Failed to stage changes: {add_result.error}")
        
        # Create commit
        result = git_tool.commit(request.message, task_id=task_id)
        if result.success:
            # Update task provenance if task_id provided
            if task_id and result.data:
                task_manager.update_task_provenance(task_id, result.data)
            
            # Emit event (placeholder for now)
            logger.info(f"Emitted event: cage.git.commit.created for commit {result.data.get('sha', 'unknown')[:8]}")
            
            return {
                "status": "success",
                "message": "Commit created successfully",
                "data": result.data
            }
        else:
            raise HTTPException(status_code=400, detail=result.error)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating commit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/git/push")
def push_changes(request: GitPushRequest, token: str = Depends(get_pod_token)):
    """Push changes to remote repository."""
    try:
        result = git_tool.push(request.remote, request.branch)
        if result.success:
            return {
                "status": "success",
                "message": f"Pushed to {request.remote}/{request.branch or 'current branch'}",
                "data": result.data
            }
        else:
            raise HTTPException(status_code=400, detail=result.error)
    except Exception as e:
        logger.error(f"Error pushing to remote: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/git/pull")
def pull_changes(request: GitPullRequest, token: str = Depends(get_pod_token)):
    """Pull changes from remote repository."""
    try:
        result = git_tool.pull(request.remote, request.branch)
        if result.success:
            return {
                "status": "success",
                "message": f"Pulled from {request.remote}/{request.branch or 'current branch'}",
                "data": result.data
            }
        else:
            raise HTTPException(status_code=400, detail=result.error)
    except Exception as e:
        logger.error(f"Error pulling from remote: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/git/merge")
def merge_branches(request: GitMergeRequest, token: str = Depends(get_pod_token)):
    """Merge a branch into current branch."""
    try:
        result = git_tool.merge_branch(request.source)
        if result.success:
            return {
                "status": "success",
                "message": f"Merged branch: {request.source}",
                "data": result.data
            }
        else:
            raise HTTPException(status_code=400, detail=result.error)
    except Exception as e:
        logger.error(f"Error merging branch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/git/history")
def git_history(limit: int = 10, token: str = Depends(get_pod_token)):
    """Get Git commit history."""
    try:
        result = git_tool.get_commit_history(limit)
        if result.success:
            return {
                "status": "success",
                "data": result.data
            }
        else:
            raise HTTPException(status_code=400, detail=result.error)
    except Exception as e:
        logger.error(f"Error getting commit history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# RAG endpoints
@app.post("/rag/query")
async def rag_query(request: RAGQueryRequest, token: str = Depends(get_pod_token)):
    """Query RAG system."""
    if not rag_service:
        raise HTTPException(status_code=503, detail="RAG service not available")
    
    try:
        results = await rag_service.query(
            query_text=request.query,
            top_k=request.top_k,
            filters=request.filters
        )
        
        # Convert results to response format
        hits = []
        for result in results:
            hit = {
                "content": result.content,
                "metadata": {
                    "path": result.metadata.path,
                    "language": result.metadata.language,
                    "commit_sha": result.metadata.commit_sha,
                    "branch": result.metadata.branch,
                    "chunk_id": result.metadata.chunk_id
                },
                "score": result.score,
                "blob_sha": result.blob_sha
            }
            hits.append(hit)
        
        return {
            "status": "success",
            "hits": hits,
            "total": len(hits),
            "query": request.query
        }
        
    except Exception as e:
        logger.error(f"Error in RAG query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rag/reindex")
async def rag_reindex(request: RAGReindexRequest, token: str = Depends(get_pod_token)):
    """Reindex RAG system."""
    logger.info(f"RAG reindex request received: scope={request.scope}")
    
    if not rag_service:
        logger.error("RAG service not available")
        raise HTTPException(status_code=503, detail="RAG service not available")
    
    try:
        repo_path = get_repository_path()
        logger.info(f"Repository path: {repo_path}")
        logger.info(f"Repository path exists: {repo_path.exists()}")
        
        logger.info(f"Calling rag_service.reindex_repository with path={repo_path}, scope={request.scope}")
        logger.info(f"RAG service object: {rag_service}")
        logger.info(f"RAG service type: {type(rag_service)}")
        logger.info(f"RAG service has reindex_repository method: {hasattr(rag_service, 'reindex_repository')}")
        
        try:
            result = await rag_service.reindex_repository(repo_path, request.scope)
            logger.info(f"Reindex result: {result}")
        except Exception as e:
            logger.error(f"Exception in rag_service.reindex_repository: {e}")
            raise
        
        return {
            "status": "success",
            "scope": request.scope,
            "indexed_files": result["indexed_files"],
            "total_chunks": result["total_chunks"],
            "blob_shas": result["blob_shas"]
        }
        
    except Exception as e:
        logger.error(f"Error in RAG reindex: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rag/blobs/{sha}")
async def get_rag_blob(sha: str, token: str = Depends(get_pod_token)):
    """Check if blob metadata is present."""
    if not rag_service:
        raise HTTPException(status_code=503, detail="RAG service not available")
    
    try:
        result = await rag_service.check_blob_metadata(sha)
        return result
        
    except Exception as e:
        logger.error(f"Error checking blob metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Additional endpoints for Cage-native planner

@app.get("/files/sha")
def get_file_sha(path: str, token: str = Depends(get_pod_token)):
    """Get SHA hash of a file for validation."""
    try:
        repo_path = get_repository_path()
        file_path = repo_path / path
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {path}")
        
        # Calculate SHA256 hash
        import hashlib
        with open(file_path, 'rb') as f:
            content = f.read()
            sha = hashlib.sha256(content).hexdigest()
        
        return {
            "status": "success",
            "path": path,
            "sha": sha,
            "size": len(content)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file SHA for {path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/diff")
def get_diff(branch: str = None, token: str = Depends(get_pod_token)):
    """Get diff for a branch or current changes."""
    try:
        if branch:
            # Get diff between branch and main
            result = git_tool.get_diff(branch, "main")
        else:
            # Get diff for current working directory
            result = git_tool.get_status()
            if not result.success:
                raise HTTPException(status_code=400, detail=result.error)
            # For now, return status as diff - this could be enhanced
            return {
                "status": "success",
                "diff": result.data.get("status", "No changes"),
                "branch": result.data.get("current_branch", "unknown")
            }
        
        if result.success:
            return {
                "status": "success",
                "diff": result.data,
                "branch": branch
            }
        else:
            raise HTTPException(status_code=400, detail=result.error)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting diff: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/git/revert")
def git_revert(branch: str, to: str = "HEAD~1", token: str = Depends(get_pod_token)):
    """Revert commits on a branch for rollback."""
    try:
        result = git_tool.revert_commits(branch, to)
        
        if result.success:
            return {
                "status": "success",
                "message": f"Reverted {branch} to {to}",
                "data": result.data
            }
        else:
            raise HTTPException(status_code=400, detail=result.error)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reverting branch {branch}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/runner/exec")
def runner_exec(workdir: str, cmd: list[str], timeout_sec: int = 30, token: str = Depends(get_pod_token)):
    """Execute a command in a working directory."""
    try:
        import subprocess
        import os
        
        repo_path = get_repository_path()
        full_workdir = repo_path / workdir
        
        if not full_workdir.exists():
            raise HTTPException(status_code=404, detail=f"Working directory not found: {workdir}")
        
        # Execute command
        result = subprocess.run(
            cmd,
            cwd=str(full_workdir),
            capture_output=True,
            text=True,
            timeout=timeout_sec
        )
        
        return {
            "status": "success",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "workdir": workdir,
            "cmd": cmd
        }
        
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail=f"Command timed out after {timeout_sec} seconds")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing command {cmd} in {workdir}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/git/open_pr")
def open_pr(from_branch: str, to: str = "main", title: str = "", body: str = "", token: str = Depends(get_pod_token)):
    """Open a pull request (placeholder implementation)."""
    try:
        # This is a placeholder - in a real implementation, this would integrate with GitHub/GitLab API
        # For now, we'll just return a mock response
        pr_id = f"pr-{from_branch}-{int(datetime.datetime.now().timestamp())}"
        
        return {
            "status": "success",
            "pr_id": pr_id,
            "from_branch": from_branch,
            "to_branch": to,
            "title": title,
            "body": body,
            "state": "OPEN",
            "message": "Pull request created (mock implementation)"
        }
        
    except Exception as e:
        logger.error(f"Error opening PR from {from_branch} to {to}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tasks/update")
def update_task_comprehensive(request: dict, token: str = Depends(get_pod_token)):
    """Update task with comprehensive fields including changelog and lessons."""
    try:
        task_id = request.get("task_id")
        if not task_id:
            raise HTTPException(status_code=400, detail="task_id is required")
        
        # Extract update fields
        updates = {}
        for field in ["status", "progress_percent", "changelog_append", "lessons_append"]:
            if field in request:
                updates[field] = request[field]
        
        # Handle changelog and lessons appending
        if "changelog_append" in updates:
            task = task_manager.load_task(task_id)
            if task:
                current_changelog = task.changelog or []
                updates["changelog"] = current_changelog + [{"timestamp": datetime.datetime.now().isoformat(), "text": item} for item in updates["changelog_append"]]
                del updates["changelog_append"]
        
        if "lessons_append" in updates:
            task = task_manager.load_task(task_id)
            if task:
                current_lessons = task.lessons_learned or []
                updates["lessons_learned"] = current_lessons + updates["lessons_append"]
                del updates["lessons_append"]
        
        task = task_manager.update_task(task_id, updates)
        if task:
            logger.info(f"Updated task {task_id} with comprehensive fields")
            return {
                "status": "success",
                "task_id": task_id,
                "updated_fields": list(updates.keys())
            }
        else:
            raise HTTPException(status_code=404, detail="Task not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Individual Agent endpoints
@app.post("/crew/request")
def test_individual_agent(request: AgentRequest, token: str = Depends(get_pod_token)):
    """Test an individual agent with a specific request."""
    try:
        # Validate agent name
        valid_agents = ["planner", "implementer", "reviewer", "committer"]
        if request.agent not in valid_agents:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid agent name. Must be one of: {', '.join(valid_agents)}"
            )
        
        # Test the agent
        result = modular_crew_tool.test_agent(request.agent, request.request, request.task_id)
        
        if result["success"]:
            logger.info(f"Agent {request.agent} executed successfully")
            return {
                "status": "success",
                "agent": request.agent,
                "request": request.request,
                "output": result["output"],
                "execution_time": result.get("execution_time", "unknown")
            }
        else:
            logger.error(f"Agent {request.agent} execution failed: {result.get('error', 'Unknown error')}")
            raise HTTPException(
                status_code=400, 
                detail=f"Agent execution failed: {result.get('error', 'Unknown error')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing agent {request.agent}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/crew/agents")
def list_available_agents(token: str = Depends(get_pod_token)):
    """List all available agents and their information."""
    try:
        agents_info = modular_crew_tool.list_available_agents()
        
        return {
            "status": "success",
            "agents": agents_info,
            "count": len(agents_info)
        }
        
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/crew/agents/{agent_name}")
def get_agent_info(agent_name: str, token: str = Depends(get_pod_token)):
    """Get information about a specific agent."""
    try:
        agent_info = modular_crew_tool.get_agent_info(agent_name)
        
        if agent_info:
            return {
                "status": "success",
                "agent": agent_info
            }
        else:
            raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent info for {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Webhooks endpoint
@app.post("/webhooks")
def register_webhook(token: str = Depends(get_pod_token)):
    """Register webhook."""
    # TODO: Implement webhook registration
    return {"status": "success", "message": "Webhooks not yet implemented"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)