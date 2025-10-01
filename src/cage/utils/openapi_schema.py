"""
OpenAPI schema utilities for file API services.

This module provides standardized OpenAPI schema components and utilities
for consistent API documentation across all file API services.
"""

from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

# Standard Problem Details schema for RFC 7807 compliance
PROBLEM_DETAILS_SCHEMA = {
    "ProblemDetail": {
        "type": "object",
        "required": ["type", "title", "status", "detail"],
        "properties": {
            "type": {
                "type": "string",
                "format": "uri",
                "description": "A URI reference that identifies the problem type",
                "example": "https://example.com/problems/validation-error",
            },
            "title": {
                "type": "string",
                "description": "A short, human-readable summary of the problem type",
                "example": "Validation Error",
            },
            "status": {
                "type": "integer",
                "description": "The HTTP status code",
                "example": 400,
            },
            "detail": {
                "type": "string",
                "description": "A human-readable explanation specific to this occurrence of the problem",
                "example": "Your request parameters did not validate.",
            },
            "instance": {
                "type": "string",
                "format": "uri",
                "description": "A URI reference that identifies the specific occurrence of the problem",
                "example": "/files/edit",
            },
            "errors": {
                "type": "object",
                "description": "A map of validation errors, where keys are field names and values are lists of error messages",
                "additionalProperties": {"type": "array", "items": {"type": "string"}},
                "example": {
                    "path": ["Path cannot be empty", "Path must be absolute"],
                    "operation": ["Operation 'delete' is not supported"],
                },
            },
        },
    }
}

# Standard response headers schema
RESPONSE_HEADERS_SCHEMA = {
    "X-Request-ID": {
        "description": "Request ID for tracing and correlation",
        "schema": {
            "type": "string",
            "format": "uuid",
            "example": "123e4567-e89b-12d3-a456-426614174000",
        },
    },
    "Content-Type": {
        "description": "Content type of the response",
        "schema": {"type": "string", "example": "application/json"},
    },
}

# Standard error response schemas
ERROR_RESPONSES_SCHEMA = {
    "400": {
        "description": "Bad Request - Invalid request parameters",
        "content": {
            "application/problem+json": {
                "schema": {"$ref": "#/components/schemas/ProblemDetail"},
                "example": {
                    "type": "https://example.com/problems/validation-error",
                    "title": "Validation Failed",
                    "status": 400,
                    "detail": "Your request parameters did not validate.",
                    "instance": "/files/edit",
                    "errors": {
                        "path": ["Path cannot be empty"],
                        "operation": ["Operation 'delete' is not supported"],
                    },
                },
            }
        },
        "headers": RESPONSE_HEADERS_SCHEMA,
    },
    "401": {
        "description": "Unauthorized - Invalid authentication credentials",
        "content": {
            "application/problem+json": {
                "schema": {"$ref": "#/components/schemas/ProblemDetail"},
                "example": {
                    "type": "https://example.com/problems/unauthorized",
                    "title": "Unauthorized",
                    "status": 401,
                    "detail": "Invalid authentication credentials",
                    "instance": "/files/edit",
                },
            }
        },
        "headers": RESPONSE_HEADERS_SCHEMA,
    },
    "403": {
        "description": "Forbidden - Insufficient permissions",
        "content": {
            "application/problem+json": {
                "schema": {"$ref": "#/components/schemas/ProblemDetail"},
                "example": {
                    "type": "https://example.com/problems/forbidden",
                    "title": "Forbidden",
                    "status": 403,
                    "detail": "Insufficient permissions to access this resource",
                    "instance": "/files/edit",
                },
            }
        },
        "headers": RESPONSE_HEADERS_SCHEMA,
    },
    "404": {
        "description": "Not Found - Resource not found",
        "content": {
            "application/problem+json": {
                "schema": {"$ref": "#/components/schemas/ProblemDetail"},
                "example": {
                    "type": "https://example.com/problems/not-found",
                    "title": "Not Found",
                    "status": 404,
                    "detail": "The requested resource was not found",
                    "instance": "/files/edit",
                },
            }
        },
        "headers": RESPONSE_HEADERS_SCHEMA,
    },
    "409": {
        "description": "Conflict - Resource conflict",
        "content": {
            "application/problem+json": {
                "schema": {"$ref": "#/components/schemas/ProblemDetail"},
                "example": {
                    "type": "https://example.com/problems/conflict",
                    "title": "Conflict",
                    "status": 409,
                    "detail": "Resource conflict occurred",
                    "instance": "/files/edit",
                },
            }
        },
        "headers": RESPONSE_HEADERS_SCHEMA,
    },
    "422": {
        "description": "Unprocessable Entity - Validation error",
        "content": {
            "application/problem+json": {
                "schema": {"$ref": "#/components/schemas/ProblemDetail"},
                "example": {
                    "type": "https://example.com/problems/validation-error",
                    "title": "Validation Failed",
                    "status": 422,
                    "detail": "Your request parameters did not validate.",
                    "instance": "/files/edit",
                    "errors": {
                        "path": ["Path cannot be empty", "Path must be absolute"],
                        "operation": ["Operation 'delete' is not supported"],
                    },
                },
            }
        },
        "headers": RESPONSE_HEADERS_SCHEMA,
    },
    "500": {
        "description": "Internal Server Error",
        "content": {
            "application/problem+json": {
                "schema": {"$ref": "#/components/schemas/ProblemDetail"},
                "example": {
                    "type": "https://example.com/problems/internal-server-error",
                    "title": "Internal Server Error",
                    "status": 500,
                    "detail": "An internal server error occurred. Please try again later.",
                    "instance": "/files/edit",
                },
            }
        },
        "headers": RESPONSE_HEADERS_SCHEMA,
    },
    "503": {
        "description": "Service Unavailable",
        "content": {
            "application/problem+json": {
                "schema": {"$ref": "#/components/schemas/ProblemDetail"},
                "example": {
                    "type": "https://example.com/problems/service-unavailable",
                    "title": "Service Unavailable",
                    "status": 503,
                    "detail": "Service temporarily unavailable",
                    "instance": "/files/edit",
                },
            }
        },
        "headers": RESPONSE_HEADERS_SCHEMA,
    },
}

