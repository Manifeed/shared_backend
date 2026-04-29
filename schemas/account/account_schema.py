from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from shared_backend.schemas.auth.auth_schema import AuthenticatedUserRead


WorkerType = Literal["rss_scrapper", "source_embedding"]


class AccountMeRead(BaseModel):
    user: AuthenticatedUserRead


class AccountPasswordUpdateRequestSchema(BaseModel):
    current_password: str = Field(min_length=1, max_length=255)
    new_password: str = Field(min_length=12, max_length=255)


class AccountPasswordUpdateRead(BaseModel):
    ok: bool = True


class AccountProfileUpdateRequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pseudo: str | None = Field(default=None, min_length=1, max_length=80)
    pp_id: int | None = Field(default=None, ge=1, le=8)

    @model_validator(mode="after")
    def validate_non_empty_payload(self) -> "AccountProfileUpdateRequestSchema":
        if self.pseudo is None and self.pp_id is None:
            raise ValueError("At least one profile field must be provided")
        return self


class AccountProfileUpdateRead(BaseModel):
    user: AuthenticatedUserRead


class UserApiKeyRead(BaseModel):
    id: int = Field(ge=1)
    label: str = Field(min_length=1, max_length=120)
    worker_type: WorkerType
    worker_name: str = Field(min_length=1, max_length=120)
    key_prefix: str = Field(min_length=1, max_length=32)
    last_used_at: datetime | None = None
    created_at: datetime


class UserApiKeyListRead(BaseModel):
    items: list[UserApiKeyRead] = Field(default_factory=list)


class UserApiKeyCreateRequestSchema(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    worker_type: WorkerType


class UserApiKeyCreateRead(BaseModel):
    api_key: str = Field(min_length=1)
    api_key_info: UserApiKeyRead


class UserApiKeyDeleteRead(BaseModel):
    ok: bool = True
