from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from shared_backend.domain.current_user import build_authenticated_user_read
from shared_backend.domain.password_policy import validate_password_policy
from shared_backend.domain.user_identity import normalize_user_pseudo
from shared_backend.domain.worker_identity import build_worker_name
from shared_backend.errors.custom_exceptions import WeakPasswordError
from shared_backend.schemas.account.account_schema import AccountProfileUpdateRequestSchema
from shared_backend.utils.auth_utils import (
    build_key_prefix,
    generate_api_key,
    generate_session_token,
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
    api_key = generate_api_key()
    session_token = generate_session_token()

    assert verify_password(password_hash, "valid-password") is True
    assert verify_password(password_hash, "invalid-password") is False
    assert api_key.startswith("mk_")
    assert session_token.startswith("msess_")
    assert build_key_prefix(api_key) == api_key[:12]
    assert hash_secret_token("secret") == hash_secret_token("secret")
