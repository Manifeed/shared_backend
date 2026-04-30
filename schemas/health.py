from pydantic import BaseModel, Field


class HealthServiceRead(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    kind: str = Field(min_length=1, max_length=40)
    status: str = Field(min_length=1, max_length=32)
    detail: str | None = Field(default=None, max_length=512)
    latency_ms: int | None = Field(default=None, ge=0)


class HealthRead(BaseModel):
    status: str = Field(min_length=1, max_length=32)
    database: str = Field(min_length=1, max_length=32)
    services: dict[str, HealthServiceRead] = Field(default_factory=dict)
