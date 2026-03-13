"""Structured JSON logging configuration with correlation ID support.

Configures the root logger to emit JSON lines in production (ENVIRONMENT != development).
In development, keeps the default human-readable format for convenience.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

from app.core.config import settings

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class JSONFormatter(logging.Formatter):
    """Emit one JSON object per log line — structured logging for production."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = request_id_ctx.get("")
        if request_id:
            log_entry["request_id"] = request_id

        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry, ensure_ascii=False, default=str)


def configure_logging() -> None:
    """Set up root logger. Call once at application startup."""
    is_production = settings.environment.lower() not in ("development", "dev", "local", "test")

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicates on reload
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    if is_production:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-8s [%(name)s] %(message)s")
        )
    root.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
