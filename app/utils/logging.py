"""Structured (JSON-lines) logging using only the standard library.

Rule for this project: log identifiers, decisions, reasons and latencies.
NEVER log message text, customer data, or API keys. Pass extra fields with
`logger.info("event", extra={"fields": {...}})`.
"""

import json
import logging
import sys
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        payload.update(getattr(record, "fields", {}))
        if record.exc_info:
            # Exception type only: tracebacks can contain request data.
            payload["exc_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    # The SDK logs request/response BODIES at debug level (headers are redacted, bodies
    # are not - per its docs). Keep it at WARNING so ticket text never reaches the logs.
    logging.getLogger("typesafe_sdk").setLevel(logging.WARNING)
