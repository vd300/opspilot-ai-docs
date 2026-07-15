import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key in (
            "request_id",
            "investigation_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "node",
            "route",
            "active_agent",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(settings: Settings) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())

    if any(getattr(handler, "_opspilot_json", False) for handler in root_logger.handlers):
        return

    handler = logging.StreamHandler()
    handler._opspilot_json = True  # type: ignore[attr-defined]
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)
