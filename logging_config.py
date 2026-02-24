#!/usr/bin/env python3
"""
logging_config.py — Structured Logging
========================================
Configures structured JSON or text logging for the application.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

import config


class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "user"):
            log_entry["user"] = record.user
        if hasattr(record, "action"):
            log_entry["action"] = record.action
        if hasattr(record, "ip"):
            log_entry["ip"] = record.ip
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        return json.dumps(log_entry, default=str)


def setup_logging() -> None:
    """Configure the root logger based on config settings."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))

    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    if config.LOG_FORMAT == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        ))
    root.addHandler(handler)

    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
