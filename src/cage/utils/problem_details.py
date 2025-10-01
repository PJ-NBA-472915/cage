"""
Problem Details for HTTP APIs (RFC 7807) implementation.

This module provides utilities for creating standardized error responses
according to RFC 7807 Problem Details specification.
"""

from typing import Optional

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class ProblemDetail(BaseModel):
    """Problem Details schema according to RFC 7807."""

    type: str = Field(
        ...,
        description="A URI reference that identifies the problem type",
        example="https://example.com/problems/validation-error",
    )
    title: str = Field(
        ...,
        description="A short, human-readable summary of the problem type",
        example="Validation Error",
    )
    status: int = Field(..., description="The HTTP status code", example=400)
    detail: str = Field(
        ...,
        description="A human-readable explanation specific to this occurrence",
        example="The request body contains invalid data",
    )
    instance: str = Field(
        ...,
        description="A URI reference that identifies the specific occurrence of the problem",
        example="/files/edit",
    )
    errors: Optional[dict[str, list[str]]] = Field(
        None,
        description="Optional field for validation errors",
        example={"field1": ["error message 1", "error message 2"]},
    )


class ErrorTypes:
    """Standard error types for file API services."""

    # Client errors (4xx)
    VALIDATION_ERROR = "https://api.cage.dev/problems/validation-error"
    NOT_FOUND = "https://api.cage.dev/problems/not-found"
    CONFLICT = "https://api.cage.dev/problems/conflict"
    UNAUTHORIZED = "https://api.cage.dev/problems/unauthorized"
    FORBIDDEN = "https://api.cage.dev/problems/forbidden"
    RATE_LIMITED = "https://api.cage.dev/problems/rate-limited"
    BAD_REQUEST = "https://api.cage.dev/problems/bad-request"

    # Server errors (5xx)
    INTERNAL_ERROR = "https://api.cage.dev/problems/internal-error"
    SERVICE_UNAVAILABLE = "https://api.cage.dev/problems/service-unavailable"
    TIMEOUT = "https://api.cage.dev/problems/timeout"


class ErrorTitles:
    """Standard error titles for file API services."""

    VALIDATION_ERROR = "Validation Error"
    NOT_FOUND = "Not Found"
    CONFLICT = "Conflict"
    UNAUTHORIZED = "Unauthorized"
    FORBIDDEN = "Forbidden"
    RATE_LIMITED = "Rate Limited"
    BAD_REQUEST = "Bad Request"
    INTERNAL_ERROR = "Internal Server Error"
    SERVICE_UNAVAILABLE = "Service Unavailable"
    TIMEOUT = "Request Timeout"


def create_problem_detail(
    error_type: str,
    title: str,
    status: int,
    detail: str,
    instance: str,
    errors: Optional[dict[str, list[str]]] = None,
) -> ProblemDetail:
    """Create a Problem Detail response."""
    return ProblemDetail(
        type=error_type,
        title=title,
        status=status,
        detail=detail,
        instance=instance,
        errors=errors,
    )


def create_validation_error(
    detail: str, instance: str, errors: Optional[dict[str, list[str]]] = None
) -> ProblemDetail:
    """Create a validation error Problem Detail."""
    return create_problem_detail(
        error_type=ErrorTypes.VALIDATION_ERROR,
        title=ErrorTitles.VALIDATION_ERROR,
        status=422,
        detail=detail,
        instance=instance,
        errors=errors,
    )


def create_not_found_error(detail: str, instance: str) -> ProblemDetail:
    """Create a not found error Problem Detail."""
    return create_problem_detail(
        error_type=ErrorTypes.NOT_FOUND,
        title=ErrorTitles.NOT_FOUND,
        status=404,
        detail=detail,
        instance=instance,
    )


def create_conflict_error(detail: str, instance: str) -> ProblemDetail:
    """Create a conflict error Problem Detail."""
    return create_problem_detail(
        error_type=ErrorTypes.CONFLICT,
        title=ErrorTitles.CONFLICT,
        status=409,
        detail=detail,
        instance=instance,
    )


