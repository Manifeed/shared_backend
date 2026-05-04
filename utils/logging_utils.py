from __future__ import annotations

from collections.abc import Iterable, Mapping
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import logging
from logging.config import dictConfig
import os
from time import perf_counter
from typing import Any, Callable
from uuid import uuid4

from fastapi import Request, Response


REQUEST_ID_HEADER = "x-request-id"
DEFAULT_REQUEST_LOG_SKIP_PATHS = frozenset(
    {
        "/internal/health",
        "/internal/ready",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
)


@dataclass(frozen=True)
class LogContext:
    request_id: str
    service_name: str


RequestLogExtraFieldsFactory = Callable[
    [Request, Response | None, int],
    Mapping[str, Any] | None,
]


_log_context: ContextVar[LogContext | None] = ContextVar(
    "shared_backend_log_context",
    default=None,
)


def begin_log_context(*, request_id: str, service_name: str) -> object:
    return _log_context.set(
        LogContext(
            request_id=request_id,
            service_name=service_name,
        )
    )


def end_log_context(token: object) -> None:
    _log_context.reset(token)


def get_log_context() -> LogContext | None:
    return _log_context.get()


def get_request_id() -> str | None:
    context = get_log_context()
    if context is None:
        return None
    return context.request_id


def resolve_request_id(request: Request) -> str:
    header_value = (request.headers.get(REQUEST_ID_HEADER) or "").strip()
    if header_value:
        return header_value[:128]
    return uuid4().hex


def configure_service_logging(service_name: str) -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO"
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": JsonLogFormatter,
                    "service_name": service_name,
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {
                "handlers": ["default"],
                "level": log_level,
            },
            "loggers": {
                "uvicorn.access": {
                    "handlers": ["default"],
                    "level": "WARNING",
                    "propagate": False,
                },
                "uvicorn.error": {
                    "handlers": ["default"],
                    "level": log_level,
                    "propagate": False,
                },
                "uvicorn": {
                    "handlers": ["default"],
                    "level": log_level,
                    "propagate": False,
                },
            },
        }
    )


def create_request_logging_middleware(
    *,
    service_name: str,
    route_class: str,
    logger_name: str | None = None,
    skip_paths: Iterable[str] | None = None,
    extra_fields_factory: RequestLogExtraFieldsFactory | None = None,
):
    logger = logging.getLogger(logger_name or f"manifeed.{service_name}")
    ignored_paths = frozenset(skip_paths or DEFAULT_REQUEST_LOG_SKIP_PATHS)

    async def request_logging_middleware(request: Request, call_next):
        request_id = resolve_request_id(request)
        token = begin_log_context(
            request_id=request_id,
            service_name=service_name,
        )
        request.state.request_id = request_id

        started_at = perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            response.headers.setdefault("X-Request-ID", request_id)
            return response
        finally:
            latency_ms = max(0, round((perf_counter() - started_at) * 1000))
            if request.url.path not in ignored_paths:
                payload: dict[str, Any] = {
                    "event": "http_request",
                    "route_class": route_class,
                    "method": request.method,
                    "path": request.url.path,
                    "path_template": _resolve_route_path_template(request),
                    "query_keys": sorted(set(request.query_params.keys())),
                    "status_code": response.status_code if response is not None else 500,
                    "latency_ms": latency_ms,
                }
                if extra_fields_factory is not None:
                    extra_fields = extra_fields_factory(request, response, latency_ms) or {}
                    payload.update(dict(extra_fields))
                logger.info(payload)
            end_log_context(token)

    return request_logging_middleware


class JsonLogFormatter(logging.Formatter):
    def __init__(self, *, service_name: str) -> None:
        super().__init__()
        self._service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "service": self._service_name,
            "logger": record.name,
        }

        context = get_log_context()
        if context is not None:
            payload["request_id"] = context.request_id

        if isinstance(record.msg, Mapping) and not record.args:
            payload.update(_json_safe_value(dict(record.msg)))
        else:
            payload["message"] = record.getMessage()

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(
            payload,
            default=str,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )


def _resolve_route_path_template(request: Request) -> str:
    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    if isinstance(route_path, str) and route_path:
        return route_path
    return request.url.path


def _json_safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Mapping):
        return {
            str(key): _json_safe_value(item_value)
            for key, item_value in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe_value(item) for item in value]
    return str(value)