# Standard security schema for Bearer token authentication
SECURITY_SCHEMA = {
    "BearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Bearer token authentication",
    }
}

# Standard components schema
COMPONENTS_SCHEMA = {
    "schemas": PROBLEM_DETAILS_SCHEMA,
    "securitySchemes": SECURITY_SCHEMA,
}


def get_standard_openapi_schema(
    app: FastAPI,
    title: str,
    version: str = "1.0.0",
    description: str = "",
    tags: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Generate a standardized OpenAPI schema for a FastAPI application.

    Args:
        app: FastAPI application instance
        title: API title
        version: API version
        description: API description
        tags: Optional list of tags for API organization

    Returns:
        Standardized OpenAPI schema dictionary
    """
    # Get the base OpenAPI schema
    openapi_schema = get_openapi(
        title=title,
        version=version,
        description=description,
        routes=app.routes,
        tags=tags or [],
    )

    # Add standardized components
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}

    # Merge schemas
    if "schemas" not in openapi_schema["components"]:
        openapi_schema["components"]["schemas"] = {}
    openapi_schema["components"]["schemas"].update(PROBLEM_DETAILS_SCHEMA)

    # Add security schemes
    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {}
    openapi_schema["components"]["securitySchemes"].update(SECURITY_SCHEMA)

    # Add global security requirement
    openapi_schema["security"] = [{"BearerAuth": []}]

    # Update info section
    openapi_schema["info"].update(
        {
            "title": title,
            "version": version,
            "description": description,
            "contact": {"name": "File API Support", "email": "support@example.com"},
            "license": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
        }
    )

    # Add standard error responses to all paths
    for path, path_item in openapi_schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if isinstance(operation, dict) and "responses" in operation:
                # Add standard error responses if not already present
                for status_code, response_schema in ERROR_RESPONSES_SCHEMA.items():
                    if status_code not in operation["responses"]:
                        operation["responses"][status_code] = response_schema

    return openapi_schema


def add_response_headers_to_openapi(openapi_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add X-Request-ID header to all successful responses in OpenAPI schema.

    Args:
        openapi_schema: OpenAPI schema dictionary

    Returns:
        Updated OpenAPI schema with response headers
    """
    for path, path_item in openapi_schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if isinstance(operation, dict) and "responses" in operation:
                for status_code, response in operation["responses"].items():
                    # Add headers to 2xx responses
                    if status_code.startswith("2"):
                        if "headers" not in response:
                            response["headers"] = {}
                        response["headers"]["X-Request-ID"] = {
                            "description": "Request ID for tracing and correlation",
                            "schema": {
                                "type": "string",
                                "format": "uuid",
                                "example": "123e4567-e89b-12d3-a456-426614174000",
                            },
                        }

    return openapi_schema


def add_examples_to_openapi(
    openapi_schema: Dict[str, Any], examples: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Add concrete examples to OpenAPI schema endpoints.

    Args:
        openapi_schema: OpenAPI schema dictionary
        examples: Dictionary mapping endpoint paths to example data

    Returns:
        Updated OpenAPI schema with examples
    """
    for path, path_examples in examples.items():
        if path in openapi_schema.get("paths", {}):
            path_item = openapi_schema["paths"][path]
            for method, operation in path_item.items():
                if isinstance(operation, dict):
                    # Add request body examples
                    if (
                        "requestBody" in operation
                        and "content" in operation["requestBody"]
                    ):
                        for content_type, content_schema in operation["requestBody"][
                            "content"
                        ].items():
                            if path_examples.get("request"):
                                content_schema["example"] = path_examples["request"]

                    # Add response examples
                    if "responses" in operation:
                        for status_code, response in operation["responses"].items():
                            if "content" in response:
                                for content_type, content_schema in response[
                                    "content"
                                ].items():
                                    if path_examples.get("response"):
                                        content_schema["example"] = path_examples[
                                            "response"
                                        ]

    return openapi_schema


# Pre-defined examples for file API services
FILES_API_EXAMPLES = {
    "/files/edit": {
        "request": {
            "path": "/src/main.py",
            "operation": "edit",
            "content": "print('Hello, World!')",
            "line_start": 1,
            "line_end": 1,
        },
        "response": {
            "ok": True,
            "file": "/src/main.py",
            "operation": "edit",
            "lock_id": "123e4567-e89b-12d3-a456-426614174000",
            "pre_hash": "sha256:abc123...",
            "post_hash": "sha256:def456...",
            "diff": "+ print('Hello, World!')",
            "warnings": [],
            "conflicts": [],
        },
    },
    "/files/commit": {
        "request": {
            "message": "Add hello world example",
            "task_id": "task-123",
            "author": "developer@example.com",
        },
        "response": {
            "ok": True,
            "commit_id": "abc123def456",
            "message": "Add hello world example",
            "files_changed": ["/src/main.py"],
            "timestamp": "2025-09-30T11:45:00Z",
        },
    },
}

RAG_API_EXAMPLES = {
    "/rag/query": {
        "request": {
            "query": "How to implement authentication?",
            "top_k": 5,
            "filters": {"language": "python"},
        },
        "response": {
            "status": "success",
            "hits": [
                {
                    "content": "Authentication can be implemented using JWT tokens...",
                    "metadata": {
                        "path": "/docs/auth.md",
                        "language": "markdown",
                        "commit_sha": "abc123",
                        "branch": "main",
                        "chunk_id": "chunk-1",
                    },
                    "score": 0.95,
                    "blob_sha": "sha256:abc123...",
                }
            ],
            "total": 1,
            "query": "How to implement authentication?",
        },
    }
}

LOCK_API_EXAMPLES = {
    "/lock/generate": {
        "request": {
            "template": "web-server",
            "variables": {"port": "8080", "host": "localhost"},
            "output_path": "/tmp/my-app",
        },
        "response": {
            "status": "success",
            "template": "web-server",
            "output_path": "/tmp/my-app",
            "files_generated": ["main.go", "go.mod", "README.md"],
            "instructions": "Run 'go run main.go' to start the server",
        },
    }
}

GIT_API_EXAMPLES = {
    "/git/status": {
        "response": {
            "status": "success",
            "branch": "main",
            "clean": True,
            "ahead": 0,
            "behind": 0,
            "modified_files": [],
            "staged_files": [],
        }
    }
}


if __name__ == "__main__":
    # Test the OpenAPI schema utilities
    print("Testing OpenAPI schema utilities...")

    # Test Problem Details schema
    print(f"Problem Details schema: {PROBLEM_DETAILS_SCHEMA}")

    # Test error responses schema
    print(f"Error responses count: {len(ERROR_RESPONSES_SCHEMA)}")

    # Test components schema
    print(f"Components schema keys: {list(COMPONENTS_SCHEMA.keys())}")

    print("All OpenAPI schema utilities tests passed!")
