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
    validate_internal_service_token_configuration,
)
from shared_backend.schemas.account.account_schema import AccountProfileUpdateRequestSchema
from shared_backend.utils.auth_utils import (
    hash_password,
    hash_secret_token,
    verify_password,
)


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


def test_internal_service_token_can_be_omitted_in_local_environment() -> None:
    require_internal_service_token(
        SimpleNamespace(headers={}),
        env={"APP_ENV": "local"},
    )


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
