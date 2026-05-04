from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from shared_backend.clients import user_service_networking_client
from shared_backend.clients.service_http_client import ServiceClientConfig
from shared_backend.clients.user_service_networking_client import (
    INTERNAL_CURRENT_USER_API_ACCESS_ENABLED_HEADER,
    INTERNAL_CURRENT_USER_EMAIL_HEADER,
    INTERNAL_CURRENT_USER_ID_HEADER,
    INTERNAL_CURRENT_USER_IS_ACTIVE_HEADER,
    INTERNAL_CURRENT_USER_ROLE_HEADER,
    INTERNAL_CURRENT_USER_SESSION_EXPIRES_AT_HEADER,
    INTERNAL_SESSION_TOKEN_HEADER,
    UserServiceNetworkingClient,
)
from shared_backend.domain.current_user import AuthenticatedUserContext
from shared_backend.schemas.account.account_schema import (
    AccountMeRead,
    UserApiKeyCreateRead,
    UserApiKeyCreateRequestSchema,
    UserApiKeyDeleteRead,
)
from shared_backend.schemas.admin.admin_user_schema import AdminUserUpdateRequestSchema


def _config() -> ServiceClientConfig:
    return ServiceClientConfig(
        base_url="http://user-service:8000",
        internal_token="x" * 32,
        timeout_seconds=5.0,
        service_name="User",
    )


def _session_token() -> str:
    return "msess_example"


def _current_user() -> AuthenticatedUserContext:
    return AuthenticatedUserContext(
        user_id=7,
        email="admin@example.com",
        role="admin",
        is_active=True,
        api_access_enabled=True,
        session_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )


def test_read_account_me_wraps_session_token_payload(monkeypatch, sample_auth_user) -> None:
    seen: dict[str, object] = {}

    def fake_request_service(**kwargs) -> httpx.Response:
        seen.update(kwargs)
        return httpx.Response(
            200,
            json={"user": sample_auth_user.model_dump(mode="json")},
            request=httpx.Request("POST", "http://user-service:8000/internal/users/account/me"),
        )

    monkeypatch.setattr(user_service_networking_client, "request_service", fake_request_service)
    client = UserServiceNetworkingClient(_config())
    session_token = _session_token()

    response = client.read_account_me(session_token=session_token)

    assert isinstance(response, AccountMeRead)
    assert seen["path"] == "/internal/users/account/me"
    assert seen["json"] == {
        "payload": {"session_token": session_token}
    }


