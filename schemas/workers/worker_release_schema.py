from pydantic import BaseModel, Field


class WorkerPingRead(BaseModel):
    ok: bool = True
    worker_type: str = Field(min_length=1, max_length=80)
    worker_name: str = Field(min_length=1, max_length=100)
