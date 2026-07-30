"""Structured JSON logging for the herbal-oil runtime.

Emits one JSON object per log line so logs are machine-parseable and
correlatable by `run_id` / `step`. Falls back to a human-readable format when
structured logging is disabled via feature flags.
"""
from __future__ import annotations

import json
import logging
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_CONFIGURED: set[str] = set()

# Fixed set of standard LogRecord attributes. Anything else attached to a
# record (via ``extra=``) is treated as a structured field and serialised.
_STD_RECORD_ATTRS = {
    "args", "asctime", "created", "exc_info", "exc_text", "filename",
    "funcName", "levelname", "levelno", "lineno", "message", "module",
    "msecs", "msg", "name", "pathname", "process", "processName",
    "relativeCreated", "stack_info", "thread", "threadName", "taskName",
    "event",  # our own convenience key, surfaced explicitly below
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JsonFormatter(logging.Formatter):
    """Formats LogRecords as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": _utc_now(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, value in vars(record).items():
            if key in _STD_RECORD_ATTRS or key.startswith("_"):
                continue
            payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class StructuredLogger:
    """Adapter that funnels arbitrary keyword fields into the stdlib ``extra``
    dict so the JsonFormatter emits them as structured fields.

    Usage mirrors a normal logger: ``log.info("event_name", key=value)``.
    """

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def __getattr__(self, item: str):
        return getattr(self._logger, item)

    def _emit(self, level: int, event: str, args: tuple, kwargs: dict) -> None:
        extra: dict[str, Any] = dict(kwargs.pop("extra", {}) or {})
        exc_info = kwargs.pop("exc_info", None)
        _reserved = {"args", "msg", "level", "name"}
        for key, value in kwargs.items():
            if key in _reserved:
                continue
            extra[key] = value
        extra.setdefault("event", event)
        self._logger.log(level, event, *args, extra=extra, exc_info=exc_info)

    def debug(self, event: str, *args, **kwargs) -> None:
        self._emit(logging.DEBUG, event, args, kwargs)

    def info(self, event: str, *args, **kwargs) -> None:
        self._emit(logging.INFO, event, args, kwargs)

    def warning(self, event: str, *args, **kwargs) -> None:
        self._emit(logging.WARNING, event, args, kwargs)

    def error(self, event: str, *args, **kwargs) -> None:
        self._emit(logging.ERROR, event, args, kwargs)

    def critical(self, event: str, *args, **kwargs) -> None:
        self._emit(logging.CRITICAL, event, args, kwargs)


def configure_logging(
    level: str = "INFO",
    *,
    log_dir: str | Path | None = None,
    structured: bool = True,
    run_id: str | None = None,
    force: bool = False,
) -> logging.Logger:
    """Idempotently configure the ``herbal_oil`` logger hierarchy."""
    root_name = "herbal_oil"
    key = f"{root_name}:{level}:{structured}:{log_dir}"
    if key in _CONFIGURED and not force:
        return logging.getLogger(root_name)
    logger = logging.getLogger(root_name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()
    logger.propagate = False

    formatter: logging.Formatter = (
        JsonFormatter() if structured
        else logging.Formatter("%(asctime)s %(levelname)-7s %(name)s %(message)s")
    )

    stream = logging.StreamHandler(sys.stderr)
    stream.setFormatter(formatter)
    logger.addHandler(stream)

    if log_dir is not None:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / "herbal_oil.log", encoding="utf-8")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    _CONFIGURED.add(key)
    return logger


def get_logger(name: str = "herbal_oil") -> StructuredLogger:
    configure_logging()
    return StructuredLogger(logging.getLogger(name))


def log_event(logger, event: str, **fields: Any) -> None:
    logger.info(event, **fields)


__all__ = ["configure_logging", "get_logger", "log_event", "JsonFormatter", "StructuredLogger"]