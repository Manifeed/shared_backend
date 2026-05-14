from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from shared_backend.schemas.auth.auth_schema import UserRole


class AdminUserRead(BaseModel):
    id: int = Field(ge=1)
    email: str = Field(min_length=3, max_length=320)
    pseudo: str = Field(min_length=1, max_length=80)
    role: UserRole
    is_active: bool
    api_access_enabled: bool


class AdminUserListRead(BaseModel):
    items: list[AdminUserRead] = Field(default_factory=list)
    total: int = Field(ge=0, default=0)
    active_total: int = Field(ge=0, default=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class AdminUserUpdateRequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool | None = None
    api_access_enabled: bool | None = None

    @model_validator(mode="after")
    def validate_non_empty_payload(self) -> "AdminUserUpdateRequestSchema":
        if self.is_active is None and self.api_access_enabled is None:
            raise ValueError("At least one admin field must be provided")
        return self
