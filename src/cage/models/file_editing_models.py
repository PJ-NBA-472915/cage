"""
File Editing API models for optimistic concurrency.

This module provides Pydantic models for the new file editing API endpoints
that implement optimistic concurrency with ETag support.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class FileContentResponse(BaseModel):
    """Response model for GET /files/{path} endpoint."""

    path: str
    sha: str
    size: int
    encoding: str = "base64"
    content: str
    last_modified: datetime


class FileCreateUpdateRequest(BaseModel):
    """Request model for PUT /files/{path} endpoint."""

    message: str
    content_base64: str
    base_sha: Optional[str] = None
    author: Optional[dict[str, str]] = None
    committer: Optional[dict[str, str]] = None


class FileCreateUpdateResponse(BaseModel):
    """Response model for PUT /files/{path} endpoint."""

    path: str
    sha_before: Optional[str] = None
    sha_after: str
    commit: "CommitInfo"


class CommitInfo(BaseModel):
    """Commit information for file operations."""

    id: str
    message: str
    timestamp: datetime
    author: Optional[dict[str, str]] = None
    committer: Optional[dict[str, str]] = None


class JsonPatchRequest(BaseModel):
    """Request model for PATCH /files/{path} endpoint (JSON Patch)."""

    operations: list[dict[str, Any]] = Field(
        ..., description="JSON Patch operations array"
    )


class TextPatchRequest(BaseModel):
    """Request model for PATCH /files/{path} endpoint (Text Patch)."""

    content: str = Field(..., description="New file content")
    message: str = Field(..., description="Description of the change")


class LinePatchRequest(BaseModel):
    """Request model for PATCH /files/{path} endpoint (Line-based Patch)."""

    operations: list[dict[str, Any]] = Field(
        ..., description="Line-based operations (add, remove, replace)"
    )
    message: str = Field(..., description="Description of the change")


class FileDeleteRequest(BaseModel):
    """Request model for DELETE /files/{path} endpoint."""

    message: str


class AuditEntry(BaseModel):
    """Audit trail entry model."""

    id: str
    timestamp: datetime
    actor: str
    method: str
    path: str
    base_etag: Optional[str] = None
    new_etag: Optional[str] = None
    sha_before: Optional[str] = None
    sha_after: Optional[str] = None
    message: str


class AuditQueryParams(BaseModel):
    """Query parameters for GET /audit endpoint."""

    path: Optional[str] = None
    actor: Optional[str] = None
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)
    cursor: Optional[str] = None


class AuditResponse(BaseModel):
    """Response model for GET /audit endpoint."""

    items: list[AuditEntry]
    next_cursor: Optional[str] = None


class FileOperationError(BaseModel):
    """Error response model for file operations."""

    error: str
    code: str
    details: Optional[dict[str, Any]] = None


class FileSearchRequest(BaseModel):
    """Request model for file search using RAG."""

    query: str = Field(..., description="Search query text")
    filters: Optional[dict[str, Any]] = Field(
        None, description="Search filters (path, language, etc.)"
    )
    top_k: int = Field(8, description="Maximum number of results to return")


class FileSearchHit(BaseModel):
    """Individual search hit from file search."""

    content: str = Field(..., description="Content snippet")
    metadata: dict[str, Any] = Field(
        ..., description="File metadata (path, language, etc.)"
    )
    score: float = Field(..., description="Relevance score")
    blob_sha: str = Field(..., description="Git blob SHA")


class FileSearchResponse(BaseModel):
    """Response model for file search."""

    status: str = Field(..., description="Search status")
    hits: list[FileSearchHit] = Field(..., description="Search results")
    total: int = Field(..., description="Total number of results")
    query: str = Field(..., description="Original query")


class FileReindexRequest(BaseModel):
    """Request model for reindexing files in RAG system."""

    scope: str = Field(
        ..., description="Reindex scope: 'repo', 'tasks', 'chat', or 'all'"
    )


class FileReindexResponse(BaseModel):
    """Response model for file reindexing."""

    status: str = Field(..., description="Reindex status")
    scope: str = Field(..., description="Reindex scope")
    indexed_files: int = Field(..., description="Number of files indexed")
    total_chunks: int = Field(..., description="Total number of chunks created")
    blob_shas: list[str] = Field(..., description="List of blob SHAs processed")


# Update forward references
FileCreateUpdateResponse.model_rebuild()
