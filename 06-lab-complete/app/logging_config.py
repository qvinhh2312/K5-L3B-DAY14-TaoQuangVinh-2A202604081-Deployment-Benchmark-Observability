"""
Structured logging: mỗi dòng log của app là một JSON object.

Cách dùng:
    logger.info("request", extra={"fields": {"path": "/ask", "status": 200}})
"""
import json
import logging
import sys
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """Ghép cả dòng log thành dict rồi json.dumps một lần, nên luôn escape đúng."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        payload.update(getattr(record, "fields", {}))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    # force=True: thay mọi cấu hình logging đã có, kể cả cấu hình ngầm do thư viện tạo ra
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
