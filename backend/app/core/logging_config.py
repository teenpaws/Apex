"""
Structured JSON logging for production.

Usage:
    from app.core.logging_config import configure_logging
    configure_logging(log_level=settings.LOG_LEVEL, json_logs=settings.JSON_LOGS)
"""

import logging
from datetime import datetime, timezone

from pythonjsonlogger.jsonlogger import JsonFormatter


class ApexJsonFormatter(JsonFormatter):
    """JSON log formatter that emits timestamp, level, logger, message."""

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = datetime.now(timezone.utc).isoformat()
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record.pop("levelname", None)
        log_record.pop("name", None)


def configure_logging(log_level: str = "INFO", json_logs: bool = False) -> None:
    """Configure root logger. Call once at application startup."""
    handler = logging.StreamHandler()
    if json_logs:
        handler.setFormatter(ApexJsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
        )
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        handlers=[handler],
        force=True,
    )
