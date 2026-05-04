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
from shared_backend.domain.current_user import AuthenticatedUserContext
from shared_backend.errors.app_error import AppError, UpstreamServiceError
from shared_backend.schemas.account.account_schema import (
    AccountMeRead,
    AccountPasswordUpdateRead,
    AccountPasswordUpdateRequestSchema,
    AccountProfileUpdateRead,
    AccountProfileUpdateRequestSchema,
    UserApiKeyCreateRead,
    UserApiKeyCreateRequestSchema,
    UserApiKeyDeleteRead,
    UserApiKeyListRead,
)
from shared_backend.schemas.admin.admin_user_schema import (
    AdminUserListRead,
    AdminUserRead,
    AdminUserUpdateRequestSchema,
)
from shared_backend.schemas.auth.auth_schema import UserRole
from shared_backend.schemas.internal.auth_service_schema import InternalSessionTokenRequest
from shared_backend.schemas.internal.service_schema import InternalServiceHealthRead
from shared_backend.schemas.internal.user_service_schema import (
    InternalAccountPasswordUpdateRequest,
    InternalAccountProfileUpdateRequest,
    InternalAdminUserUpdateRequest,
    InternalApiKeyCreateRequest,
    InternalCurrentUserPayload,
)


INTERNAL_SESSION_TOKEN_HEADER = "x-manifeed-session-token"

INTERNAL_CURRENT_USER_ID_HEADER = "x-manifeed-acting-user-id"
INTERNAL_CURRENT_USER_EMAIL_HEADER = "x-manifeed-acting-user-email"
INTERNAL_CURRENT_USER_ROLE_HEADER = "x-manifeed-acting-user-role"
INTERNAL_CURRENT_USER_IS_ACTIVE_HEADER = "x-manifeed-acting-user-is-active"
INTERNAL_CURRENT_USER_API_ACCESS_ENABLED_HEADER = "x-manifeed-acting-user-api-access-enabled"
INTERNAL_CURRENT_USER_SESSION_EXPIRES_AT_HEADER = "x-manifeed-acting-user-session-expires-at"


