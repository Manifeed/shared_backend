from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from shared_backend.clients import auth_service_networking_client
from shared_backend.clients.auth_service_networking_client import AuthServiceNetworkingClient
from shared_backend.clients.service_http_client import ServiceClientConfig
from shared_backend.schemas.auth.auth_schema import (
    AuthLoginRequestSchema,
    AuthRegisterRequestSchema,
)


def _config() -> ServiceClientConfig:
    return ServiceClientConfig(
        base_url="http://auth-service:8000",
        internal_token="x" * 32,
        timeout_seconds=5.0,
        service_name="Auth",
    )


def test_register_wraps_payload_for_internal_auth_service(monkeypatch, sample_auth_user) -> None:
    seen: dict[str, object] = {}

    def fake_request_service(**kwargs) -> httpx.Response:
        seen.update(kwargs)
        return httpx.Response(
            200,
            json={"user": sample_auth_user.model_dump(mode="json")},
            request=httpx.Request("POST", "http://auth-service:8000/internal/auth/register"),
        )

    monkeypatch.setattr(auth_service_networking_client, "request_service", fake_request_service)
    client = AuthServiceNetworkingClient(_config())
    payload = AuthRegisterRequestSchema(
        email="user@example.com",
        pseudo="dorn",
        password="Disburse4-Acclaim6-Mantra1-Juggling4",
    )

    response = client.register(payload)

    assert response.user.email == "user@example.com"
    assert seen["path"] == "/internal/auth/register"
    assert seen["json"] == {"payload": payload.model_dump(mode="json")}


def test_login_wraps_payload_for_internal_auth_service(monkeypatch, sample_auth_user) -> None:
    seen: dict[str, object] = {}
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    def fake_request_service(**kwargs) -> httpx.Response:
        seen.update(kwargs)
        return httpx.Response(
            200,
            json={
                "session_token": "session-token",
                "expires_at": expires_at.isoformat(),
                "user": sample_auth_user.model_dump(mode="json"),
            },
            request=httpx.Request("POST", "http://auth-service:8000/internal/auth/login"),
        )

    monkeypatch.setattr(auth_service_networking_client, "request_service", fake_request_service)
    client = AuthServiceNetworkingClient(_config())
    payload = AuthLoginRequestSchema(
        email="user@example.com",
        password="Disburse4-Acclaim6-Mantra1-Juggling4",
    )

    response = client.login(payload)

    assert response.session_token == "session-token"
    assert seen["path"] == "/internal/auth/login"
    assert seen["json"] == {"payload": payload.model_dump(mode="json")}


def test_resolve_session_wraps_session_token_payload(monkeypatch) -> None:
    seen: dict[str, object] = {}
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    def fake_request_service(**kwargs) -> httpx.Response:
        seen.update(kwargs)
        return httpx.Response(
            200,
            json={
                "user_id": 1,
                "email": "user@example.com",
                "role": "user",
                "is_active": True,
                "api_access_enabled": True,
                "session_expires_at": expires_at.isoformat(),
            },
            request=httpx.Request("POST", "http://auth-service:8000/internal/auth/resolve-session"),
        )

    monkeypatch.setattr(auth_service_networking_client, "request_service", fake_request_service)
    client = AuthServiceNetworkingClient(_config())

    response = client.resolve_session(session_token="session-token")

    assert response.user_id == 1
    assert seen["path"] == "/internal/auth/resolve-session"
    assert seen["json"] == {"payload": {"session_token": "session-token"}}


def test_read_session_wraps_session_token_payload(monkeypatch, sample_auth_user) -> None:
    seen: dict[str, object] = {}
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    def fake_request_service(**kwargs) -> httpx.Response:
        seen.update(kwargs)
        return httpx.Response(
            200,
            json={
                "expires_at": expires_at.isoformat(),
                "user": sample_auth_user.model_dump(mode="json"),
            },
            request=httpx.Request("POST", "http://auth-service:8000/internal/auth/session"),
        )

    monkeypatch.setattr(auth_service_networking_client, "request_service", fake_request_service)
    client = AuthServiceNetworkingClient(_config())

    response = client.read_session(session_token="session-token")

    assert response.user.email == "user@example.com"
    assert seen["path"] == "/internal/auth/session"
    assert seen["json"] == {"payload": {"session_token": "session-token"}}


def test_logout_wraps_session_token_payload(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_request_service(**kwargs) -> httpx.Response:
        seen.update(kwargs)
        return httpx.Response(
            200,
            json={"ok": True},
            request=httpx.Request("POST", "http://auth-service:8000/internal/auth/logout"),
        )

    monkeypatch.setattr(auth_service_networking_client, "request_service", fake_request_service)
    client = AuthServiceNetworkingClient(_config())

    response = client.logout(session_token="session-token")

    assert response.ok is True
    assert seen["path"] == "/internal/auth/logout"
    assert seen["json"] == {"payload": {"session_token": "session-token"}}
