"""
File operations logging utility.

This module provides detailed JSON logging for file editing operations
with daily rotation in the logs/api/files/ directory.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from .jsonl_logger import setup_jsonl_logger


class FileOperationLogger:
    """Logger for file editing operations with detailed JSON format."""

    def __init__(self, log_dir: str = "logs/api/files"):
        """
        Initialize file operation logger.

        Args:
            log_dir: Directory for file operation logs
        """
        self.log_dir = log_dir
        self.logger = setup_jsonl_logger("files", log_dir, logging.INFO)

    def log_file_read(
        self,
        path: str,
        etag: str,
        sha: str,
        size: int,
        actor: str,
        success: bool,
        error: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ):
        """Log file read operation."""
        log_data = {
            "operation": "file_read",
            "path": path,
            "etag": etag,
            "sha": sha,
            "size": size,
            "actor": actor,
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if error:
            log_data["error"] = error
        if duration_ms:
            log_data["duration_ms"] = duration_ms

        self.logger.info("File read operation", extra={"json_data": log_data})

    def log_file_write(
        self,
        path: str,
        etag_before: Optional[str],
        etag_after: str,
        sha_before: Optional[str],
        sha_after: str,
        actor: str,
        method: str,
        success: bool,
        error: Optional[str] = None,
        duration_ms: Optional[int] = None,
        message: Optional[str] = None,
    ):
        """Log file write operation (PUT/PATCH/DELETE)."""
        log_data = {
            "operation": "file_write",
            "path": path,
            "method": method,
            "etag_before": etag_before,
            "etag_after": etag_after,
            "sha_before": sha_before,
            "sha_after": sha_after,
            "actor": actor,
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if error:
            log_data["error"] = error
        if duration_ms:
            log_data["duration_ms"] = duration_ms
        if message:
            log_data["message"] = message

        self.logger.info("File write operation", extra={"json_data": log_data})

    def log_etag_validation(
        self, path: str, provided_etag: str, current_etag: str, valid: bool, actor: str
    ):
        """Log ETag validation."""
        log_data = {
            "operation": "etag_validation",
            "path": path,
            "provided_etag": provided_etag,
            "current_etag": current_etag,
            "valid": valid,
            "actor": actor,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.logger.info("ETag validation", extra={"json_data": log_data})

    def log_json_patch(
        self,
        path: str,
        operations_count: int,
        etag_before: str,
        etag_after: str,
        actor: str,
        success: bool,
        error: Optional[str] = None,
    ):
        """Log JSON Patch operation."""
        log_data = {
            "operation": "json_patch",
            "path": path,
            "operations_count": operations_count,
            "etag_before": etag_before,
            "etag_after": etag_after,
            "actor": actor,
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if error:
            log_data["error"] = error

        self.logger.info("JSON Patch operation", extra={"json_data": log_data})

    def log_path_validation(
        self,
        path: str,
        normalized_path: str,
        valid: bool,
        actor: str,
        error: Optional[str] = None,
    ):
        """Log path validation."""
        log_data = {
            "operation": "path_validation",
            "original_path": path,
            "normalized_path": normalized_path,
            "valid": valid,
            "actor": actor,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if error:
            log_data["error"] = error

        self.logger.info("Path validation", extra={"json_data": log_data})

    def log_audit_query(
        self,
        actor: str,
        filters: dict[str, Any],
        result_count: int,
        duration_ms: Optional[int] = None,
    ):
        """Log audit trail query."""
        log_data = {
            "operation": "audit_query",
            "actor": actor,
            "filters": filters,
            "result_count": result_count,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if duration_ms:
            log_data["duration_ms"] = duration_ms

        self.logger.info("Audit query", extra={"json_data": log_data})


# Global file operation logger instance
file_logger = FileOperationLogger()