class UserServiceNetworkingClient:
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
    ) -> UserServiceNetworkingClient | None:
        config = build_service_config(
            base_url_env="USER_SERVICE_URL",
            timeout_env="USER_SERVICE_TIMEOUT_SECONDS",
            default_timeout_seconds=5.0,
            service_name="User",
        )
        if config is None:
            return None
        return cls(config, http_client=http_client, trace_callback=trace_callback)

    def read_account_me(self, *, session_token: str) -> AccountMeRead:
        response = self._post(
            "/internal/users/account/me",
            json={"payload": InternalSessionTokenRequest(session_token=session_token).model_dump(mode="json")},
        )
        return AccountMeRead.model_validate(response.json())

    def update_account_profile(
        self,
        *,
        session_token: str,
        payload: AccountProfileUpdateRequestSchema,
    ) -> AccountProfileUpdateRead:
        response = self._patch(
            "/internal/users/account/me",
            json={
                "payload": InternalAccountProfileUpdateRequest(
                    session_token=session_token,
                    payload=payload,
                ).model_dump(mode="json", exclude_none=True)
            },
        )
        return AccountProfileUpdateRead.model_validate(response.json())

    def update_account_password(
        self,
        *,
        session_token: str,
        payload: AccountPasswordUpdateRequestSchema,
    ) -> AccountPasswordUpdateRead:
        response = self._patch(
            "/internal/users/account/password",
            json={
                "payload": InternalAccountPasswordUpdateRequest(
                    session_token=session_token,
                    payload=payload,
                ).model_dump(mode="json")
            },
        )
        return AccountPasswordUpdateRead.model_validate(response.json())

    def read_account_api_keys(self, *, session_token: str) -> UserApiKeyListRead:
        response = self._get(
            "/internal/users/account/api-keys",
            params={},
            headers={INTERNAL_SESSION_TOKEN_HEADER: session_token},
        )
        return UserApiKeyListRead.model_validate(response.json())

    def create_account_api_key(
        self,
        *,
        session_token: str,
        payload: UserApiKeyCreateRequestSchema,
    ) -> UserApiKeyCreateRead:
        response = self._post(
            "/internal/users/account/api-keys",
            json={
                "payload": InternalApiKeyCreateRequest(
                    session_token=session_token,
                    payload=payload,
                ).model_dump(mode="json")
            },
        )
        return UserApiKeyCreateRead.model_validate(response.json())

    def delete_account_api_key(
        self,
        *,
        session_token: str,
        api_key_id: int,
    ) -> UserApiKeyDeleteRead:
        response = self._delete(
            f"/internal/users/account/api-keys/{api_key_id}",
            headers={INTERNAL_SESSION_TOKEN_HEADER: session_token},
        )
        return UserApiKeyDeleteRead.model_validate(response.json())

    def read_admin_users(
        self,
        *,
        current_user: AuthenticatedUserContext,
        role: UserRole | None,
        is_active: bool | None,
        api_access_enabled: bool | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> AdminUserListRead:
        response = self._get(
            "/internal/users/admin/users",
            params={
                "role": role,
                "is_active": is_active,
                "api_access_enabled": api_access_enabled,
                "search": search,
                "limit": limit,
                "offset": offset,
            },
            headers=_current_user_headers(current_user),
        )
        return AdminUserListRead.model_validate(response.json())

    def update_admin_user(
        self,
        *,
        current_user: AuthenticatedUserContext,
        user_id: int,
        payload: AdminUserUpdateRequestSchema,
    ) -> AdminUserRead:
        response = self._patch(
            f"/internal/users/admin/users/{user_id}",
            json={
                "payload": InternalAdminUserUpdateRequest(
                    current_user=_current_user_payload(current_user),
                    payload=payload,
                ).model_dump(mode="json", exclude_none=True)
            },
        )
        return AdminUserRead.model_validate(response.json())

    def read_internal_health(self) -> InternalServiceHealthRead:
        response = self._request("GET", "/internal/health", params=None, json=None, headers=None)
        return InternalServiceHealthRead.model_validate(response.json())

    def _get(self, path: str, *, params: dict[str, Any], headers: dict[str, str] | None = None) -> httpx.Response:
        return self._request("GET", path, params=params, json=None, headers=headers)

    def _post(self, path: str, *, json: dict[str, Any]) -> httpx.Response:
        return self._request("POST", path, params=None, json=json, headers=None)

    def _patch(self, path: str, *, json: dict[str, Any]) -> httpx.Response:
        return self._request("PATCH", path, params=None, json=json, headers=None)

    def _delete(self, path: str, *, headers: dict[str, str] | None = None) -> httpx.Response:
        return self._request("DELETE", path, params=None, json=None, headers=headers)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None,
        json: dict[str, Any] | None,
        headers: dict[str, str] | None,
    ) -> httpx.Response:
        return request_service(
            config=self._config,
            method=method,
            path=path,
            params=params,
            json=json,
            headers=headers,
            http_client=self._http_client,
            app_error_factory=AppError,
            upstream_error_factory=UpstreamServiceError,
            trace_callback=self._trace_callback,
        )


def user_service_client_from_env(
    *,
    http_client: httpx.Client | None = None,
    trace_callback: Callable[[ServiceRequestTrace], None] | None = None,
) -> UserServiceNetworkingClient | None:
    return UserServiceNetworkingClient.from_env(http_client=http_client, trace_callback=trace_callback)


def get_required_user_service_client(
    *,
    http_client: httpx.Client | None = None,
    trace_callback: Callable[[ServiceRequestTrace], None] | None = None,
) -> UserServiceNetworkingClient:
    return require_service_client(
        user_service_client_from_env(http_client=http_client, trace_callback=trace_callback),
        env_name="USER_SERVICE_URL",
        upstream_error_factory=UpstreamServiceError,
    )


def _current_user_payload(current_user: AuthenticatedUserContext) -> InternalCurrentUserPayload:
    return InternalCurrentUserPayload(
        user_id=current_user.user_id,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        api_access_enabled=current_user.api_access_enabled,
        session_expires_at=current_user.session_expires_at,
    )


def _current_user_headers(current_user: AuthenticatedUserContext) -> dict[str, str]:
    return {
        INTERNAL_CURRENT_USER_ID_HEADER: str(current_user.user_id),
        INTERNAL_CURRENT_USER_EMAIL_HEADER: current_user.email,
        INTERNAL_CURRENT_USER_ROLE_HEADER: current_user.role,
        INTERNAL_CURRENT_USER_IS_ACTIVE_HEADER: "true" if current_user.is_active else "false",
        INTERNAL_CURRENT_USER_API_ACCESS_ENABLED_HEADER: "true" if current_user.api_access_enabled else "false",
        INTERNAL_CURRENT_USER_SESSION_EXPIRES_AT_HEADER: current_user.session_expires_at.isoformat(),
    }
