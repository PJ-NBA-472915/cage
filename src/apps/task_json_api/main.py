"""
Task JSON API for Grafana SimpleJSON datasource.

This service provides a read-only JSON API to query task files
for visualization in Grafana dashboards.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Task JSON API", version="1.0.0")

# Enable CORS for Grafana
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get tasks directory from environment or default to ./tasks
TASKS_DIR = Path(os.getenv("TASKS_DIR", "/work/tasks"))


class SearchTarget(BaseModel):
    """Grafana search target."""

    target: str
    type: str = "table"


class QueryTarget(BaseModel):
    """Grafana query target."""

    target: str
    type: str = "table"
    refId: str


class QueryRequest(BaseModel):
    """Grafana query request."""

    range: dict[str, Any]
    targets: list[QueryTarget]


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "service": "Task JSON API",
        "version": "1.0.0",
        "description": "Grafana SimpleJSON datasource for task files",
        "tasks_dir": str(TASKS_DIR),
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    tasks_exist = TASKS_DIR.exists() and TASKS_DIR.is_dir()
    task_count = (
        len(list(TASKS_DIR.glob("*.json"))) if tasks_exist else 0
    )

    return {
        "status": "healthy" if tasks_exist else "degraded",
        "tasks_dir": str(TASKS_DIR),
        "tasks_dir_exists": tasks_exist,
        "task_count": task_count,
    }


@app.post("/search")
def search(body: dict[str, Any] = None):
    """
    Grafana search endpoint.
    Returns available metrics/targets for querying.
    """
    if not TASKS_DIR.exists():
        return []

    # Return list of available query types
    return [
        "all_tasks",
        "by_status",
        "by_owner",
        "by_tag",
        "progress_summary",
        "timeline",
    ]


@app.post("/query")
def query(request: QueryRequest):
    """
    Grafana query endpoint.
    Returns data based on the selected target.
    """
    if not TASKS_DIR.exists():
        return []

    results = []

    for target in request.targets:
        target_name = target.target

        if target_name == "all_tasks":
            results.append(get_all_tasks())
        elif target_name == "by_status":
            results.append(get_tasks_by_status())
        elif target_name == "by_owner":
            results.append(get_tasks_by_owner())
        elif target_name == "by_tag":
            results.append(get_tasks_by_tag())
        elif target_name == "progress_summary":
            results.append(get_progress_summary())
        elif target_name == "timeline":
            results.append(get_timeline())
        else:
            # Try to interpret as a specific query
            results.append(get_all_tasks())

    return results


def load_task_files() -> list[dict[str, Any]]:
    """Load all task JSON files from the tasks directory."""
    tasks = []

    if not TASKS_DIR.exists():
        return tasks

    for task_file in TASKS_DIR.glob("*.json"):
        try:
            with open(task_file, "r") as f:
                task_data = json.load(f)
                task_data["_filename"] = task_file.name
                tasks.append(task_data)
        except Exception as e:
            print(f"Error loading {task_file}: {e}")
            continue

    return tasks


def get_all_tasks():
    """Return all tasks in table format."""
    tasks = load_task_files()

    columns = [
        {"text": "ID", "type": "string"},
        {"text": "Title", "type": "string"},
        {"text": "Status", "type": "string"},
        {"text": "Owner", "type": "string"},
        {"text": "Progress", "type": "number"},
        {"text": "Created", "type": "time"},
        {"text": "Updated", "type": "time"},
        {"text": "Tags", "type": "string"},
    ]

    rows = []
    for task in tasks:
        rows.append(
            [
                task.get("id", ""),
                task.get("title", ""),
                task.get("status", ""),
                task.get("owner", ""),
                task.get("progress_percent", 0),
                parse_timestamp(task.get("created_at", "")),
                parse_timestamp(task.get("updated_at", "")),
                ", ".join(task.get("tags", [])),
            ]
        )

    return {"type": "table", "columns": columns, "rows": rows}


def get_tasks_by_status():
    """Group tasks by status."""
    tasks = load_task_files()
    status_counts = {}

    for task in tasks:
        status = task.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    columns = [
        {"text": "Status", "type": "string"},
        {"text": "Count", "type": "number"},
    ]

    rows = [[status, count] for status, count in status_counts.items()]

    return {"type": "table", "columns": columns, "rows": rows}


def get_tasks_by_owner():
    """Group tasks by owner."""
    tasks = load_task_files()
    owner_counts = {}

    for task in tasks:
        owner = task.get("owner", "unknown")
        owner_counts[owner] = owner_counts.get(owner, 0) + 1

    columns = [
        {"text": "Owner", "type": "string"},
        {"text": "Count", "type": "number"},
    ]

    rows = [[owner, count] for owner, count in owner_counts.items()]

    return {"type": "table", "columns": columns, "rows": rows}


def get_tasks_by_tag():
    """Group tasks by tag."""
    tasks = load_task_files()
    tag_counts = {}

    for task in tasks:
        for tag in task.get("tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    columns = [
        {"text": "Tag", "type": "string"},
        {"text": "Count", "type": "number"},
    ]

    rows = [[tag, count] for tag, count in sorted(tag_counts.items())]

    return {"type": "table", "columns": columns, "rows": rows}


def get_progress_summary():
    """Calculate progress statistics."""
    tasks = load_task_files()

    total_tasks = len(tasks)
    total_progress = sum(task.get("progress_percent", 0) for task in tasks)
    avg_progress = total_progress / total_tasks if total_tasks > 0 else 0

    status_progress = {}
    for task in tasks:
        status = task.get("status", "unknown")
        if status not in status_progress:
            status_progress[status] = []
        status_progress[status].append(task.get("progress_percent", 0))

    columns = [
        {"text": "Status", "type": "string"},
        {"text": "Task Count", "type": "number"},
        {"text": "Avg Progress", "type": "number"},
    ]

    rows = []
    for status, progress_list in status_progress.items():
        avg = sum(progress_list) / len(progress_list) if progress_list else 0
        rows.append([status, len(progress_list), round(avg, 2)])

    return {"type": "table", "columns": columns, "rows": rows}


def get_timeline():
    """Return task timeline data."""
    tasks = load_task_files()

    columns = [
        {"text": "Time", "type": "time"},
        {"text": "Task ID", "type": "string"},
        {"text": "Title", "type": "string"},
        {"text": "Event", "type": "string"},
    ]

    rows = []

    for task in tasks:
        task_id = task.get("id", "")
        title = task.get("title", "")

        # Add created event
        created_at = parse_timestamp(task.get("created_at", ""))
        if created_at:
            rows.append([created_at, task_id, title, "created"])

        # Add updated event
        updated_at = parse_timestamp(task.get("updated_at", ""))
        if updated_at and updated_at != created_at:
            rows.append([updated_at, task_id, title, "updated"])

    # Sort by timestamp
    rows.sort(key=lambda x: x[0] if x[0] else 0)

    return {"type": "table", "columns": columns, "rows": rows}


def parse_timestamp(timestamp_str: str) -> int | None:
    """Parse various timestamp formats to milliseconds since epoch."""
    if not timestamp_str:
        return None

    try:
        # Try ISO format first
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)
    except ValueError:
        pass

    try:
        # Try common format: "2025-09-07 09:05"
        dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M")
        return int(dt.timestamp() * 1000)
    except ValueError:
        pass

    try:
        # Try date only: "2025-09-07"
        dt = datetime.strptime(timestamp_str, "%Y-%m-%d")
        return int(dt.timestamp() * 1000)
    except ValueError:
        pass

    return None


@app.get("/tasks")
def list_tasks(
    status: str | None = Query(None, description="Filter by status"),
    owner: str | None = Query(None, description="Filter by owner"),
    tag: str | None = Query(None, description="Filter by tag"),
):
    """List all tasks with optional filters."""
    tasks = load_task_files()

    # Apply filters
    if status:
        tasks = [t for t in tasks if t.get("status") == status]

    if owner:
        tasks = [t for t in tasks if t.get("owner") == owner]

    if tag:
        tasks = [t for t in tasks if tag in t.get("tags", [])]

    return {"count": len(tasks), "tasks": tasks}


@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    """Get a specific task by ID."""
    task_file = TASKS_DIR / f"{task_id}.json"

    if not task_file.exists():
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        with open(task_file, "r") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error reading task: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8015)
