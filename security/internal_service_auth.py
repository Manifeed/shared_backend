from __future__ import annotations

import os
import secrets
from collections.abc import Callable, Mapping

from fastapi import Request

from shared_backend.errors.custom_exceptions import InternalServiceAuthError
from shared_backend.utils.environment import is_local_environment


INTERNAL_SERVICE_TOKEN_HEADER = "x-manifeed-internal-token"
INTERNAL_SERVICE_TOKENS_ENV = "INTERNAL_SERVICE_TOKENS"

InternalServiceAuthErrorFactory = Callable[[str | None], Exception]


def require_internal_service_token(
    request: Request,
    *,
    env: Mapping[str, str] | None = None,
    error_factory: InternalServiceAuthErrorFactory | None = None,
) -> None:
    environment = env or os.environ
    validate_internal_service_token_configuration(env=environment, error_factory=error_factory)
    accepted_tokens = read_internal_service_tokens(environment)
    if not accepted_tokens and is_local_environment(environment):
        return
    received_token = request.headers.get(INTERNAL_SERVICE_TOKEN_HEADER, "").strip()
    if not received_token or not any(
        secrets.compare_digest(received_token, expected_token)
        for expected_token in accepted_tokens
    ):
        raise _build_internal_service_auth_error(None, error_factory)


def validate_internal_service_token_configuration(
    *,
    env: Mapping[str, str] | None = None,
    error_factory: InternalServiceAuthErrorFactory | None = None,
) -> None:
    environment = env or os.environ
    accepted_tokens = read_internal_service_tokens(environment)
    if not accepted_tokens:
        if is_local_environment(environment):
            return
        raise _build_internal_service_auth_error(
            "INTERNAL_SERVICE_TOKEN or INTERNAL_SERVICE_TOKENS must be configured",
            error_factory,
        )
    if not is_local_environment(environment):
        for expected_token in accepted_tokens:
            if len(expected_token) < 32:
                raise _build_internal_service_auth_error(
                    "INTERNAL_SERVICE_TOKEN is too weak",
                    error_factory,
                )


def read_internal_service_token(env: Mapping[str, str] | None = None) -> str | None:
    accepted_tokens = read_internal_service_tokens(env)
    if accepted_tokens:
        return accepted_tokens[0]
    return None


def read_internal_service_tokens(env: Mapping[str, str] | None = None) -> tuple[str, ...]:
    environment = env or os.environ
    raw_tokens = environment.get(INTERNAL_SERVICE_TOKENS_ENV, "")
    parsed_tokens = [
        candidate.strip()
        for candidate in raw_tokens.replace("\n", ",").split(",")
        if candidate.strip()
    ]
    fallback_token = environment.get("INTERNAL_SERVICE_TOKEN", "").strip()
    if fallback_token:
        parsed_tokens.insert(0, fallback_token)
    # Keep caller-defined order stable while dropping duplicates.
    return tuple(dict.fromkeys(parsed_tokens))


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
