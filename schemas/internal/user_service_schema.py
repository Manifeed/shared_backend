from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from shared_backend.schemas.account.account_schema import (
    AccountPasswordUpdateRequestSchema,
    AccountProfileUpdateRequestSchema,
    UserApiKeyCreateRequestSchema,
)
from shared_backend.schemas.admin.admin_user_schema import AdminUserUpdateRequestSchema
from shared_backend.schemas.auth.auth_schema import UserRole


class InternalCurrentUserPayload(BaseModel):
    user_id: int = Field(ge=1)
    email: str = Field(min_length=3, max_length=320)
    role: UserRole
    is_active: bool
    api_access_enabled: bool
    session_expires_at: datetime


class InternalAdminUserListFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: UserRole | None = None
    is_active: bool | None = None
    api_access_enabled: bool | None = None
    search: str | None = Field(default=None, min_length=1, max_length=320)
    limit: int = Field(default=100, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class InternalAdminUserListRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_user: InternalCurrentUserPayload
    filters: InternalAdminUserListFilters = Field(default_factory=InternalAdminUserListFilters)


class InternalAdminUserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_user: InternalCurrentUserPayload
    payload: AdminUserUpdateRequestSchema


class InternalAccountProfileUpdateRequest(BaseModel):
    current_user: InternalCurrentUserPayload
    payload: AccountProfileUpdateRequestSchema


class InternalAccountPasswordUpdateRequest(BaseModel):
    current_user: InternalCurrentUserPayload
    payload: AccountPasswordUpdateRequestSchema


class InternalApiKeyCreateRequest(BaseModel):
    current_user: InternalCurrentUserPayload
    payload: UserApiKeyCreateRequestSchema


class InternalAccountMeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_user: InternalCurrentUserPayload


__all__ = [
    "InternalAdminUserListFilters",
    "InternalAdminUserListRequest",
    "InternalAdminUserUpdateRequest",
    "InternalAccountMeRequest",
    "InternalAccountPasswordUpdateRequest",
    "InternalAccountProfileUpdateRequest",
    "InternalApiKeyCreateRequest",
    "InternalCurrentUserPayload",
]
