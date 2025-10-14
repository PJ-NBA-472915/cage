"""
CrewAI Router

Main router for all crew endpoints.
"""

import asyncio
import logging
import os
from uuid import UUID

from fastapi import APIRouter, Request

from src.cage.utils.jsonl_logger import log_with_context
from src.crew_service.middleware_request_id import get_current_request_id
from src.crew_service.run_engine import RunEngine
from src.models.crewai import (
    Agent,
    AgentCreate,
    AgentInvoke,
    AgentListResponse,
    Crew,
    CrewCreate,
    CrewListResponse,
    CrewRunRequest,
    Run,
    RunListResponse,
    RunStatusResponse,
)

logger = logging.getLogger(__name__)

# In-memory storage (simplified for now)
agents_db = {}
crews_db = {}
runs_db = {}

# Initialize run engine with runs_db
run_engine = RunEngine(runs_db=runs_db)

# Create router without prefix (standalone service)
router = APIRouter(tags=["crew"])


@router.get("/health")
async def health_check(request: Request):
    """Health check endpoint."""
    request_id = get_current_request_id()

    log_with_context(
        logger=logger,
        level=logging.INFO,
        message="Health check requested",
        request_id=request_id,
        route="/crew/health",
    )

    return {"status": "ok"}


@router.get("/about")
async def about(request: Request):
    """About endpoint with pod information."""
    request_id = get_current_request_id()

    log_with_context(
        logger=logger,
        level=logging.INFO,
        message="About requested",
        request_id=request_id,
        route="/crew/about",
    )

    # Get pod information
    import uuid

    pod_id = os.getenv("POD_ID", str(uuid.uuid4()))
    version = "1.0.0"
    labels = os.getenv("POD_LABELS", "").split(",") if os.getenv("POD_LABELS") else []

    return {"pod_id": pod_id, "version": version, "labels": labels}


# Agent endpoints
@router.post("/agents", response_model=Agent)
async def create_agent(request: Request, agent_data: AgentCreate):
    """Create a new agent."""
    request_id = get_current_request_id()

    log_with_context(
        logger=logger,
        level=logging.INFO,
        message="Creating agent",
        request_id=request_id,
        route="/crew/agents",
    )

    agent = Agent(**agent_data.dict())
    agents_db[agent.id] = agent

    return agent


@router.get("/agents", response_model=AgentListResponse)
async def list_agents(
    request: Request,
    role: str = None,
    q: str = None,
    limit: int = 50,
    cursor: str = None,
):
    """List agents with filtering and pagination."""
    request_id = get_current_request_id()

    log_with_context(
        logger=logger,
        level=logging.INFO,
        message="Listing agents",
        request_id=request_id,
        route="/crew/agents",
    )

    items = list(agents_db.values())

    if role:
        items = [a for a in items if a.role == role]
    if q:
        query = q.lower()
        items = [a for a in items if query in a.name.lower()]

    # Simple pagination
    start_idx = 0
    if cursor:
        try:
            start_idx = int(cursor)
        except:
            start_idx = 0

    paginated_items = items[start_idx : start_idx + limit]
    next_cursor = str(start_idx + limit) if len(items) > start_idx + limit else None

    return AgentListResponse(items=paginated_items, next_cursor=next_cursor)


@router.get("/agents/{agent_id}", response_model=Agent)
async def get_agent(request: Request, agent_id: UUID):
    """Get a specific agent by ID."""
    request_id = get_current_request_id()

    log_with_context(
        logger=logger,
        level=logging.INFO,
        message=f"Getting agent {agent_id}",
        request_id=request_id,
        route=f"/crew/agents/{agent_id}",
    )

    agent = agents_db.get(agent_id)
    if not agent:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Agent not found")

    return agent


@router.post("/agents/{agent_id}/invoke", response_model=Run)
async def invoke_agent(request: Request, agent_id: UUID, invoke_data: AgentInvoke):
    """Invoke a single agent with a task."""
    request_id = get_current_request_id()

    log_with_context(
        logger=logger,
        level=logging.INFO,
        message=f"Invoking agent {agent_id}",
        request_id=request_id,
        route=f"/crew/agents/{agent_id}/invoke",
    )

    agent = agents_db.get(agent_id)
    if not agent:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Agent not found")

    # Create a run
    run = Run(
        kind="agent",
        agent_id=agent_id,
        task_ref=invoke_data.task.dict(),
        status="queued",
    )
    runs_db[run.id] = run

    # Execute agent run in background with agent role
    asyncio.create_task(
        run_engine.execute_agent_run(run, agent_id, agent.role, invoke_data.task)
    )

    return run


