"""
CrewAI Domain Models

Pydantic models for Agents, Crews, Runs, and related DTOs.
"""

from datetime import datetime
from typing import Dict, List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# Domain Models


class Agent(BaseModel):
    """Agent model representing an AI agent with specific role and configuration."""

    id: UUID = Field(default_factory=uuid4, description="Unique agent identifier")
    name: str = Field(..., min_length=1, description="Agent name")
    role: Literal["planner", "implementer", "verifier", "committer"] = Field(
        ..., description="Agent role in the crew"
    )
    config: Dict = Field(default_factory=dict, description="Agent configuration")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )


class Crew(BaseModel):
    """Crew model representing a group of agents working together."""

    id: UUID = Field(default_factory=uuid4, description="Unique crew identifier")
    name: str = Field(..., min_length=1, description="Crew name")
    roles: Dict[str, Optional[UUID]] = Field(
        default_factory=dict, description="Mapping of role names to agent IDs"
    )
    labels: Optional[List[str]] = Field(
        default_factory=list, description="Optional labels for crew categorization"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )


class Run(BaseModel):
    """Run model representing execution of an agent or crew task."""

    id: UUID = Field(default_factory=uuid4, description="Unique run identifier")
    kind: Literal["agent", "crew"] = Field(..., description="Type of run")
    agent_id: Optional[UUID] = Field(None, description="Agent ID (for agent runs)")
    crew_id: Optional[UUID] = Field(None, description="Crew ID (for crew runs)")
    status: Literal["queued", "running", "succeeded", "failed", "cancelled"] = Field(
        default="queued", description="Run status"
    )
    task_ref: Dict = Field(
        ..., description="Task reference with title, description, acceptance criteria"
    )
    result_summary: Optional[str] = Field(None, description="Summary of run results")
    artefacts: Optional[List[str]] = Field(
        default_factory=list, description="List of artefact paths created during run"
    )
    started_at: Optional[datetime] = Field(None, description="Run start timestamp")
    finished_at: Optional[datetime] = Field(
        None, description="Run completion timestamp"
    )


# DTOs (Data Transfer Objects)


class AgentCreate(BaseModel):
    """DTO for creating a new agent."""

    name: str = Field(..., min_length=1, description="Agent name")
    role: Literal["planner", "implementer", "verifier", "committer"] = Field(
        ..., description="Agent role"
    )
    config: Dict = Field(default_factory=dict, description="Agent configuration")


class CrewCreate(BaseModel):
    """DTO for creating a new crew."""

    name: str = Field(..., min_length=1, description="Crew name")
    roles: Dict[str, UUID] = Field(
        ..., description="Mapping of role names to agent IDs"
    )
    labels: Optional[List[str]] = Field(
        default_factory=list, description="Optional labels"
    )


class TaskSpec(BaseModel):
    """Task specification for agent/crew execution."""

    title: str = Field(..., min_length=1, description="Task title")
    description: str = Field(..., min_length=1, description="Task description")
    acceptance: List[str] = Field(..., min_items=1, description="Acceptance criteria")


class AgentInvoke(BaseModel):
    """DTO for invoking a single agent."""

    task: TaskSpec = Field(..., description="Task specification")
    context: Optional[Dict] = Field(
        default_factory=dict, description="Execution context"
    )
    timeout_s: int = Field(default=600, ge=1, le=3600, description="Timeout in seconds")


class CrewRunRequest(BaseModel):
    """DTO for running a crew task."""

    task: TaskSpec = Field(..., description="Task specification")
    strategy: str = Field(default="impl_then_verify", description="Execution strategy")
    timeout_s: int = Field(
        default=1200, ge=1, le=7200, description="Timeout in seconds"
    )


# Response DTOs


class AgentListResponse(BaseModel):
    """Response for listing agents with pagination."""

    items: List[Agent] = Field(..., description="List of agents")
    next_cursor: Optional[str] = Field(None, description="Cursor for next page")


class CrewListResponse(BaseModel):
    """Response for listing crews with pagination."""

    items: List[Crew] = Field(..., description="List of crews")
    next_cursor: Optional[str] = Field(None, description="Cursor for next page")


class RunListResponse(BaseModel):
    """Response for listing runs with pagination."""

    items: List[Run] = Field(..., description="List of runs")
    next_cursor: Optional[str] = Field(None, description="Cursor for next page")


class RunStatusResponse(BaseModel):
    """Response for run status updates."""

    status: str = Field(..., description="Current run status")
