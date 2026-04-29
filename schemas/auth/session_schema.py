from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from shared_backend.schemas.auth.auth_schema import AuthenticatedUserRead


@dataclass(frozen=True)
class AuthLoginResult:
    session_token: str
    expires_at: datetime
    user: AuthenticatedUserRead
