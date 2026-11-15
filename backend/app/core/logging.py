"""Logging configuration and request-scoped correlation ids."""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar

REQUEST_ID_HEADER = "X-Request-ID"
_request_id: ContextVar[str] = ContextVar("request_id", default="req_unknown")

_LOG_FORMAT = "%(asctime)s %(levelname)-8s [%(request_id)s] %(name)s: %(message)s"


def set_request_id(value: str) -> None:
    _request_id.set(value)


def get_request_id() -> str:
    return _request_id.get()


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003 - logging API
        record.request_id = get_request_id()
        return True


def configure_logging(level: str = "INFO") -> None:
    """Idempotent logging setup for the API process."""

    root = logging.getLogger()
    if getattr(root, "_trend_detective_configured", False):
        root.setLevel(level)
        return

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    handler.addFilter(_RequestIdFilter())
    root.handlers = [handler]
    root.setLevel(level)
    root._trend_detective_configured = True  # type: ignore[attr-defined]
