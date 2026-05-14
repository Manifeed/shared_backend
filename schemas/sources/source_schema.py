from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SourceSearchMatchedBy = Literal["lexical", "sparse", "dense"]
SourceSearchFilterField = Literal[
    "country",
    "company_id",
    "author_id",
    "published_period",
]
SourceSearchFilterSource = Literal["explicit"]


class RssSourceAuthorRead(BaseModel):
    id: int
    name: str


class SourceListReadBase(BaseModel):
    id: int
    title: str
    authors: list[RssSourceAuthorRead] = Field(default_factory=list)
    url: str | None = None
    published_at: datetime | None = None
    company_names: list[str] = Field(default_factory=list)


class RssSourceRead(SourceListReadBase):
    image_url: str | None = None


class UserSourceRead(SourceListReadBase):
    pass


class RssSourcePageRead(BaseModel):
    items: list[RssSourceRead] = Field(default_factory=list)
    total: int = Field(ge=0, default=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class UserSourcePageRead(BaseModel):
    items: list[UserSourceRead] = Field(default_factory=list)
    total: int = Field(ge=0, default=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class AppliedSearchFilterRead(BaseModel):
    field: SourceSearchFilterField
    value: int | str
    label: str = Field(min_length=1)
    source: SourceSearchFilterSource = "explicit"


class SourceDetailBase(SourceListReadBase):
    summary: str | None = None
    feed_sections: list[str] = Field(default_factory=list)


class RssSourceDetailRead(SourceDetailBase):
    image_url: str | None = None


class UserSourceDetailRead(SourceDetailBase):
    pass


class UserSourceSearchItemRead(SourceDetailBase):
    score: float = Field(ge=0.0, default=0.0)
    matched_by: list[SourceSearchMatchedBy] = Field(default_factory=list)


class UserSourceSearchPageRead(BaseModel):
    raw_query: str = ""
    subject_query: str = ""
    applied_filters: list[AppliedSearchFilterRead] = Field(default_factory=list)
    items: list[UserSourceSearchItemRead] = Field(default_factory=list)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    has_more: bool = False
