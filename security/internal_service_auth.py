from __future__ import annotations

import os
import secrets
from collections.abc import Callable, Mapping

from fastapi import Request

from shared_backend.errors.custom_exceptions import InternalServiceAuthError
from shared_backend.utils.environment import is_local_environment


INTERNAL_SERVICE_TOKEN_HEADER = "x-manifeed-internal-token"

InternalServiceAuthErrorFactory = Callable[[str | None], Exception]


def require_internal_service_token(
    request: Request,
    *,
    env: Mapping[str, str] | None = None,
    error_factory: InternalServiceAuthErrorFactory | None = None,
) -> None:
    environment = env or os.environ
    validate_internal_service_token_configuration(env=environment, error_factory=error_factory)
    expected_token = read_internal_service_token(environment)
    if not expected_token and is_local_environment(environment):
        return
    received_token = request.headers.get(INTERNAL_SERVICE_TOKEN_HEADER, "").strip()
    if not received_token or not secrets.compare_digest(received_token, expected_token or ""):
        raise _build_internal_service_auth_error(None, error_factory)


def validate_internal_service_token_configuration(
    *,
    env: Mapping[str, str] | None = None,
    error_factory: InternalServiceAuthErrorFactory | None = None,
) -> None:
    environment = env or os.environ
    expected_token = read_internal_service_token(environment)
    if not expected_token:
        if is_local_environment(environment):
            return
        raise _build_internal_service_auth_error(
            "INTERNAL_SERVICE_TOKEN is not configured",
            error_factory,
        )
    if len(expected_token) < 32 and not is_local_environment(environment):
        raise _build_internal_service_auth_error(
            "INTERNAL_SERVICE_TOKEN is too weak",
            error_factory,
        )


def read_internal_service_token(env: Mapping[str, str] | None = None) -> str | None:
    environment = env or os.environ
    token = environment.get("INTERNAL_SERVICE_TOKEN", "").strip()
    return token or None


def build_internal_service_headers(
    internal_token: str | None,
    *,
    content_type: str = "application/json",
) -> dict[str, str]:
    headers = {"Content-Type": content_type}
    if internal_token:
        headers[INTERNAL_SERVICE_TOKEN_HEADER] = internal_token
    return headers


def _build_internal_service_auth_error(
    message: str | None,
    error_factory: InternalServiceAuthErrorFactory | None,
) -> Exception:
    if error_factory is None:
        return InternalServiceAuthError(message)
    return error_factory(message)
