from pydantic import BaseModel


class RssCompanyRead(BaseModel):
    id: int
    name: str
    icon_url: str | None = None
    enabled: bool
