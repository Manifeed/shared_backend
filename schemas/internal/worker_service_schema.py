from pydantic import BaseModel, Field


class WorkerServiceStatsRead(BaseModel):
    connected_workers: int = Field(ge=0)
    pending_rss_tasks: int = Field(ge=0, default=0)
    pending_embedding_tasks: int = Field(ge=0, default=0)
    expired_claims: int = Field(ge=0, default=0)
    stale_redis_task_ids_dropped: int = Field(ge=0, default=0)
    embedding_tasks_requeued: int = Field(ge=0, default=0)
    payload_rebuild_failures: int = Field(ge=0, default=0)
