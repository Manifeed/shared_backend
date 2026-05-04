from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx

from shared_backend.clients.service_http_client import (
    ServiceClientConfig,
    ServiceRequestTrace,
    build_service_config,
    request_service,
    require_service_client,
)
from shared_backend.errors.app_error import AppError, UpstreamServiceError
from shared_backend.schemas.auth.auth_schema import (
    AuthLoginRequestSchema,
    AuthLogoutRead,
    AuthRegisterRead,
    AuthRegisterRequestSchema,
    AuthSessionRead,
)
from shared_backend.schemas.auth.session_schema import AuthLoginResult
from shared_backend.schemas.internal.auth_service_schema import InternalAuthLoginRead, InternalSessionTokenRequest
from shared_backend.schemas.internal.service_schema import InternalResolvedSessionRead, InternalServiceHealthRead


class AuthServiceNetworkingClient:
    def __init__(
        self,
        config: ServiceClientConfig,
        http_client: httpx.Client | None = None,
        trace_callback: Callable[[ServiceRequestTrace], None] | None = None,
    ) -> None:
        self._config = config
        self._http_client = http_client
        self._trace_callback = trace_callback

    @classmethod
    def from_env(
        cls,
        *,
        http_client: httpx.Client | None = None,
        trace_callback: Callable[[ServiceRequestTrace], None] | None = None,
    ) -> AuthServiceNetworkingClient | None:
        config = build_service_config(
            base_url_env="AUTH_SERVICE_URL",
            timeout_env="AUTH_SERVICE_TIMEOUT_SECONDS",
            default_timeout_seconds=5.0,
            service_name="Auth",
        )
        if config is None:
            return None
        return cls(config, http_client=http_client, trace_callback=trace_callback)

    def register(self, payload: AuthRegisterRequestSchema) -> AuthRegisterRead:
        response = self._post(
            "/internal/auth/register",
            json={"payload": payload.model_dump(mode="json")},
        )
        return AuthRegisterRead.model_validate(response.json())

    def login(self, payload: AuthLoginRequestSchema) -> AuthLoginResult:
        response = self._post(
            "/internal/auth/login",
            json={"payload": payload.model_dump(mode="json")},
        )
        result = InternalAuthLoginRead.model_validate(response.json())
        return AuthLoginResult(
            session_token=result.session_token,
            expires_at=result.expires_at,
            user=result.user,
        )

    def read_session(self, *, session_token: str) -> AuthSessionRead:
        response = self._post(
            "/internal/auth/session",
            json={"payload": InternalSessionTokenRequest(session_token=session_token).model_dump(mode="json")},
        )
        return AuthSessionRead.model_validate(response.json())

    def resolve_session(self, *, session_token: str) -> InternalResolvedSessionRead:
        response = self._post(
            "/internal/auth/resolve-session",
            json={"payload": InternalSessionTokenRequest(session_token=session_token).model_dump(mode="json")},
        )
        return InternalResolvedSessionRead.model_validate(response.json())

    def logout(self, *, session_token: str) -> AuthLogoutRead:
        response = self._post(
            "/internal/auth/logout",
            json={"payload": InternalSessionTokenRequest(session_token=session_token).model_dump(mode="json")},
        )
        return AuthLogoutRead.model_validate(response.json())

    def read_internal_health(self) -> InternalServiceHealthRead:
        response = request_service(
            config=self._config,
            method="GET",
            path="/internal/health",
            http_client=self._http_client,
            app_error_factory=AppError,
            upstream_error_factory=UpstreamServiceError,
            trace_callback=self._trace_callback,
        )
        return InternalServiceHealthRead.model_validate(response.json())

    def _post(self, path: str, *, json: dict[str, Any]) -> httpx.Response:
        return request_service(
            config=self._config,
            method="POST",
            path=path,
            json=json,
            http_client=self._http_client,
            app_error_factory=AppError,
            upstream_error_factory=UpstreamServiceError,
            trace_callback=self._trace_callback,
        )


def get_auth_service_client(
    *,
    http_client: httpx.Client | None = None,
    trace_callback: Callable[[ServiceRequestTrace], None] | None = None,
) -> AuthServiceNetworkingClient | None:
    return AuthServiceNetworkingClient.from_env(http_client=http_client, trace_callback=trace_callback)


def get_required_auth_service_client(
    *,
    http_client: httpx.Client | None = None,
    trace_callback: Callable[[ServiceRequestTrace], None] | None = None,
) -> AuthServiceNetworkingClient:
    return require_service_client(
        get_auth_service_client(http_client=http_client, trace_callback=trace_callback),
        env_name="AUTH_SERVICE_URL",
        upstream_error_factory=UpstreamServiceError,
    )
