from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field
from shared_backend.schemas.auth.auth_schema import AuthenticatedUserRead


class InternalSessionTokenRequest(BaseModel):
    session_token: str = Field(min_length=1)


class InternalAuthLoginRead(BaseModel):
    session_token: str = Field(min_length=1)
    expires_at: datetime
    user: AuthenticatedUserRead
