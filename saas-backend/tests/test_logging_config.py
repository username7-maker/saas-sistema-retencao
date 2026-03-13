"""Tests for structured logging and correlation ID support."""

import json
import logging

from app.core.logging_config import JSONFormatter, request_id_ctx


class TestJSONFormatter:
    def setup_method(self):
        self.formatter = JSONFormatter()

    def test_basic_format(self):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Hello %s",
            args=("world",),
            exc_info=None,
        )
        output = self.formatter.format(record)
        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert data["message"] == "Hello world"
        assert "timestamp" in data

    def test_includes_request_id(self):
        token = request_id_ctx.set("abc123")
        try:
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0,
                msg="test msg", args=(), exc_info=None,
            )
            output = self.formatter.format(record)
            data = json.loads(output)
            assert data["request_id"] == "abc123"
        finally:
            request_id_ctx.reset(token)

    def test_no_request_id_when_empty(self):
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test", args=(), exc_info=None,
        )
        output = self.formatter.format(record)
        data = json.loads(output)
        assert "request_id" not in data

    def test_includes_exception(self):
        try:
            raise ValueError("boom")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="", lineno=0,
            msg="error happened", args=(), exc_info=exc_info,
        )
        output = self.formatter.format(record)
        data = json.loads(output)
        assert "exception" in data
        assert "ValueError" in data["exception"]


class TestRequestIdContext:
    def test_default_empty(self):
        assert request_id_ctx.get("") == ""

    def test_set_and_reset(self):
        token = request_id_ctx.set("req-123")
        assert request_id_ctx.get("") == "req-123"
        request_id_ctx.reset(token)
        assert request_id_ctx.get("") == ""
