"""
Request ID Middleware

Middleware to correlate logs and responses with a stable per-request ID.
"""

import logging
import uuid
from contextvars import ContextVar
from typing import Optional

from fastapi import Request

# Context variable for request ID
_request_id_ctx_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

logger = logging.getLogger(__name__)


def get_current_request_id() -> Optional[str]:
    """Get the current request ID from context."""
    return _request_id_ctx_var.get()


class RequestIDMiddleware:
    """Middleware to handle request ID generation and propagation."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # Extract or generate request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in request state and context
        request.state.request_id = request_id
        _request_id_ctx_var.set(request_id)

        logger.info(
            f"Request started - request_id: {request_id}, method: {request.method}, path: {request.url.path}"
        )

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                headers[b"x-request-id"] = request_id.encode()
                message["headers"] = list(headers.items())
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # Clean up context variable
            _request_id_ctx_var.set(None)
            logger.info(f"Request completed - request_id: {request_id}")
