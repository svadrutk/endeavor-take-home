import time
import uuid
from collections.abc import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.logging_config import get_environment_context


class WideEventMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        wide_event = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "user_id": request.headers.get("X-User-ID"),
            "user_role": None,
            **get_environment_context(),
        }

        request.state.wide_event = wide_event

        try:
            response = await call_next(request)

            wide_event["status_code"] = response.status_code
            wide_event["outcome"] = "success" if response.status_code < 400 else "error"

            return response

        except Exception as exc:
            wide_event["status_code"] = 500
            wide_event["outcome"] = "error"
            wide_event["error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
            }
            raise

        finally:
            duration_ms = (time.time() - start_time) * 1000
            wide_event["duration_ms"] = round(duration_ms, 2)

            logger = structlog.get_logger()
            if wide_event.get("outcome") == "error":
                logger.error(wide_event)
            else:
                logger.info(wide_event)
