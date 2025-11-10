"""Structured logging helpers for BlazeORM."""

from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar
from typing import Any, Iterable, Mapping, MutableMapping, Optional

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True


def configure_logging(level: int = logging.INFO) -> None:
    logger = logging.getLogger("blazeorm")
    if logger.handlers:
        return
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(correlation_id)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationIdFilter())
    logger.addHandler(handler)
    logger.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(f"blazeorm.{name}")


def set_correlation_id(value: Optional[str] = None) -> str:
    token = value or str(uuid.uuid4())
    _correlation_id.set(token)
    return token


def get_correlation_id() -> str:
    cid = _correlation_id.get()
    if cid is None:
        cid = set_correlation_id()
    return cid


def time_call(name: str, logger: logging.Logger, *, sql: str | None = None, params: Iterable[Any] | None = None, threshold_ms: int = 100):
    start = time.monotonic()

    class Timer:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            elapsed_ms = (time.monotonic() - start) * 1000
            level = logging.WARNING if elapsed_ms >= threshold_ms else logging.DEBUG
            extra = {"sql": sql, "params": params, "elapsed_ms": elapsed_ms}
            logger.log(level, "%s took %.2fms", name, elapsed_ms, extra=extra)

    return Timer()
