from __future__ import annotations

from dataclasses import dataclass
import os
from time import perf_counter
from typing import Any

import httpx

from shared_backend.security.internal_service_auth import (
    build_internal_service_headers,
    read_internal_service_token,
)
from shared_backend.utils.logging_utils import REQUEST_ID_HEADER, get_request_id


@dataclass(frozen=True)
class ServiceClientConfig:
    base_url: str
    internal_token: str | None
    timeout_seconds: float
    service_name: str


@dataclass(frozen=True)
class ServiceRequestTrace:
    service: str
    method: str
    path: str
    status: int | None
    latency_ms: int
    outcome: str
    error: str | None = None


def build_service_config(
    *,
    base_url_env: str,
    timeout_env: str,
    default_timeout_seconds: float,
    service_name: str,
    env: dict[str, str] | None = None,
) -> ServiceClientConfig | None:
    environment = env or os.environ
    base_url = environment.get(base_url_env, "").strip().rstrip("/")
    if not base_url:
        return None
    return ServiceClientConfig(
        base_url=base_url,
        internal_token=read_internal_service_token(environment),
        timeout_seconds=resolve_timeout_seconds(environment.get(timeout_env), default_timeout_seconds),
        service_name=service_name,
    )


def build_internal_headers(config: ServiceClientConfig) -> dict[str, str]:
    headers = build_internal_service_headers(config.internal_token)
    request_id = get_request_id()
    if request_id:
        headers[REQUEST_ID_HEADER] = request_id
    return headers


def request_service(
    *,
    config: ServiceClientConfig,
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    http_client: httpx.Client | None = None,
    app_error_factory: Any,
    upstream_error_factory: Any,
    trace_callback: Any | None = None,
) -> httpx.Response:
    started_at = perf_counter()
    request_url = f"{config.base_url}{path}"
    try:
        if http_client is not None:
            response = http_client.request(
                method,
                request_url,
                params=compact_params(params),
                json=json,
                headers=build_internal_headers(config),
                timeout=config.timeout_seconds,
            )
        else:
            with httpx.Client(timeout=config.timeout_seconds) as client:
                response = client.request(
                    method,
                    request_url,
                    params=compact_params(params),
                    json=json,
                    headers=build_internal_headers(config),
                )
    except httpx.HTTPError as exception:
        emit_trace(
            trace_callback,
            ServiceRequestTrace(
                service=config.service_name.lower(),
                method=method,
                path=path,
                status=None,
                latency_ms=elapsed_milliseconds(started_at),
                outcome="network_error",
                error=str(exception),
            ),
        )
        raise upstream_error_factory(f"{config.service_name} service is unavailable") from exception
    emit_trace(
        trace_callback,
        ServiceRequestTrace(
            service=config.service_name.lower(),
            method=method,
            path=path,
            status=response.status_code,
            latency_ms=elapsed_milliseconds(started_at),
            outcome="ok" if response.status_code < 400 else "http_error",
            error=None if response.status_code < 400 else f"HTTP {response.status_code}",
        ),
    )
    raise_for_service_error(
        response,
        service_name=config.service_name,
        app_error_factory=app_error_factory,
        upstream_error_factory=upstream_error_factory,
    )
    return response


def raise_for_service_error(
    response: httpx.Response,
    *,
    service_name: str,
    app_error_factory: Any,
    upstream_error_factory: Any,
) -> None:
    if response.status_code < 400:
        return
    try:
        payload = response.json()
    except ValueError as exception:
        raise upstream_error_factory(
            f"{service_name} service returned HTTP {response.status_code}"
        ) from exception
    if isinstance(payload, dict):
        raise app_error_factory(
            str(payload.get("message") or f"{service_name} service error"),
            status_code=response.status_code,
            code=str(payload.get("code") or f"{service_name.lower()}_service_error"),
            details=payload.get("details"),
        )
    raise upstream_error_factory(f"{service_name} service returned HTTP {response.status_code}")


def require_service_client(
    client: Any | None,
    *,
    env_name: str,
    upstream_error_factory: Any,
) -> Any:
    if client is None:
        raise upstream_error_factory(f"{env_name} is not configured")
    return client


def compact_params(params: dict[str, Any] | None) -> dict[str, Any] | None:
    if params is None:
        return None
    return {key: value for key, value in params.items() if value is not None}


def resolve_timeout_seconds(raw_value: str | None, default_value: float) -> float:
    try:
        parsed = float(raw_value or default_value)
    except ValueError:
        return default_value
    return parsed if parsed > 0 else default_value


def emit_trace(trace_callback: Any | None, trace: ServiceRequestTrace) -> None:
    if trace_callback is not None:
        trace_callback(trace)


def elapsed_milliseconds(started_at: float) -> int:
    return max(0, round((perf_counter() - started_at) * 1000))
