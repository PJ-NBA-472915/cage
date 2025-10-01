"""
Standardized HTTP status codes and error handling for file API services.

This module provides consistent status code handling across all file API services.
"""

from enum import IntEnum
from typing import Any, Dict, Optional

from fastapi import HTTPException


class HTTPStatus(IntEnum):
    """Standard HTTP status codes with clear semantic meaning."""

    # 2xx Success
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204

    # 4xx Client Errors
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429

    # 5xx Server Errors
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504
    REQUEST_TIMEOUT = 408


def create_http_exception(
    status_code: int, detail: str, headers: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """Create an HTTPException with standardized error handling."""
    return HTTPException(status_code=status_code, detail=detail, headers=headers or {})


def create_authentication_error(
    detail: str = "Invalid authentication credentials",
) -> HTTPException:
    """Create a standardized authentication error."""
    return create_http_exception(HTTPStatus.UNAUTHORIZED, detail)


def create_authorization_error(
    detail: str = "Insufficient permissions",
) -> HTTPException:
    """Create a standardized authorization error."""
    return create_http_exception(HTTPStatus.FORBIDDEN, detail)


def create_validation_error(
    detail: str = "Invalid request parameters",
) -> HTTPException:
    """Create a standardized validation error."""
    return create_http_exception(HTTPStatus.BAD_REQUEST, detail)


def create_not_found_error(resource: str = "Resource") -> HTTPException:
    """Create a standardized not found error."""
    return create_http_exception(HTTPStatus.NOT_FOUND, f"{resource} not found")


def create_conflict_error(detail: str = "Resource conflict") -> HTTPException:
    """Create a standardized conflict error."""
    return create_http_exception(HTTPStatus.CONFLICT, detail)


def create_internal_error(detail: str = "Internal server error") -> HTTPException:
    """Create a standardized internal server error."""
    return create_http_exception(HTTPStatus.INTERNAL_SERVER_ERROR, detail)


def create_service_unavailable_error(
    detail: str = "Service temporarily unavailable",
) -> HTTPException:
    """Create a standardized service unavailable error."""
    return create_http_exception(HTTPStatus.SERVICE_UNAVAILABLE, detail)


def create_timeout_error(operation: str = "Operation") -> HTTPException:
    """Create a standardized timeout error."""
    return create_http_exception(HTTPStatus.REQUEST_TIMEOUT, f"{operation} timed out")


def create_not_implemented_error(feature: str = "Feature") -> HTTPException:
    """Create a standardized not implemented error."""
    return create_http_exception(
        HTTPStatus.NOT_IMPLEMENTED, f"{feature} not implemented"
    )


# Common error patterns for file API services
def validate_pod_token(
    token: Optional[str] = None, expected_token: Optional[str] = None
) -> str:
    """
    Validate POD_TOKEN for authentication.

    Args:
        token: The token to validate
        expected_token: The expected token value

    Returns:
        The validated token

    Raises:
        HTTPException: If token validation fails
    """
    if not expected_token:
        raise create_service_unavailable_error("Authentication service not configured")

    if not token:
        raise create_authentication_error("Authentication token required")

    if token != expected_token:
        raise create_authentication_error("Invalid authentication token")

    return token


def handle_file_operation_error(
    operation: str, path: str, error: Exception
) -> HTTPException:
    """
    Handle file operation errors with appropriate status codes.

    Args:
        operation: The file operation being performed
        path: The file path
        error: The exception that occurred

    Returns:
        HTTPException with appropriate status code
    """
    error_str = str(error).lower()

    if "not found" in error_str or "no such file" in error_str:
        return create_not_found_error(f"File '{path}'")
    elif "permission denied" in error_str or "access denied" in error_str:
        return create_authorization_error(f"Permission denied for file '{path}'")
    elif "file exists" in error_str or "already exists" in error_str:
        return create_conflict_error(f"File '{path}' already exists")
    elif "timeout" in error_str:
        return create_timeout_error(f"File operation '{operation}'")
    elif "not implemented" in error_str:
        return create_not_implemented_error(f"File operation '{operation}'")
    else:
        return create_internal_error(f"File operation '{operation}' failed: {error}")


def handle_git_operation_error(operation: str, error: Exception) -> HTTPException:
    """
    Handle git operation errors with appropriate status codes.

    Args:
        operation: The git operation being performed
        error: The exception that occurred

    Returns:
        HTTPException with appropriate status code
    """
    error_str = str(error).lower()

    if "not a git repository" in error_str:
        return create_not_found_error("Git repository")
    elif "permission denied" in error_str:
        return create_authorization_error("Git repository access denied")
    elif "merge conflict" in error_str:
        return create_conflict_error("Git merge conflict")
    elif "timeout" in error_str:
        return create_timeout_error(f"Git operation '{operation}'")
    else:
        return create_internal_error(f"Git operation '{operation}' failed: {error}")


def handle_rag_operation_error(operation: str, error: Exception) -> HTTPException:
    """
    Handle RAG operation errors with appropriate status codes.

    Args:
        operation: The RAG operation being performed
        error: The exception that occurred

    Returns:
        HTTPException with appropriate status code
    """
    error_str = str(error).lower()

    if "connection" in error_str or "database" in error_str:
        return create_service_unavailable_error("RAG database connection failed")
    elif "timeout" in error_str:
        return create_timeout_error(f"RAG operation '{operation}'")
    elif "not found" in error_str:
        return create_not_found_error("RAG document or index")
    else:
        return create_internal_error(f"RAG operation '{operation}' failed: {error}")


def handle_lock_operation_error(operation: str, error: Exception) -> HTTPException:
    """
    Handle lock/build operation errors with appropriate status codes.

    Args:
        operation: The lock/build operation being performed
        error: The exception that occurred

    Returns:
        HTTPException with appropriate status code
    """
    error_str = str(error).lower()

    if "timeout" in error_str:
        return create_timeout_error(f"Lock operation '{operation}'")
    elif "not found" in error_str:
        return create_not_found_error("Lock resource or template")
    elif "build failed" in error_str or "compilation" in error_str:
        return create_validation_error(f"Lock build failed: {error}")
    elif "not implemented" in error_str:
        return create_not_implemented_error(f"Lock operation '{operation}'")
    else:
        return create_internal_error(f"Lock operation '{operation}' failed: {error}")


if __name__ == "__main__":
    # Test the error creation functions
    print("Testing HTTP status code utilities...")

    # Test authentication error
    auth_error = create_authentication_error()
    print(f"Auth error: {auth_error.status_code} - {auth_error.detail}")

    # Test validation error
    validation_error = create_validation_error("Invalid file path")
    print(
        f"Validation error: {validation_error.status_code} - {validation_error.detail}"
    )

    # Test file operation error
    file_error = handle_file_operation_error(
        "read", "/nonexistent/file.txt", FileNotFoundError("File not found")
    )
    print(f"File error: {file_error.status_code} - {file_error.detail}")

    print("All tests passed!")
