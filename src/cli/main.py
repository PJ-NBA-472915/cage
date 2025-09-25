import typer
import subprocess
import sys
import os
import uvicorn
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.cage.models import TaskManager, TaskFile
from src.cage.git_tool import GitTool
from src.cli.crew_cli import app as crew_app

app = typer.Typer()

# Initialize task manager and git tool
task_manager = TaskManager(Path("tasks"))
git_tool = GitTool(Path("."))

def check_podman():
    """Checks if podman is running and connected."""
    try:
        subprocess.run(["podman", "system", "connection", "list"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Cannot connect to Podman. Please verify your connection to the Linux system using `podman system connection list`, or try `podman machine init` and `podman machine start` to manage a new Linux VM", file=sys.stderr)
        sys.exit(1)

@app.command()
def start():
    """Builds and starts the API service container."""
    check_podman()
    try:
        # Build the container
        subprocess.run(["podman", "build", "-t", "cage-pod", "-f", "Containerfile", "."], check=True)
        # Run the container
        subprocess.run(["podman", "run", "-d", "--name", "cage-pod", "-p", "8000:8000", "cage-pod"], check=True)
        print("Container cage-pod started successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error starting container: {e}", file=sys.stderr)
        sys.exit(1)

@app.command()
def stop():
    """Stops and removes the API service container."""
    try:
        subprocess.run(["podman", "stop", "cage-pod"], check=True)
        subprocess.run(["podman", "rm", "cage-pod"], check=True)
        print("Container cage-pod stopped and removed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error stopping container: {e}", file=sys.stderr)
        sys.exit(1)

@app.command()
def status():
    """Checks the status of the API service container."""
    try:
        subprocess.run(["podman", "ps", "-f", "name=cage-pod"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error checking container status: {e}", file=sys.stderr)
        sys.exit(1)

@app.command()
def serve(
    repository_path: str = typer.Argument(..., help="Path to the repository directory"),
    port: int = typer.Option(8000, help="Port to run the service on"),
    host: str = typer.Option("0.0.0.0", help="Host to bind the service to")
):
    """Start the Cage service for a specific repository directory."""
    # Validate repository path
    repo_path = Path(repository_path).resolve()
    if not repo_path.exists():
        print(f"Error: Repository path does not exist: {repository_path}", file=sys.stderr)
        sys.exit(1)
    
    if not (repo_path / ".git").is_dir():
        print(f"Error: Not a Git repository: {repository_path}", file=sys.stderr)
        sys.exit(1)
    
    # Set environment variables for the new Cage specification
    os.environ["REPO_PATH"] = str(repo_path)
    os.environ["POD_ID"] = os.environ.get("POD_ID", "dev-pod")
    os.environ["POD_TOKEN"] = os.environ.get("POD_TOKEN", "dev-token")
    
    print(f"Starting Cage service for repository: {repo_path}")
    print(f"Service will be available at: http://{host}:{port}")
    print("Press Ctrl+C to stop the service")
    
    try:
        # Import and run the API service
        from api.main import app
        uvicorn.run(app, host=host, port=port)
    except KeyboardInterrupt:
        print("\nService stopped.")
    except Exception as e:
        print(f"Error starting service: {e}", file=sys.stderr)
        sys.exit(1)

# Task management commands
@app.command()
def task_create(
    task_id: str = typer.Argument(..., help="Task ID (format: YYYY-MM-DD-task-slug)"),
    title: str = typer.Argument(..., help="Task title"),
    owner: str = typer.Option("system", help="Task owner"),
    summary: str = typer.Option("", help="Task summary"),
    tags: str = typer.Option("", help="Comma-separated tags")
):
    """Create a new task."""
    try:
        # Parse tags
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
        
        task_data = {
            "id": task_id,
            "title": title,
            "owner": owner,
            "status": "planned",
            "progress_percent": 0,
            "summary": summary,
            "tags": tag_list,
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
            print(f"✅ Created task: {task_id}")
            print(f"   Title: {title}")
            print(f"   Owner: {owner}")
            print(f"   Status: {task.status}")
        else:
            print(f"❌ Failed to create task: {task_id}", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error creating task: {e}", file=sys.stderr)
        sys.exit(1)

@app.command()
def task_list(
    status: Optional[str] = typer.Option(None, help="Filter by status"),
    limit: int = typer.Option(10, help="Maximum number of tasks to show")
):
    """List tasks."""
    try:
        tasks = task_manager.list_tasks()
        
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        
        tasks = tasks[:limit]
        
        if not tasks:
            print("No tasks found.")
            return
        
        print(f"\n📋 Tasks ({len(tasks)}):")
        print("-" * 80)
        
        for task in tasks:
            status_emoji = {
                "planned": "📋",
                "in-progress": "🔄", 
                "blocked": "🚫",
                "review": "👀",
                "done": "✅",
                "abandoned": "❌"
            }.get(task["status"], "❓")
            
            print(f"{status_emoji} {task['id']:<25} | {task['title']:<30} | {task['progress_percent']:>3}% | {task['status']}")
        
        print("-" * 80)
        
    except Exception as e:
        print(f"❌ Error listing tasks: {e}", file=sys.stderr)
        sys.exit(1)

@app.command()
def task_show(
    task_id: str = typer.Argument(..., help="Task ID to show")
):
    """Show detailed task information."""
    try:
        task = task_manager.load_task(task_id)
        if not task:
            print(f"❌ Task not found: {task_id}", file=sys.stderr)
            sys.exit(1)
        
        print(f"\n📋 Task: {task.id}")
        print("=" * 60)
        print(f"Title: {task.title}")
        print(f"Owner: {task.owner}")
        print(f"Status: {task.status}")
        print(f"Progress: {task.progress_percent}%")
        print(f"Created: {task.created_at}")
        print(f"Updated: {task.updated_at}")
        
        if task.tags:
            print(f"Tags: {', '.join(task.tags)}")
        
        if task.summary:
            print(f"\nSummary:")
            print(f"  {task.summary}")
        
        if task.todo:
            print(f"\nTodo Items ({len(task.todo)}):")
            for i, item in enumerate(task.todo, 1):
                status_emoji = {
                    "not-started": "⭕",
                    "done": "✅",
                    "blocked": "🚫",
                    "failed": "❌"
                }.get(item.status, "❓")
                print(f"  {i}. {status_emoji} {item.text} ({item.status})")
        
        if task.success_criteria:
            print(f"\nSuccess Criteria:")
            for i, criteria in enumerate(task.success_criteria, 1):
                check = "✅" if criteria.checked else "⭕"
                print(f"  {i}. {check} {criteria.text}")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error showing task: {e}", file=sys.stderr)
        sys.exit(1)

@app.command()
def task_update(
    task_id: str = typer.Argument(..., help="Task ID to update"),
    status: Optional[str] = typer.Option(None, help="Update status"),
    progress: Optional[int] = typer.Option(None, help="Update progress percentage"),
    title: Optional[str] = typer.Option(None, help="Update title"),
    summary: Optional[str] = typer.Option(None, help="Update summary")
):
    """Update a task."""
    try:
        updates = {}
        if status is not None:
            updates["status"] = status
        if progress is not None:
            updates["progress_percent"] = progress
        if title is not None:
            updates["title"] = title
        if summary is not None:
            updates["summary"] = summary
        
        if not updates:
            print("❌ No fields to update. Use --help to see available options.", file=sys.stderr)
            sys.exit(1)
        
        task = task_manager.update_task(task_id, updates)
        if task:
            print(f"✅ Updated task: {task_id}")
            for field, value in updates.items():
                print(f"   {field}: {value}")
        else:
            print(f"❌ Task not found: {task_id}", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error updating task: {e}", file=sys.stderr)
        sys.exit(1)

@app.command()
def tracker_rebuild():
    """Rebuild the task tracker status file."""
    try:
        status_data = task_manager.rebuild_status()
        active_count = len(status_data.get("active_tasks", []))
        completed_count = len(status_data.get("recently_completed", []))
        
        print(f"✅ Rebuilt task tracker")
        print(f"   Active tasks: {active_count}")
        print(f"   Recently completed: {completed_count}")
        
    except Exception as e:
        print(f"❌ Error rebuilding tracker: {e}", file=sys.stderr)
        sys.exit(1)

# Git commands
@app.command()
def git_status():
    """Get Git repository status."""
    try:
        result = git_tool.get_status()
        
        if result.success:
            data = result.data
            print(f"Current branch: {data.get('current_branch', 'unknown')}")
            print(f"Commit count: {data.get('commit_count', '0')}")
            print(f"Repository clean: {data.get('is_clean', False)}")
            
            if data.get('staged_files'):
                print(f"\nStaged files ({len(data['staged_files'])}):")
                for file in data['staged_files']:
                    print(f"  + {file}")
            
            if data.get('unstaged_files'):
                print(f"\nUnstaged files ({len(data['unstaged_files'])}):")
                for file in data['unstaged_files']:
                    print(f"  M {file}")
            
            if data.get('untracked_files'):
                print(f"\nUntracked files ({len(data['untracked_files'])}):")
                for file in data['untracked_files']:
                    print(f"  ? {file}")
        else:
            print(f"❌ Error: {result.error}", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error getting Git status: {e}", file=sys.stderr)
        sys.exit(1)

@app.command()
def git_branches():
    """List Git branches."""
    try:
        result = git_tool.get_branches()
        
        if result.success:
            branches = result.data.get('branches', [])
            if branches:
                print("Branches:")
                for branch in branches:
                    print(f"  {branch}")
            else:
                print("No branches found")
        else:
            print(f"❌ Error: {result.error}", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error listing branches: {e}", file=sys.stderr)
        sys.exit(1)

@app.command()
def git_create_branch(
    name: str = typer.Argument(..., help="Branch name")
):
    """Create a new Git branch."""
    try:
        result = git_tool.create_branch(name)
        
        if result.success:
            print(f"✅ Created and switched to branch: {name}")
        else:
            print(f"❌ Error: {result.error}", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error creating branch: {e}", file=sys.stderr)
        sys.exit(1)

@app.command()
def git_commit(
    message: str = typer.Argument(..., help="Commit message"),
    author: Optional[str] = typer.Option(None, help="Commit author"),
    task_id: Optional[str] = typer.Option(None, help="Task ID for provenance tracking")
):
    """Create a Git commit."""
    try:
        # Add files first
        add_result = git_tool.add_files()
        if not add_result.success:
            print(f"❌ Error staging files: {add_result.error}", file=sys.stderr)
            sys.exit(1)
        
        # Create commit
        result = git_tool.commit(message, author, task_id)
        
        if result.success:
            data = result.data
            print(f"✅ Created commit: {data.get('sha', 'unknown')[:8]}")
            print(f"   Message: {data.get('title', '')}")
            
            # Update task provenance if task_id provided
            if task_id:
                task_manager.update_task_provenance(task_id, data)
                print(f"   Updated task provenance: {task_id}")
        else:
            print(f"❌ Error: {result.error}", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error creating commit: {e}", file=sys.stderr)
        sys.exit(1)

@app.command()
def git_push(
    remote: str = typer.Option("origin", help="Remote name"),
    branch: Optional[str] = typer.Option(None, help="Branch name")
):
    """Push changes to remote repository."""
    try:
        result = git_tool.push(remote, branch)
        
        if result.success:
            print(f"✅ Pushed to {remote}/{branch or 'current branch'}")
        else:
            print(f"❌ Error: {result.error}", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error pushing: {e}", file=sys.stderr)
        sys.exit(1)

@app.command()
def git_pull(
    remote: str = typer.Option("origin", help="Remote name"),
    branch: Optional[str] = typer.Option(None, help="Branch name")
):
    """Pull changes from remote repository."""
    try:
        result = git_tool.pull(remote, branch)
        
        if result.success:
            print(f"✅ Pulled from {remote}/{branch or 'current branch'}")
        else:
            print(f"❌ Error: {result.error}", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error pulling: {e}", file=sys.stderr)
        sys.exit(1)

@app.command()
def git_merge(
    branch: str = typer.Argument(..., help="Branch to merge")
):
    """Merge a branch into current branch."""
    try:
        result = git_tool.merge_branch(branch)
        
        if result.success:
            print(f"✅ Merged branch: {branch}")
        else:
            print(f"❌ Error: {result.error}", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error merging: {e}", file=sys.stderr)
        sys.exit(1)

@app.command()
def git_history(
    limit: int = typer.Option(10, help="Number of commits to show")
):
    """Show Git commit history."""
    try:
        result = git_tool.get_commit_history(limit)
        
        if result.success:
            commits = result.data.get('commits', [])
            if commits:
                print(f"Commit history (last {len(commits)} commits):")
                for commit in commits:
                    print(f"  {commit['sha'][:8]} - {commit['title']} ({commit['author']})")
            else:
                print("No commits found")
        else:
            print(f"❌ Error: {result.error}", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error getting history: {e}", file=sys.stderr)
        sys.exit(1)

# Add crew commands as a subcommand
app.add_typer(crew_app, name="crew")

if __name__ == "__main__":
    app()