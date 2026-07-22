from datetime import datetime

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=120)
    cursor: str | None = Field(default=None, description="Opaque continuation token for fetching the next batch.")


class CandidateBroadcast(BaseModel):
    """Raw candidate stream scraped from Facebook search result page before live verification."""
    id: str
    title: str
    source_name: str
    url: str
    thumbnail_url: str | None = None


class LivestreamResult(BaseModel):
    """Fully verified live broadcast confirmed active via page navigation."""
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
    has_more: bool = False
    next_cursor: str | None = None
