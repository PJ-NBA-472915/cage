import datetime
import json
import logging
import os
import sys
import subprocess
from pathlib import Path
from fastapi import FastAPI, HTTPException
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

class BranchCreateRequest(BaseModel):
    name: str
    from_branch: str = "main"
    checkout: bool = True

class CommitRequest(BaseModel):
    message: str
    files: list[str] | None = None
    all: bool = False
    signoff: bool = False
    no_verify: bool = False

class PushRequest(BaseModel):
    remote: str = "origin"
    branch: str | None = None
    force: bool = False
    tags: bool = False

class PullRequest(BaseModel):
    remote: str = "origin"
    branch: str | None = None
    rebase: bool = False

class MergeRequest(BaseModel):
    source: str
    target: str | None = None
    no_ff: bool = False
    message: str | None = None

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

def get_repository_path():
    """Get the repository path from environment variable."""
    repo_path = os.environ.get("CAGE_REPOSITORY_PATH")
    if not repo_path:
        raise HTTPException(status_code=500, detail="Repository path not set. Start the service with 'cage serve <path>'")
    return Path(repo_path)

def run_git_command(args: list[str], cwd: Path | None = None) -> dict:
    """Run a git command and return the result."""
    if cwd is None:
        cwd = get_repository_path()
    
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return {
            "success": True,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "stdout": e.stdout.strip(),
            "stderr": e.stderr.strip(),
            "returncode": e.returncode
        }

@app.get("/health")
def health():
    """Perform a health check."""
    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        repo_path = get_repository_path()
        
        # Get current branch and commit
        branch_result = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
        commit_result = run_git_command(["rev-parse", "HEAD"])
        status_result = run_git_command(["status", "--porcelain"])
        
        response = {
            "status": "success",
            "date": current_date,
            "repository": {
                "path": str(repo_path),
                "branch": branch_result["stdout"] if branch_result["success"] else "unknown",
                "commit": commit_result["stdout"] if commit_result["success"] else "unknown",
                "status": "clean" if status_result["success"] and not status_result["stdout"] else "modified"
            }
        }
    except Exception as e:
        response = {
            "status": "error",
            "date": current_date,
            "error": str(e)
        }
    
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

# Repository-specific endpoints

