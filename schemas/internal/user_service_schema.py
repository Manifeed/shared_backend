from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from shared_backend.schemas.account.account_schema import (
    AccountPasswordUpdateRequestSchema,
    AccountProfileUpdateRequestSchema,
    UserApiKeyCreateRequestSchema,
)


class InternalCurrentUserPayload(BaseModel):
    user_id: int = Field(ge=1)
    email: str = Field(min_length=3, max_length=320)
    role: str
    is_active: bool
    api_access_enabled: bool
    session_expires_at: datetime


class InternalAccountProfileUpdateRequest(BaseModel):
    current_user: InternalCurrentUserPayload
    payload: AccountProfileUpdateRequestSchema


class InternalAccountPasswordUpdateRequest(BaseModel):
    current_user: InternalCurrentUserPayload
    payload: AccountPasswordUpdateRequestSchema


class InternalApiKeyCreateRequest(BaseModel):
    current_user: InternalCurrentUserPayload
    payload: UserApiKeyCreateRequestSchema
