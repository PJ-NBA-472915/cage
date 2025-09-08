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

from src.cage.task_models import TaskManager, TaskFile

app = typer.Typer()

# Initialize task manager
task_manager = TaskManager(Path("tasks"))

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

if __name__ == "__main__":
    app()