import contextvars
import json
import logging
import time
import uuid
from typing import Any, Dict

# Context variable to hold request-scoped tracking info (e.g. Request ID)
request_id_ctx = contextvars.ContextVar("request_id", default="")
ticket_id_ctx = contextvars.ContextVar("ticket_id", default="")

class StructuredJSONFormatter(logging.Formatter):
    """
    Structured logging formatter that outputs logs as JSON lines in production.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
            "ticket_id": ticket_id_ctx.get(),
        }
        
        # Include exception details if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        # Include extra fields passed using `extra={...}`
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
            
        return json.dumps(log_data)

def setup_logging(log_level: str = "INFO", app_env: str = "production"):
    """
    Configures root logger to use structured JSON logging or standard streaming logs.
    """
    root_logger = logging.getLogger()
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    handler = logging.StreamHandler()
    
    # In production, output structured JSON. In development, use a clean structured format.
    if app_env.lower() == "production":
        formatter = StructuredJSONFormatter()
    else:
        # Standard human-readable clean format with request context variables
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [ReqID: %(request_id)s] %(name)s: %(message)s"
        )
        # We hook into standard record factories to add context vars dynamically
        old_factory = logging.getLogRecordFactory()
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.request_id = request_id_ctx.get() or "N/A"
            return record
        logging.setLogRecordFactory(record_factory)

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
