"""
File Editing API models for optimistic concurrency.

This module provides Pydantic models for the new file editing API endpoints
that implement optimistic concurrency with ETag support.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


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
    author: Optional[Dict[str, str]] = None
    committer: Optional[Dict[str, str]] = None


class FileCreateUpdateResponse(BaseModel):
    """Response model for PUT /files/{path} endpoint."""
    path: str
    sha_before: Optional[str] = None
    sha_after: str
    commit: 'CommitInfo'


class CommitInfo(BaseModel):
    """Commit information for file operations."""
    id: str
    message: str
    timestamp: datetime
    author: Optional[Dict[str, str]] = None
    committer: Optional[Dict[str, str]] = None


class JsonPatchRequest(BaseModel):
    """Request model for PATCH /files/{path} endpoint (JSON Patch)."""
    operations: List[Dict[str, Any]] = Field(..., description="JSON Patch operations array")


class TextPatchRequest(BaseModel):
    """Request model for PATCH /files/{path} endpoint (Text Patch)."""
    content: str = Field(..., description="New file content")
    message: str = Field(..., description="Description of the change")


class LinePatchRequest(BaseModel):
    """Request model for PATCH /files/{path} endpoint (Line-based Patch)."""
    operations: List[Dict[str, Any]] = Field(..., description="Line-based operations (add, remove, replace)")
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
    items: List[AuditEntry]
    next_cursor: Optional[str] = None


class FileOperationError(BaseModel):
    """Error response model for file operations."""
    error: str
    code: str
    details: Optional[Dict[str, Any]] = None


# Update forward references
FileCreateUpdateResponse.model_rebuild()
