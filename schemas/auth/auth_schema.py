from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


UserRole = Literal["user", "admin"]


class AuthenticatedUserRead(BaseModel):
    id: int = Field(ge=1)
    email: str = Field(min_length=3, max_length=320)
    pseudo: str = Field(min_length=1, max_length=80)
    pp_id: int = Field(ge=1, le=8)
    role: UserRole
    is_active: bool
    api_access_enabled: bool
    created_at: datetime
    updated_at: datetime


class AuthRegisterRequestSchema(BaseModel):
    email: EmailStr = Field(max_length=320)
    pseudo: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=12, max_length=255)


class AuthRegisterRead(BaseModel):
    user: AuthenticatedUserRead


class AuthLoginRequestSchema(BaseModel):
    email: EmailStr = Field(max_length=320)
    password: str = Field(min_length=1, max_length=255)


class AuthLoginRead(BaseModel):
    expires_at: datetime
    user: AuthenticatedUserRead


class AuthSessionRead(BaseModel):
    expires_at: datetime
    user: AuthenticatedUserRead


class AuthLogoutRead(BaseModel):
    ok: bool = True
