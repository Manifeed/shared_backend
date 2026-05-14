from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from shared_backend.schemas.auth.auth_schema import AuthenticatedUserRead
from shared_backend.schemas.internal.service_schema import InternalResolvedSessionRead


class AuthenticatedUserRecord(Protocol):
    id: int
    email: str
    pseudo: str
    pp_id: int
    role: str
    is_active: bool
    api_access_enabled: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class AuthenticatedUserContext:
    user_id: int
    email: str
    role: str
    is_active: bool
    api_access_enabled: bool
    session_expires_at: datetime


def authenticated_user_context_from_resolved_session(
    resolved: InternalResolvedSessionRead,
) -> AuthenticatedUserContext:
    return AuthenticatedUserContext(
        user_id=resolved.user_id,
        email=resolved.email,
        role=resolved.role,
        is_active=resolved.is_active,
        api_access_enabled=resolved.api_access_enabled,
        session_expires_at=resolved.session_expires_at,
    )


def build_authenticated_user_read(
    user: AuthenticatedUserRecord,
) -> AuthenticatedUserRead:
    return AuthenticatedUserRead(
        id=user.id,
        email=user.email,
        pseudo=user.pseudo,
        pp_id=user.pp_id,
        role=user.role,
        is_active=user.is_active,
        api_access_enabled=user.api_access_enabled,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
