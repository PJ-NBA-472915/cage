"""
JSONL logging utility for Cage application.

This module provides JSONL (JSON Lines) logging with structured format
for file API services. Each log entry is a single JSON object on its own line.
"""

import json
import logging
import os
import time
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any

# Import request ID context
try:
    from .request_id_middleware import get_current_request_id
except ImportError:
    # Fallback if middleware not available
    def get_current_request_id() -> None:
        return None


class JSONLFormatter(logging.Formatter):
    """Custom JSONL formatter for structured logging."""

    def __init__(self, service: str | None = None):
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSONL entry."""
        # Base log record with required fields
        # Try to get request_id from record, then from context, then from extra
        request_id = (
            getattr(record, "req_id", None)
            or get_current_request_id()
            or getattr(record, "request_id", None)
        )

        log_entry = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "service": self.service or "unknown",
            "request_id": request_id,
            "route": getattr(record, "route", None),
            "msg": record.getMessage(),
        }

        # Add optional fields if present
        if hasattr(record, "error") and record.error:
            log_entry["error"] = record.error

        if hasattr(record, "stack") and record.stack:
            log_entry["stack"] = record.stack

        if hasattr(record, "context") and record.context:
            log_entry["context"] = record.context

        # Add any extra JSON data from record
        if hasattr(record, "json_data") and record.json_data:
            log_entry.update(record.json_data)

        # Add file and line info for debugging
        log_entry["file"] = record.filename
        log_entry["line"] = record.lineno

        # Add function name if available
        if record.funcName:
            log_entry["func"] = record.funcName

        # Convert to JSON string (one line)
        return json.dumps(log_entry, ensure_ascii=False)


class JSONLHandler(TimedRotatingFileHandler):
    """Custom daily rotating file handler with JSONL formatting."""

    def __init__(self, log_dir: str, service: str, level: int = logging.INFO):
        # Ensure log directory exists
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # Create service subdirectory
        service_dir = log_path / service
        service_dir.mkdir(parents=True, exist_ok=True)

        # Create log file with .jsonl extension
        log_file = service_dir / f"{service}.jsonl"

        # Initialize TimedRotatingFileHandler for daily rotation
        super().__init__(
            filename=str(log_file),
            when="midnight",
            interval=1,
            backupCount=30,  # Keep 30 days of logs
            encoding="utf-8",
        )

        # Set up JSONL formatter
        formatter = JSONLFormatter(service=service)
        self.setFormatter(formatter)
        self.setLevel(level)

    def doRollover(self) -> None:
        """Override doRollover to use YYYY-MM-DD.jsonl format."""
        if self.stream:
            self.stream.close()
            self.stream = None

        # Get current time for date formatting
        current_time = int(time.time())

        # Create the new filename with YYYY-MM-DD.jsonl format
        if self.backupCount > 0:
            # Get the service name from the base filename
            base_path = Path(self.baseFilename)
            # service = base_path.stem  # This should be the service name

            # Format date as YYYY-MM-DD
            date_str = datetime.fromtimestamp(current_time).strftime("%Y-%m-%d")
            new_filename = base_path.parent / f"{date_str}.jsonl"

            # Rename the current file to the new format
            if os.path.exists(self.baseFilename):
                os.rename(self.baseFilename, str(new_filename))

        # Open new file
        if not self.delay:
            self.stream = self._open()


def setup_jsonl_logger(
    service: str, log_dir: str = "logs", level: int = logging.INFO
) -> logging.Logger:
    """
    Set up a JSONL logger for a specific service.

    Args:
        service: Service name (e.g., 'files-api', 'rag-api', 'lock-api')
        log_dir: Base log directory (default: 'logs')
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(f"cage.{service}")
    logger.setLevel(level)

    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()

    # Add JSONL file handler
    file_handler = JSONLHandler(log_dir, service, level)
    logger.addHandler(file_handler)

    # Prevent propagation to avoid duplicate logs
    logger.propagate = False

    return logger


def get_jsonl_logger(service: str) -> logging.Logger:
    """
    Get an existing JSONL logger for a service.

    Args:
        service: Service name

    Returns:
        Logger instance
    """
    return logging.getLogger(f"cage.{service}")


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    request_id: str | None = None,
    route: str | None = None,
    error: str | None = None,
    stack: str | None = None,
    context: dict[str, Any] | None = None,
    **kwargs,
) -> None:
    """
    Log a message with structured context.

    Args:
        logger: Logger instance
        level: Log level (e.g., logging.INFO, logging.ERROR)
        message: Log message
        request_id: Request ID for tracing
        route: API route being called
        error: Error message (for error logs)
        stack: Stack trace (for error logs)
        context: Additional context dictionary
        **kwargs: Additional fields to include in log
    """
    # Create a log record with extra fields
    extra = {}
    if request_id:
        extra[
            "req_id"
        ] = request_id  # Use req_id instead of request_id to avoid conflicts
    if route:
        extra["route"] = route
    if error:
        extra["error"] = error
    if stack:
        extra["stack"] = stack
    if context:
        extra["context"] = context
    if kwargs:
        extra.update(kwargs)

    logger.log(level, message, extra=extra)


# Convenience functions for common services
def get_files_api_logger() -> logging.Logger:
    """Get the files API JSONL logger."""
    return get_jsonl_logger("files-api")


def get_rag_api_logger() -> logging.Logger:
    """Get the RAG API JSONL logger."""
    return get_jsonl_logger("rag-api")


def get_lock_api_logger() -> logging.Logger:
    """Get the lock API JSONL logger."""
    return get_jsonl_logger("lock-api")


def get_git_api_logger() -> logging.Logger:
    """Get the git API JSONL logger."""
    return get_jsonl_logger("git-api")
