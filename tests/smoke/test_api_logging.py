"""
Log assertion tests for file API services.

These tests verify that the structured logging works correctly by testing
the logging utilities directly and verifying log format.
"""

import json
import logging

from src.cage.utils.jsonl_logger import JSONLFormatter, log_with_context
from src.cage.utils.request_id_middleware import get_current_request_id


class TestAPILogging:
    """Tests for API logging behavior and structured log format."""

    def test_jsonl_formatter_structure(self):
        """Test that JSONL formatter produces correct log structure."""
        formatter = JSONLFormatter(service="test-service")

        # Create a test log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add extra fields
        record.req_id = "test-request-123"
        record.route = "/test/endpoint"

        # Format the record
        formatted = formatter.format(record)

        # Parse the JSON
        log_entry = json.loads(formatted)

        # Assert required fields are present
        required_fields = ["ts", "level", "service", "msg"]
        for field in required_fields:
            assert field in log_entry, f"Missing required field '{field}'"

        # Assert specific values
        assert log_entry["level"] == "INFO"
        assert log_entry["service"] == "test-service"
        assert log_entry["msg"] == "Test message"
        assert log_entry["request_id"] == "test-request-123"
        assert log_entry["route"] == "/test/endpoint"

    def test_jsonl_formatter_with_error(self):
        """Test JSONL formatter with error information."""
        formatter = JSONLFormatter(service="test-service")

        # Create a test log record with error info
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="/test/path",
            lineno=42,
            msg="Test error message",
            args=(),
            exc_info=None,
        )

        # Add error fields
        record.error = "TestError: Something went wrong"
        record.stack = "Traceback (most recent call last):\n  File 'test.py', line 42, in test\n    raise TestError()"

        # Format the record
        formatted = formatter.format(record)
        log_entry = json.loads(formatted)

        # Assert error fields are present
        assert log_entry["level"] == "ERROR"
        assert "error" in log_entry
        assert "stack" in log_entry
        assert log_entry["error"] == "TestError: Something went wrong"

    def test_log_with_context_function(self, caplog):
        """Test the log_with_context utility function."""
        logger = logging.getLogger("test.logger")

        with caplog.at_level(logging.INFO):
            log_with_context(
                logger=logger,
                level=logging.INFO,
                message="Test context message",
                request_id="test-req-456",
                route="/test/context",
                context={"key": "value"},
            )

        # Verify log was captured
        assert len(caplog.records) == 1
        record = caplog.records[0]

        # Check that extra data was added
        assert hasattr(record, "req_id")
        assert hasattr(record, "route")
        assert hasattr(record, "context")
        assert record.req_id == "test-req-456"
        assert record.route == "/test/context"
        assert record.context == {"key": "value"}

    def test_request_id_context_var(self):
        """Test that request ID context variable works."""
        # Initially should be None
        assert get_current_request_id() is None

        # Note: We can't easily test the context var setting without
        # the middleware, but we can test the getter function exists
        # and returns None when not set
        request_id = get_current_request_id()
        assert request_id is None

    def test_log_structure_consistency(self):
        """Test that log structure is consistent across different scenarios."""
        formatter = JSONLFormatter(service="test-service")

        # Test different log levels
        levels = [
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        ]

        for level in levels:
            record = logging.LogRecord(
                name="test.logger",
                level=level,
                pathname="/test/path",
                lineno=42,
                msg=f"Test message for {logging.getLevelName(level)}",
                args=(),
                exc_info=None,
            )

            formatted = formatter.format(record)
            log_entry = json.loads(formatted)

            # All logs should have the same base structure
            base_fields = ["ts", "level", "service", "msg"]
            for field in base_fields:
                assert (
                    field in log_entry
                ), f"Missing field '{field}' in {logging.getLevelName(level)} log"

            # Level should match
            assert log_entry["level"] == logging.getLevelName(level)
            assert log_entry["service"] == "test-service"

    def test_jsonl_format_validation(self):
        """Test that all formatted logs are valid JSONL."""
        formatter = JSONLFormatter(service="test-service")

        # Test various log scenarios
        test_cases = [
            {"msg": "Simple message", "req_id": "req-123"},
            {"msg": "Message with special chars: éñ中文", "route": "/api/test"},
            {"msg": "Error message", "error": "ValueError", "stack": "Traceback..."},
            {
                "msg": "Message with extra data",
                "context": {"user_id": "user-456", "action": "login"},
            },
        ]

        for i, test_case in enumerate(test_cases):
            record = logging.LogRecord(
                name="test.logger",
                level=logging.INFO,
                pathname="/test/path",
                lineno=42 + i,
                msg=test_case["msg"],
                args=(),
                exc_info=None,
            )

            # Add extra fields from test case
            for key, value in test_case.items():
                if key != "msg":
                    setattr(record, key, value)

            # Format and validate JSON
            formatted = formatter.format(record)

            # Should be valid JSON
            log_entry = json.loads(formatted)
            assert isinstance(log_entry, dict)
            assert "msg" in log_entry
            assert log_entry["msg"] == test_case["msg"]

    def test_timestamp_format(self):
        """Test that timestamps are in the correct format."""
        formatter = JSONLFormatter(service="test-service")

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path",
            lineno=42,
            msg="Test timestamp",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        log_entry = json.loads(formatted)

        # Timestamp should be present and in ISO format
        assert "ts" in log_entry
        assert isinstance(log_entry["ts"], str)

        # Should be in ISO format (YYYY-MM-DDTHH:MM:SS.microsecondsZ)
        ts = log_entry["ts"]
        assert len(ts) > 20  # Reasonable length for ISO timestamp
        assert ts.endswith("Z")  # Should end with Z for UTC
        assert "T" in ts  # Should have T separator between date and time
