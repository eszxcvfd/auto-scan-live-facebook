from datetime import datetime

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=120)


class LivestreamResult(BaseModel):
    id: str
    title: str
    source_name: str
    url: str
    thumbnail_url: str | None = None
    started_at: datetime | None = None
    verified_at: datetime
    is_live: bool
    is_replay: bool


class SearchResponse(BaseModel):
    query: str
    verified_at: datetime
    results: list[LivestreamResult]