def create_internal_error(detail: str, instance: str) -> ProblemDetail:
    """Create an internal server error Problem Detail."""
    return create_problem_detail(
        error_type=ErrorTypes.INTERNAL_ERROR,
        title=ErrorTitles.INTERNAL_ERROR,
        status=500,
        detail=detail,
        instance=instance,
    )


def create_unauthorized_error(detail: str, instance: str) -> ProblemDetail:
    """Create an unauthorized error Problem Detail."""
    return create_problem_detail(
        error_type=ErrorTypes.UNAUTHORIZED,
        title=ErrorTitles.UNAUTHORIZED,
        status=401,
        detail=detail,
        instance=instance,
    )


def create_forbidden_error(detail: str, instance: str) -> ProblemDetail:
    """Create a forbidden error Problem Detail."""
    return create_problem_detail(
        error_type=ErrorTypes.FORBIDDEN,
        title=ErrorTitles.FORBIDDEN,
        status=403,
        detail=detail,
        instance=instance,
    )


def create_bad_request_error(detail: str, instance: str) -> ProblemDetail:
    """Create a bad request error Problem Detail."""
    return create_problem_detail(
        error_type=ErrorTypes.BAD_REQUEST,
        title=ErrorTitles.BAD_REQUEST,
        status=400,
        detail=detail,
        instance=instance,
    )


async def problem_detail_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Handle HTTPException and return Problem Details response."""
    # Map HTTP status codes to error types and titles
    error_mappings = {
        400: (ErrorTypes.BAD_REQUEST, ErrorTitles.BAD_REQUEST),
        401: (ErrorTypes.UNAUTHORIZED, ErrorTitles.UNAUTHORIZED),
        403: (ErrorTypes.FORBIDDEN, ErrorTitles.FORBIDDEN),
        404: (ErrorTypes.NOT_FOUND, ErrorTitles.NOT_FOUND),
        409: (ErrorTypes.CONFLICT, ErrorTitles.CONFLICT),
        422: (ErrorTypes.VALIDATION_ERROR, ErrorTitles.VALIDATION_ERROR),
        429: (ErrorTypes.RATE_LIMITED, ErrorTitles.RATE_LIMITED),
        500: (ErrorTypes.INTERNAL_ERROR, ErrorTitles.INTERNAL_ERROR),
        503: (ErrorTypes.SERVICE_UNAVAILABLE, ErrorTitles.SERVICE_UNAVAILABLE),
    }

    error_type, title = error_mappings.get(
        exc.status_code, (ErrorTypes.INTERNAL_ERROR, ErrorTitles.INTERNAL_ERROR)
    )

    problem = create_problem_detail(
        error_type=error_type,
        title=title,
        status=exc.status_code,
        detail=str(exc.detail) if exc.detail else "An error occurred",
        instance=request.url.path,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=problem.dict(),
        headers={"Content-Type": "application/problem+json"},
    )


async def validation_exception_handler(request: Request, exc) -> JSONResponse:
    """Handle Pydantic validation exceptions and return Problem Details response."""
    # Extract validation errors from Pydantic exception
    errors = {}
    if hasattr(exc, "errors"):
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            if field not in errors:
                errors[field] = []
            errors[field].append(error["msg"])

    problem = create_validation_error(
        detail="Request validation failed",
        instance=request.url.path,
        errors=errors if errors else None,
    )

    return JSONResponse(
        status_code=422,
        content=problem.dict(),
        headers={"Content-Type": "application/problem+json"},
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions and return Problem Details response."""
    # Log the full exception with stack trace
    import logging

    logger = logging.getLogger(__name__)
    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=True,
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "path": request.url.path,
            "method": request.method,
        },
    )

    # Create internal error response (don't expose stack trace to client)
    problem = create_internal_error(
        detail="An internal server error occurred", instance=request.url.path
    )

    return JSONResponse(
        status_code=500,
        content=problem.dict(),
        headers={"Content-Type": "application/problem+json"},
    )


def setup_problem_detail_handlers(app):
    """Set up Problem Details exception handlers for FastAPI app."""

    # Add exception handlers
    app.add_exception_handler(HTTPException, problem_detail_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