# Crew endpoints
@router.post("/crews", response_model=Crew)
async def create_crew(request: Request, crew_data: CrewCreate):
    """Create a new crew."""
    request_id = get_current_request_id()

    log_with_context(
        logger=logger,
        level=logging.INFO,
        message="Creating crew",
        request_id=request_id,
        route="/crew/crews",
    )

    crew = Crew(**crew_data.dict())
    crews_db[crew.id] = crew

    return crew


@router.get("/crews", response_model=CrewListResponse)
async def list_crews(
    request: Request,
    label: str = None,
    q: str = None,
    limit: int = 50,
    cursor: str = None,
):
    """List crews with filtering and pagination."""
    request_id = get_current_request_id()

    log_with_context(
        logger=logger,
        level=logging.INFO,
        message="Listing crews",
        request_id=request_id,
        route="/crew/crews",
    )

    items = list(crews_db.values())

    if label:
        items = [c for c in items if label in (c.labels or [])]
    if q:
        query = q.lower()
        items = [c for c in items if query in c.name.lower()]

    # Simple pagination
    start_idx = 0
    if cursor:
        try:
            start_idx = int(cursor)
        except:
            start_idx = 0

    paginated_items = items[start_idx : start_idx + limit]
    next_cursor = str(start_idx + limit) if len(items) > start_idx + limit else None

    return CrewListResponse(items=paginated_items, next_cursor=next_cursor)


@router.get("/crews/{crew_id}", response_model=Crew)
async def get_crew(request: Request, crew_id: UUID):
    """Get a specific crew by ID."""
    request_id = get_current_request_id()

    log_with_context(
        logger=logger,
        level=logging.INFO,
        message=f"Getting crew {crew_id}",
        request_id=request_id,
        route=f"/crew/crews/{crew_id}",
    )

    crew = crews_db.get(crew_id)
    if not crew:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Crew not found")

    return crew


@router.post("/crews/{crew_id}/run", response_model=Run)
async def run_crew(request: Request, crew_id: UUID, run_data: CrewRunRequest):
    """Run a crew task."""
    request_id = get_current_request_id()

    log_with_context(
        logger=logger,
        level=logging.INFO,
        message=f"Running crew {crew_id}",
        request_id=request_id,
        route=f"/crew/crews/{crew_id}/run",
    )

    crew = crews_db.get(crew_id)
    if not crew:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Crew not found")

    # Create a run
    run = Run(
        kind="crew", crew_id=crew_id, task_ref=run_data.task.dict(), status="queued"
    )
    runs_db[run.id] = run

    # Execute crew run in background with strategy
    strategy = run_data.strategy if hasattr(run_data, "strategy") else "sequential"
    asyncio.create_task(
        run_engine.execute_crew_run(run, crew_id, run_data.task, strategy)
    )

    return run


# Run endpoints
@router.get("/runs", response_model=RunListResponse)
async def list_runs(
    request: Request,
    status: str = None,
    agent_id: UUID = None,
    crew_id: UUID = None,
    limit: int = 50,
    cursor: str = None,
):
    """List runs with filtering and pagination."""
    request_id = get_current_request_id()

    log_with_context(
        logger=logger,
        level=logging.INFO,
        message="Listing runs",
        request_id=request_id,
        route="/crew/runs",
    )

    items = list(runs_db.values())

    if status:
        items = [r for r in items if r.status == status]
    if agent_id:
        items = [r for r in items if r.agent_id == agent_id]
    if crew_id:
        items = [r for r in items if r.crew_id == crew_id]

    # Simple pagination
    start_idx = 0
    if cursor:
        try:
            start_idx = int(cursor)
        except:
            start_idx = 0

    paginated_items = items[start_idx : start_idx + limit]
    next_cursor = str(start_idx + limit) if len(items) > start_idx + limit else None

    return RunListResponse(items=paginated_items, next_cursor=next_cursor)


@router.get("/runs/{run_id}", response_model=Run)
async def get_run(request: Request, run_id: UUID):
    """Get a specific run by ID."""
    request_id = get_current_request_id()

    log_with_context(
        logger=logger,
        level=logging.INFO,
        message=f"Getting run {run_id}",
        request_id=request_id,
        route=f"/crew/runs/{run_id}",
    )

    run = runs_db.get(run_id)
    if not run:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Run not found")

    return run


@router.post("/runs/{run_id}/cancel", response_model=RunStatusResponse)
async def cancel_run(request: Request, run_id: UUID):
    """Cancel a running task."""
    request_id = get_current_request_id()

    log_with_context(
        logger=logger,
        level=logging.INFO,
        message=f"Cancelling run {run_id}",
        request_id=request_id,
        route=f"/crew/runs/{run_id}/cancel",
    )

    run = runs_db.get(run_id)
    if not run:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Run not found")

    run.status = "cancelled"
    runs_db[run_id] = run

    return RunStatusResponse(status=run.status)