@app.get("/repository/info")
def repository_info():
    """Get information about the current repository."""
    try:
        repo_path = get_repository_path()
        
        # Get basic info
        branch_result = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
        commit_result = run_git_command(["rev-parse", "HEAD"])
        status_result = run_git_command(["status", "--porcelain"])
        remotes_result = run_git_command(["remote", "-v"])
        
        # Parse remotes
        remotes = []
        if remotes_result["success"]:
            for line in remotes_result["stdout"].split('\n'):
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        remotes.append({
                            "name": parts[0],
                            "url": parts[1].split(' ')[0]
                        })
        
        return {
            "path": str(repo_path),
            "branch": branch_result["stdout"] if branch_result["success"] else "unknown",
            "commit": commit_result["stdout"] if commit_result["success"] else "unknown",
            "status": "clean" if status_result["success"] and not status_result["stdout"] else "modified",
            "remotes": remotes,
            "last_modified": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/repository/status")
def repository_status():
    """Get detailed Git status information."""
    try:
        # Get current branch
        branch_result = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
        commit_result = run_git_command(["rev-parse", "HEAD"])
        status_result = run_git_command(["status", "--porcelain"])
        
        # Parse status
        staged_files = []
        unstaged_files = []
        untracked_files = []
        
        if status_result["success"]:
            for line in status_result["stdout"].split('\n'):
                if line.strip():
                    status = line[:2]
                    filename = line[3:]
                    if status[0] != ' ':
                        staged_files.append(filename)
                    if status[1] != ' ':
                        if status[1] == '?':
                            untracked_files.append(filename)
                        else:
                            unstaged_files.append(filename)
        
        return {
            "branch": branch_result["stdout"] if branch_result["success"] else "unknown",
            "commit": commit_result["stdout"] if commit_result["success"] else "unknown",
            "status": "clean" if not staged_files and not unstaged_files and not untracked_files else "modified",
            "staged_files": staged_files,
            "unstaged_files": unstaged_files,
            "untracked_files": untracked_files,
            "ahead": 0,  # TODO: implement ahead/behind calculation
            "behind": 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/branches")
def list_branches(remote: bool = True):
    """List all branches (local and remote)."""
    try:
        local_result = run_git_command(["branch", "--format=%(refname:short) %(objectname)"])
        current_branch_result = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
        
        local_branches = []
        if local_result["success"]:
            for line in local_result["stdout"].split('\n'):
                if line.strip():
                    parts = line.split(' ', 1)
                    if len(parts) >= 2:
                        local_branches.append({
                            "name": parts[0],
                            "commit": parts[1],
                            "is_current": parts[0] == current_branch_result["stdout"]
                        })
        
        remote_branches = []
        if remote:
            remote_result = run_git_command(["branch", "-r", "--format=%(refname:short) %(objectname)"])
            if remote_result["success"]:
                for line in remote_result["stdout"].split('\n'):
                    if line.strip() and not line.startswith('origin/HEAD'):
                        parts = line.split(' ', 1)
                        if len(parts) >= 2:
                            remote_branches.append({
                                "name": parts[0],
                                "commit": parts[1],
                                "tracking": parts[0].replace('origin/', '') if parts[0].startswith('origin/') else None
                            })
        
        return {
            "local": local_branches,
            "remote": remote_branches
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/branches")
def create_branch(request: BranchCreateRequest):
    """Create a new branch."""
    try:
        # Create branch
        result = run_git_command(["checkout", "-b", request.name, request.from_branch])
        if not result["success"]:
            raise HTTPException(status_code=400, detail=f"Failed to create branch: {result['stderr']}")
        
        # Get commit hash
        commit_result = run_git_command(["rev-parse", "HEAD"])
        
        return {
            "status": "success",
            "branch": request.name,
            "commit": commit_result["stdout"] if commit_result["success"] else "unknown",
            "message": "Branch created successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/branches/{branch_name}")
def delete_branch(branch_name: str, force: bool = False):
    """Delete a branch."""
    try:
        args = ["branch", "-d"]
        if force:
            args = ["branch", "-D"]
        
        result = run_git_command(args + [branch_name])
        if not result["success"]:
            raise HTTPException(status_code=400, detail=f"Failed to delete branch: {result['stderr']}")
        
        return {
            "status": "success",
            "message": "Branch deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/commits")
def create_commit(request: CommitRequest):
    """Create a new commit."""
    try:
        # Stage files
        if request.files:
            for file in request.files:
                run_git_command(["add", file])
        elif request.all:
            run_git_command(["add", "-A"])
        
        # Create commit
        commit_args = ["commit", "-m", request.message]
        if request.signoff:
            commit_args.append("--signoff")
        if request.no_verify:
            commit_args.append("--no-verify")
        
        result = run_git_command(commit_args)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=f"Failed to create commit: {result['stderr']}")
        
        # Get commit hash
        commit_hash_result = run_git_command(["rev-parse", "HEAD"])
        
        return {
            "status": "success",
            "commit": commit_hash_result["stdout"] if commit_hash_result["success"] else "unknown",
            "message": "Commit created successfully",
            "files_changed": len(request.files) if request.files else 0
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/push")
def push_changes(request: PushRequest):
    """Push changes to remote."""
    try:
        # Get current branch if not specified
        branch = request.branch
        if not branch:
            branch_result = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
            if not branch_result["success"]:
                raise HTTPException(status_code=400, detail="Could not determine current branch")
            branch = branch_result["stdout"]
        
        # Push
        push_args = ["push", request.remote, branch]
        if request.force:
            push_args.append("--force")
        if request.tags:
            push_args.append("--tags")
        
        result = run_git_command(push_args)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=f"Failed to push: {result['stderr']}")
        
        return {
            "status": "success",
            "message": "Pushed successfully",
            "remote": request.remote,
            "branch": branch
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/pull")
def pull_changes(request: PullRequest):
    """Pull changes from remote."""
    try:
        # Get current branch if not specified
        branch = request.branch
        if not branch:
            branch_result = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
            if not branch_result["success"]:
                raise HTTPException(status_code=400, detail="Could not determine current branch")
            branch = branch_result["stdout"]
        
        # Pull
        pull_args = ["pull", request.remote, branch]
        if request.rebase:
            pull_args.append("--rebase")
        
        result = run_git_command(pull_args)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=f"Failed to pull: {result['stderr']}")
        
        return {
            "status": "success",
            "message": "Pulled successfully",
            "remote": request.remote,
            "branch": branch,
            "commits_ahead": 0,  # TODO: implement ahead/behind calculation
            "commits_behind": 0
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/merge")
def merge_branches(request: MergeRequest):
    """Merge branches."""
    try:
        # Get current branch if target not specified
        target = request.target
        if not target:
            target_result = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
            if not target_result["success"]:
                raise HTTPException(status_code=400, detail="Could not determine current branch")
            target = target_result["stdout"]
        
        # Merge
        merge_args = ["merge", request.source]
        if request.no_ff:
            merge_args.append("--no-ff")
        if request.message:
            merge_args.extend(["-m", request.message])
        
        result = run_git_command(merge_args)
        if not result["success"]:
            raise HTTPException(status_code=409, detail=f"Merge failed: {result['stderr']}")
        
        # Get merge commit hash
        commit_result = run_git_command(["rev-parse", "HEAD"])
        
        return {
            "status": "success",
            "message": "Merge completed successfully",
            "merge_commit": commit_result["stdout"] if commit_result["success"] else "unknown",
            "conflicts": []
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
