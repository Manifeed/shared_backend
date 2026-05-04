from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from pydantic import ValidationError

import pytest

from shared_backend.clients.service_http_client import (
    ServiceClientConfig,
    build_internal_headers,
    build_service_config,
    require_service_client,
)
from shared_backend.domain.current_user import build_authenticated_user_read
from shared_backend.domain.password_policy import validate_password_policy
from shared_backend.domain.user_identity import normalize_user_pseudo
from shared_backend.domain.worker_identity import build_worker_name
from shared_backend.errors.app_error import UpstreamServiceError
from shared_backend.errors.custom_exceptions import InternalServiceAuthError, WeakPasswordError
from shared_backend.security.internal_service_auth import (
    INTERNAL_SERVICE_TOKEN_HEADER,
    require_internal_service_token,
    read_internal_service_tokens,
    validate_internal_service_token_configuration,
)
from shared_backend.schemas.account.account_schema import AccountProfileUpdateRequestSchema
from shared_backend.schemas.admin.admin_user_schema import AdminUserUpdateRequestSchema
from shared_backend.utils.auth_utils import (
    hash_password,
    hash_secret_token,
    verify_password,
)
from shared_backend.utils.datetime_utils import normalize_datetime_to_utc
from shared_backend.utils.environment_utils import (
    is_development_environment,
    is_production_like_environment,
)
from shared_backend.utils.logging_utils import begin_log_context, end_log_context
from shared_backend.utils.public_url import build_public_url, require_public_base_url


@dataclass(frozen=True)
class UserRecordFixture:
    id: int
    email: str
    pseudo: str
    pp_id: int
    role: str
    is_active: bool
    api_access_enabled: bool
    created_at: datetime
    updated_at: datetime


def test_normalize_user_pseudo_is_ascii_slug() -> None:
    assert normalize_user_pseudo("Élodie Admin!!") == "elodie-admin"


def test_validate_password_policy_rejects_weak_password() -> None:
    with pytest.raises(WeakPasswordError):
        validate_password_policy("123456789012")


def test_account_profile_update_requires_at_least_one_field() -> None:
    with pytest.raises(ValidationError):
        AccountProfileUpdateRequestSchema()


def test_admin_user_update_requires_at_least_one_field() -> None:
    with pytest.raises(ValidationError):
        AdminUserUpdateRequestSchema()


def test_build_authenticated_user_read_maps_user_record() -> None:
    now = datetime.now(UTC)
    user = UserRecordFixture(
        id=1,
        email="user@example.com",
        pseudo="user",
        pp_id=1,
        role="admin",
        is_active=True,
        api_access_enabled=True,
        created_at=now,
        updated_at=now,
    )

    result = build_authenticated_user_read(user)

    assert result.id == user.id
    assert result.role == "admin"
    assert result.created_at == now


def test_worker_name_uses_normalized_parts() -> None:
    assert (
        build_worker_name(
            pseudo="Élodie",
            worker_type="source_embedding",
            worker_number=0,
        )
        == "elodie-embedding-1"
    )


def test_auth_utils_hash_and_token_contracts() -> None:
    password_hash = hash_password("valid-password")

    assert verify_password(password_hash, "valid-password") is True
    assert verify_password(password_hash, "invalid-password") is False
    assert hash_secret_token("secret") == hash_secret_token("secret")


def test_normalize_datetime_to_utc_supports_naive_and_zulu_values() -> None:
    naive_value = datetime(2026, 5, 4, 12, 0, 0)

    assert normalize_datetime_to_utc(naive_value) == datetime(2026, 5, 4, 12, 0, 0, tzinfo=UTC)
    assert normalize_datetime_to_utc("2026-05-04T12:00:00Z") == datetime(
        2026,
        5,
        4,
        12,
        0,
        0,
        tzinfo=UTC,
    )


def test_internal_service_token_can_be_omitted_in_local_environment() -> None:
    require_internal_service_token(
        SimpleNamespace(headers={}),
        env={"APP_ENV": "local"},
    )


def test_internal_service_tokens_support_multiple_candidates() -> None:
    require_internal_service_token(
        SimpleNamespace(headers={INTERNAL_SERVICE_TOKEN_HEADER: "y" * 32}),
        env={
            "APP_ENV": "production",
            "INTERNAL_SERVICE_TOKENS": f"{'x' * 32}, {'y' * 32}",
        },
    )


def test_read_internal_service_tokens_keeps_primary_token_first() -> None:
    assert read_internal_service_tokens(
        {
            "INTERNAL_SERVICE_TOKEN": "x" * 32,
            "INTERNAL_SERVICE_TOKENS": f"{'y' * 32},{'x' * 32}",
        }
    ) == ("x" * 32, "y" * 32)


def test_environment_utils_detect_development_values() -> None:
    assert is_development_environment({"APP_ENV": "development"}) is True
    assert is_production_like_environment({"APP_ENV": "development"}) is False


def test_environment_utils_detect_production_like_values() -> None:
    assert is_development_environment({"ENVIRONMENT": "staging"}) is False
    assert is_production_like_environment({"ENVIRONMENT": "staging"}) is True


def test_require_internal_service_token_true_overrides_dev_environment() -> None:
    with pytest.raises(InternalServiceAuthError):
        validate_internal_service_token_configuration(
            env={
                "APP_ENV": "dev",
                "REQUIRE_INTERNAL_SERVICE_TOKEN": "true",
            }
        )


def test_internal_service_token_header_is_built_when_token_is_present() -> None:
    assert build_internal_headers(
        ServiceClientConfig(
            base_url="http://example.test",
            internal_token="x" * 32,
            timeout_seconds=5.0,
            service_name="Example",
        )
    ) == {
        "Content-Type": "application/json",
        INTERNAL_SERVICE_TOKEN_HEADER: "x" * 32,
    }


def test_build_service_config_reads_env_contract() -> None:
    config = build_service_config(
        base_url_env="EXAMPLE_SERVICE_URL",
        timeout_env="EXAMPLE_TIMEOUT_SECONDS",
        default_timeout_seconds=5.0,
        service_name="Example",
        env={
            "EXAMPLE_SERVICE_URL": "http://example.test/",
            "EXAMPLE_TIMEOUT_SECONDS": "9",
            "INTERNAL_SERVICE_TOKEN": "x" * 32,
        },
    )

    assert config == ServiceClientConfig(
        base_url="http://example.test",
        internal_token="x" * 32,
        timeout_seconds=9.0,
        service_name="Example",
    )


def test_require_service_client_fails_with_shared_upstream_error() -> None:
    with pytest.raises(UpstreamServiceError):
        require_service_client(
            None,
            env_name="EXAMPLE_SERVICE_URL",
            upstream_error_factory=UpstreamServiceError,
        )


def test_internal_service_request_id_header_is_propagated() -> None:
    token = begin_log_context(
        request_id="req-123",
        service_name="example-service",
    )
    try:
        assert build_internal_headers(
            ServiceClientConfig(
                base_url="http://example.test",
                internal_token="x" * 32,
                timeout_seconds=5.0,
                service_name="Example",
            )
        )["x-request-id"] == "req-123"
    finally:
        end_log_context(token)


def test_require_public_base_url_normalizes_host_and_path(monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://Example.test/base/")

    public_base_url = require_public_base_url()

    assert public_base_url == "https://example.test/base"
    assert build_public_url(public_base_url, "/workers/api/releases/desktop") == (
        "https://example.test/base/workers/api/releases/desktop"
    )
