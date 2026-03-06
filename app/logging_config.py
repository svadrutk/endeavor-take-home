import logging
import os
import sys
import structlog
from typing import Any
from structlog.types import EventDict


def get_environment_context() -> dict:
    """Get environment and deployment context for logging."""
    return {
        "app": "poketracker",
        "version": os.getenv("SERVICE_VERSION", "0.0.1"),
        "commit_hash": os.getenv("COMMIT_SHA", os.getenv("GIT_COMMIT", "unknown")),
        "environment": os.getenv("ENVIRONMENT", os.getenv("NODE_ENV", "development")),
        "region": os.getenv("REGION", "local"),
        "instance_id": os.getenv("HOSTNAME", "local"),
    }


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog with JSON output for production and human-readable for dev."""
    
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    env_context = get_environment_context()
    
    def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
        """Add application context to all log entries."""
        event_dict["app"] = env_context["app"]
        event_dict["version"] = env_context["version"]
        event_dict["commit_hash"] = env_context["commit_hash"]
        event_dict["environment"] = env_context["environment"]
        event_dict["region"] = env_context["region"]
        return event_dict
    
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            add_app_context,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
            if os.getenv("ENVIRONMENT", "development") == "production"
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """Get a configured structlog logger."""
    return structlog.get_logger(name)
