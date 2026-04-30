from pydantic import BaseModel

from shared_backend.schemas.rss.rss_company_schema import RssCompanyRead


class RssFeedRead(BaseModel):
    id: int
    url: str | None = None
    section: str | None = None
    enabled: bool
    trust_score: float
    fetchprotection: int
    consecutive_error_count: int
    last_error_code: int | None = None
    company: RssCompanyRead | None = None
