from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import create_app
from backend.app.models import LivestreamResult


class FakeDiscovery:
    async def search(self, query: str) -> list[LivestreamResult]:
        assert query == "gaming"
        verified_at = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        return [
            LivestreamResult(
                id="live-1",
                title="Gaming live now",
                source_name="Public Page",
                url="https://www.facebook.com/watch/live-1",
                thumbnail_url=None,
                started_at=None,
                verified_at=verified_at,
                is_live=True,
                is_replay=False,
            ),
            LivestreamResult(
                id="replay-1",
                title="Gaming replay",
                source_name="Public Page",
                url="https://www.facebook.com/watch/replay-1",
                thumbnail_url=None,
                started_at=None,
                verified_at=verified_at,
                is_live=False,
                is_replay=True,
            ),
            LivestreamResult(
                id="live-1",
                title="Gaming live now",
                source_name="Public Page",
                url="https://www.facebook.com/watch/live-1",
                thumbnail_url=None,
                started_at=None,
                verified_at=verified_at,
                is_live=True,
                is_replay=False,
            ),
        ]


@pytest.mark.anyio
async def test_search_returns_only_unique_verified_live_broadcasts() -> None:
    app = create_app(FakeDiscovery())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/search", json={"query": "  gaming  "})

    assert response.status_code == 200
    assert response.json()["query"] == "gaming"
    assert len(response.json()["results"]) == 1
    assert response.json()["results"][0]["id"] == "live-1"


@pytest.mark.anyio
async def test_search_rejects_blank_queries() -> None:
    app = create_app(FakeDiscovery())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/search", json={"query": "   "})

    assert response.status_code == 422
    assert response.json()["detail"] == "Search query must contain at least one non-whitespace character."
