from pydantic import BaseModel, Field


class AdminStatsRead(BaseModel):
    connected_users: int = Field(ge=0)
    total_users: int = Field(ge=0)
    connected_workers: int = Field(ge=0)
    total_sources: int = Field(ge=0)
