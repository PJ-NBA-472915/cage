"""
Enhanced RequestID middleware for file API services.

This middleware ensures request IDs are properly propagated through
all logging contexts and responses.
"""

import logging
import uuid
from contextvars import ContextVar

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Context variable to store request ID across async operations
request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)


class EnhancedRequestIDMiddleware(BaseHTTPMiddleware):
    """Enhanced middleware for request ID propagation with JSONL logging support."""

    def __init__(self, app, service_name: str = "unknown") -> None:
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next) -> None:
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Add request ID to request state
        request.state.request_id = request_id

        # Set request ID in context variable for global access
        request_id_context.set(request_id)

        # Set up logging context for compatibility with old logging
        old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.request_id = request_id
            return record

        logging.setLogRecordFactory(record_factory)

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            # Clean up context
            request_id_context.set(None)
            # Restore original factory
            logging.setLogRecordFactory(old_factory)


def get_current_request_id() -> str | None:
    """Get the current request ID from context."""
    return request_id_context.get()


def get_request_id_from_request(request: Request) -> str | None:
    """Get request ID from FastAPI request object."""
    return getattr(request.state, "request_id", None)