def test_read_account_api_keys_passes_session_token_header(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_request_service(**kwargs) -> httpx.Response:
        seen.update(kwargs)
        return httpx.Response(
            200,
            json={"items": []},
            request=httpx.Request("GET", "http://user-service:8000/internal/users/account/api-keys"),
        )

    monkeypatch.setattr(user_service_networking_client, "request_service", fake_request_service)
    client = UserServiceNetworkingClient(_config())
    session_token = _session_token()

    response = client.read_account_api_keys(session_token=session_token)

    assert response.items == []
    assert seen["method"] == "GET"
    assert seen["path"] == "/internal/users/account/api-keys"
    assert seen["headers"] == {INTERNAL_SESSION_TOKEN_HEADER: session_token}


def test_create_account_api_key_wraps_internal_request_payload(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_request_service(**kwargs) -> httpx.Response:
        seen.update(kwargs)
        return httpx.Response(
            200,
            json={
                "api_key": "mf_test_key",
                "api_key_info": {
                    "id": 9,
                    "label": "smoke",
                    "worker_type": "rss_scrapper",
                    "worker_name": "user-rss_scrapper-1",
                    "key_prefix": "mf_1234",
                    "last_used_at": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            },
            request=httpx.Request("POST", "http://user-service:8000/internal/users/account/api-keys"),
        )

    monkeypatch.setattr(user_service_networking_client, "request_service", fake_request_service)
    client = UserServiceNetworkingClient(_config())
    session_token = _session_token()
    payload = UserApiKeyCreateRequestSchema(label="smoke", worker_type="rss_scrapper")

    response = client.create_account_api_key(session_token=session_token, payload=payload)

    assert isinstance(response, UserApiKeyCreateRead)
    assert seen["path"] == "/internal/users/account/api-keys"
    assert seen["json"] == {
        "payload": {
            "session_token": session_token,
            "payload": payload.model_dump(mode="json"),
        }
    }


def test_delete_account_api_key_passes_session_token_header(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_request_service(**kwargs) -> httpx.Response:
        seen.update(kwargs)
        return httpx.Response(
            200,
            json={"ok": True},
            request=httpx.Request(
                "DELETE",
                "http://user-service:8000/internal/users/account/api-keys/9",
            ),
        )

    monkeypatch.setattr(user_service_networking_client, "request_service", fake_request_service)
    client = UserServiceNetworkingClient(_config())
    session_token = _session_token()

    response = client.delete_account_api_key(session_token=session_token, api_key_id=9)

    assert isinstance(response, UserApiKeyDeleteRead)
    assert seen["method"] == "DELETE"
    assert seen["path"] == "/internal/users/account/api-keys/9"
    assert seen["headers"] == {INTERNAL_SESSION_TOKEN_HEADER: session_token}


def test_read_admin_users_passes_filters_and_current_user_headers(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_request_service(**kwargs) -> httpx.Response:
        seen.update(kwargs)
        return httpx.Response(
            200,
            json={"items": [], "total": 0, "active_total": 0, "limit": 25, "offset": 10},
            request=httpx.Request("GET", "http://user-service:8000/internal/users/admin/users"),
        )

    monkeypatch.setattr(user_service_networking_client, "request_service", fake_request_service)
    client = UserServiceNetworkingClient(_config())
    current_user = _current_user()

    response = client.read_admin_users(
        current_user=current_user,
        role="admin",
        is_active=True,
        api_access_enabled=True,
        search="bob",
        limit=25,
        offset=10,
    )

    assert response.limit == 25
    assert seen["method"] == "GET"
    assert seen["path"] == "/internal/users/admin/users"
    assert seen["params"] == {
        "role": "admin",
        "is_active": True,
        "api_access_enabled": True,
        "search": "bob",
        "limit": 25,
        "offset": 10,
    }
    assert seen["headers"] == {
        INTERNAL_CURRENT_USER_ID_HEADER: str(current_user.user_id),
        INTERNAL_CURRENT_USER_EMAIL_HEADER: current_user.email,
        INTERNAL_CURRENT_USER_ROLE_HEADER: current_user.role,
        INTERNAL_CURRENT_USER_IS_ACTIVE_HEADER: "true",
        INTERNAL_CURRENT_USER_API_ACCESS_ENABLED_HEADER: "true",
        INTERNAL_CURRENT_USER_SESSION_EXPIRES_AT_HEADER: current_user.session_expires_at.isoformat(),
    }


def test_update_admin_user_wraps_current_user_and_payload(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_request_service(**kwargs) -> httpx.Response:
        seen.update(kwargs)
        return httpx.Response(
            200,
            json={
                "id": 9,
                "email": "user@example.com",
                "pseudo": "user",
                "role": "user",
                "is_active": True,
                "api_access_enabled": False,
            },
            request=httpx.Request("PATCH", "http://user-service:8000/internal/users/admin/users/9"),
        )

    monkeypatch.setattr(user_service_networking_client, "request_service", fake_request_service)
    client = UserServiceNetworkingClient(_config())
    current_user = _current_user()
    payload = AdminUserUpdateRequestSchema(api_access_enabled=False)

    response = client.update_admin_user(current_user=current_user, user_id=9, payload=payload)

    assert response.id == 9
    assert seen["path"] == "/internal/users/admin/users/9"
    assert seen["json"]["payload"]["current_user"]["user_id"] == current_user.user_id
    assert seen["json"]["payload"]["current_user"]["email"] == current_user.email
    assert seen["json"]["payload"]["current_user"]["role"] == current_user.role
    assert seen["json"]["payload"]["payload"] == {"api_access_enabled": False}
