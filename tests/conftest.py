from __future__ import annotations

from datetime import datetime, timezone

import pytest

from shared_backend.schemas.auth.auth_schema import AuthenticatedUserRead


@pytest.fixture
def sample_auth_user() -> AuthenticatedUserRead:
    now = datetime.now(timezone.utc)
    return AuthenticatedUserRead(
        id=1,
        email="user@example.com",
        pseudo="user",
        pp_id=1,
        role="user",
        is_active=True,
        api_access_enabled=True,
        created_at=now,
        updated_at=now,
    )
