from pydantic import BaseModel, Field


class WorkerServiceStatsRead(BaseModel):
    connected_workers: int = Field(ge=0)
