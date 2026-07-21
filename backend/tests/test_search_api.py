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


class FailingDiscovery:
    async def search(self, query: str) -> list[LivestreamResult]:
        from backend.app.service import DiscoveryUnavailable

        raise DiscoveryUnavailable("Facebook service is down")


@pytest.mark.anyio
async def test_search_api_returns_503_when_discovery_unavailable() -> None:
    app = create_app(FailingDiscovery())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/search", json={"query": "gaming"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Facebook service is down"


class MockLocator:
    def __init__(self, links: list[dict[str, str]] | None = None, text: str = "") -> None:
        self._links = links or []
        self._text = text

    async def evaluate_all(self, expression: str) -> list[dict[str, str]]:
        return self._links

    async def inner_text(self) -> str:
        return self._text


class MockPage:
    def __init__(
        self,
        url: str = "",
        links: list[dict[str, str]] | None = None,
        body_text: str = "",
        goto_exception: Exception | None = None,
    ) -> None:
        self.url = url
        self._links = links or []
        self._body_text = body_text
        self._goto_exception = goto_exception

    async def goto(self, url: str, wait_until: str | None = None, timeout: int | None = None) -> None:
        if self._goto_exception:
            raise self._goto_exception
        self.url = url

    async def wait_for_timeout(self, timeout: int) -> None:
        pass

    def locator(self, selector: str) -> MockLocator:
        if selector == "a[href]":
            return MockLocator(links=self._links)
        elif selector == "body":
            return MockLocator(text=self._body_text)
        return MockLocator()

    async def close(self) -> None:
        pass


class MockContext:
    def __init__(self, search_links: list[dict[str, str]], candidate_responses: list[dict[str, object]]) -> None:
        self._search_links = search_links
        self._candidate_responses = candidate_responses
        self._created_pages: list[MockPage] = []

    async def new_page(self) -> MockPage:
        if not self._created_pages:
            page = MockPage(links=self._search_links)
            self._created_pages.append(page)
            return page

        page_idx = len(self._created_pages) - 1
        if page_idx < len(self._candidate_responses):
            resp = self._candidate_responses[page_idx]
        else:
            resp = {}

        page = MockPage(
            body_text=str(resp.get("body_text", "")),
            goto_exception=resp.get("exception") if isinstance(resp.get("exception"), Exception) else None,
        )
        self._created_pages.append(page)
        return page


class MockBrowser:
    def __init__(self, search_links: list[dict[str, str]], candidate_responses: list[dict[str, object]]) -> None:
        self._search_links = search_links
        self._candidate_responses = candidate_responses

    async def new_context(self, **kwargs: object) -> MockContext:
        return MockContext(self._search_links, self._candidate_responses)

    async def close(self) -> None:
        pass


class MockChromium:
    def __init__(self, search_links: list[dict[str, str]], candidate_responses: list[dict[str, object]]) -> None:
        self._search_links = search_links
        self._candidate_responses = candidate_responses

    async def launch(self, **kwargs: object) -> MockBrowser:
        return MockBrowser(self._search_links, self._candidate_responses)


class MockPlaywright:
    def __init__(self, search_links: list[dict[str, str]], candidate_responses: list[dict[str, object]]) -> None:
        self.chromium = MockChromium(search_links, candidate_responses)

    async def __aenter__(self) -> "MockPlaywright":
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        pass


@pytest.mark.anyio
async def test_discovery_excludes_candidates_requiring_login(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.discovery import FacebookBrowserDiscovery

    search_links = [
        {"href": "https://www.facebook.com/watch/?v=101", "text": "Public Stream"},
        {"href": "https://www.facebook.com/watch/?v=102", "text": "Private Stream"},
    ]
    candidate_responses = [
        {"body_text": "Live broadcast streaming now live gaming"},
        {"body_text": "Log In to Facebook. You must log in to view this live video."},
    ]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        lambda: MockPlaywright(search_links, candidate_responses),
    )

    discovery = FacebookBrowserDiscovery()
    results = await discovery.search("gaming")

    assert len(results) == 1
    assert results[0].url == "https://www.facebook.com/watch/?v=101"


@pytest.mark.anyio
async def test_discovery_excludes_ended_livestreams_with_was_live_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.discovery import FacebookBrowserDiscovery

    search_links = [
        {"href": "https://www.facebook.com/watch/?v=201", "text": "Ended Stream"},
    ]
    candidate_responses = [
        {"body_text": "Page Name was live 2 hours ago. Broadcast completed."},
    ]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        lambda: MockPlaywright(search_links, candidate_responses),
    )

    discovery = FacebookBrowserDiscovery()
    results = await discovery.search("gaming")

    assert len(results) == 0


@pytest.mark.anyio
async def test_discovery_resilient_to_single_candidate_verification_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.discovery import FacebookBrowserDiscovery

    search_links = [
        {"href": "https://www.facebook.com/watch/?v=301", "text": "Failing Candidate"},
        {"href": "https://www.facebook.com/watch/?v=302", "text": "Healthy Candidate"},
    ]
    candidate_responses = [
        {"exception": RuntimeError("Playwright navigation failed")},
        {"body_text": "Gaming broadcast is live right now"},
    ]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        lambda: MockPlaywright(search_links, candidate_responses),
    )

    discovery = FacebookBrowserDiscovery()
    results = await discovery.search("gaming")

    assert len(results) == 1
    assert results[0].url == "https://www.facebook.com/watch/?v=302"


@pytest.mark.anyio
async def test_discovery_produces_stable_ids_for_url_tracking_variations(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.discovery import FacebookBrowserDiscovery
    from backend.app.service import verified_live_results

    search_links = [
        {"href": "https://www.facebook.com/watch/?v=401", "text": "Stream standard URL"},
        {"href": "https://www.facebook.com/watch/?v=401&ref=search&tracking=xyz123", "text": "Stream tracked URL"},
    ]
    candidate_responses = [
        {"body_text": "Live broadcast streaming now live gaming"},
        {"body_text": "Live broadcast streaming now live gaming"},
    ]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        lambda: MockPlaywright(search_links, candidate_responses),
    )

    discovery = FacebookBrowserDiscovery()
    raw_results = await discovery.search("gaming")
    deduped_results = verified_live_results(raw_results)

    assert len(deduped_results) == 1
    assert deduped_results[0].id == raw_results[0].id
