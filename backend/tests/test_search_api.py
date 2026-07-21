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


class EmptyDiscovery:
    async def search(self, query: str) -> list[LivestreamResult]:
        return []


@pytest.mark.anyio
async def test_search_api_returns_empty_results_on_successful_empty_search() -> None:
    app = create_app(EmptyDiscovery())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/search", json={"query": "gaming"})

    assert response.status_code == 200
    assert response.json()["query"] == "gaming"
    assert response.json()["results"] == []
    assert "verified_at" in response.json()

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
    def __init__(
        self,
        links: list[dict[str, str]] | None = None,
        text: str = "",
        content: str | None = None,
        exception: Exception | None = None,
    ) -> None:
        self._links = links or []
        self._text = text
        self._content = content
        self._exception = exception

    @property
    def first(self) -> MockLocator:
        return self

    async def evaluate_all(self, expression: str) -> list[dict[str, str]]:
        if self._exception:
            raise self._exception
        return self._links

    async def inner_text(self) -> str:
        if self._exception:
            raise self._exception
        return self._text

    async def get_attribute(self, name: str, timeout: int | None = None) -> str | None:
        if self._exception:
            raise self._exception
        if name == "content":
            return self._content
        return None


class MockPage:
    def __init__(
        self,
        url: str = "",
        links: list[dict[str, str]] | None = None,
        body_text: str = "",
        meta_contents: list[str | None] | None = None,
        goto_exception: Exception | None = None,
        locator_exception: Exception | None = None,
    ) -> None:
        self.url = url
        self._links = links or []
        self._body_text = body_text
        self._meta_contents = list(meta_contents) if meta_contents is not None else []
        self._goto_exception = goto_exception
        self._locator_exception = locator_exception

    async def goto(self, url: str, wait_until: str | None = None, timeout: int | None = None) -> None:
        if self._goto_exception:
            raise self._goto_exception
        self.url = url

    async def wait_for_timeout(self, timeout: int) -> None:
        pass

    def locator(self, selector: str) -> MockLocator:
        if selector == "a[href]":
            return MockLocator(links=self._links, exception=self._locator_exception)
        elif selector == "body":
            return MockLocator(text=self._body_text, exception=self._locator_exception)
        content = self._meta_contents.pop(0) if self._meta_contents else None
        return MockLocator(content=content, exception=self._locator_exception)

    async def close(self) -> None:
        pass


class MockContext:
    def __init__(
        self,
        search_page: dict[str, object] | list[dict[str, str]],
        candidate_responses: list[dict[str, object]] | None = None,
    ) -> None:
        if isinstance(search_page, list):
            self._search_page: dict[str, object] = {"links": search_page}
        else:
            self._search_page = search_page or {}
        self._candidate_responses = candidate_responses or []
        self._created_pages: list[MockPage] = []

    async def new_page(self) -> MockPage:
        if not self._created_pages:
            links = self._search_page.get("links")
            body_text = str(self._search_page.get("body_text", ""))
            goto_exc = self._search_page.get("exception")
            loc_exc = self._search_page.get("locator_exception")
            page = MockPage(
                links=links if isinstance(links, list) else None,
                body_text=body_text,
                goto_exception=goto_exc if isinstance(goto_exc, Exception) else None,
                locator_exception=loc_exc if isinstance(loc_exc, Exception) else None,
            )
            self._created_pages.append(page)
            return page

        page_idx = len(self._created_pages) - 1
        resp = self._candidate_responses[page_idx] if page_idx < len(self._candidate_responses) else {}
        meta_contents = resp.get("meta_contents")

        page = MockPage(
            body_text=str(resp.get("body_text", "")),
            meta_contents=meta_contents if isinstance(meta_contents, list) else None,
            goto_exception=resp.get("exception") if isinstance(resp.get("exception"), Exception) else None,
            locator_exception=resp.get("locator_exception") if isinstance(resp.get("locator_exception"), Exception) else None,
        )
        self._created_pages.append(page)
        return page


class MockBrowser:
    def __init__(
        self,
        search_page: dict[str, object] | list[dict[str, str]],
        candidate_responses: list[dict[str, object]] | None = None,
    ) -> None:
        self._search_page = search_page
        self._candidate_responses = candidate_responses

    async def new_context(self, **kwargs: object) -> MockContext:
        return MockContext(self._search_page, self._candidate_responses)

    async def close(self) -> None:
        pass


class MockChromium:
    def __init__(
        self,
        search_page: dict[str, object] | list[dict[str, str]],
        candidate_responses: list[dict[str, object]] | None = None,
    ) -> None:
        self._search_page = search_page
        self._candidate_responses = candidate_responses

    async def launch(self, **kwargs: object) -> MockBrowser:
        return MockBrowser(self._search_page, self._candidate_responses)


class MockPlaywright:
    def __init__(
        self,
        search_page: dict[str, object] | list[dict[str, str]],
        candidate_responses: list[dict[str, object]] | None = None,
    ) -> None:
        self.chromium = MockChromium(search_page, candidate_responses)

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
@pytest.mark.anyio
async def test_discovery_returns_live_broadcast_when_page_has_incidental_login_footer(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.discovery import FacebookBrowserDiscovery

    search_links = [
        {"href": "https://www.facebook.com/watch/?v=501", "text": "Public Stream"},
    ]
    candidate_responses = [
        {"body_text": "See more on Facebook. Log In or Create New Account. Gaming stream is live now."},
    ]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        lambda: MockPlaywright(search_links, candidate_responses),
    )

    discovery = FacebookBrowserDiscovery()
    results = await discovery.search("gaming")

    assert len(results) == 1
    assert results[0].url == "https://www.facebook.com/watch/?v=501"


@pytest.mark.anyio
async def test_discovery_raises_unavailable_when_candidate_fails_and_remaining_are_non_live(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.discovery import FacebookBrowserDiscovery
    from backend.app.service import DiscoveryUnavailable

    search_links = [
        {"href": "https://www.facebook.com/watch/?v=601", "text": "Failing Stream"},
        {"href": "https://www.facebook.com/watch/?v=602", "text": "Ended Stream"},
    ]
    candidate_responses = [
        {"exception": RuntimeError("Navigation timeout")},
        {"body_text": "Stream ended 1 hour ago"},
    ]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        lambda: MockPlaywright(search_links, candidate_responses),
    )

    discovery = FacebookBrowserDiscovery()
    with pytest.raises(DiscoveryUnavailable):
        await discovery.search("gaming")

@pytest.mark.anyio
async def test_search_api_returns_503_on_search_page_captcha(monkeypatch: pytest.MonkeyPatch) -> None:
    search_page = {
        "links": [{"href": "https://www.facebook.com/watch/?v=701", "text": "Stream"}],
        "body_text": "Security Check. Please enter the CAPTCHA characters to continue.",
    }

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        lambda: MockPlaywright(search_page, []),
    )

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/search", json={"query": "gaming"})

    assert response.status_code == 503
    assert "security check" in response.json()["detail"].lower() or "captcha" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_search_api_returns_503_on_search_page_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    search_page = {
        "links": [{"href": "https://www.facebook.com/watch/?v=801", "text": "Stream"}],
        "body_text": "Rate limit exceeded. You're temporarily blocked.",
    }

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        lambda: MockPlaywright(search_page, []),
    )

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/search", json={"query": "gaming"})

    assert response.status_code == 503
    assert "rate limit" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_search_api_returns_503_on_candidate_page_captcha(monkeypatch: pytest.MonkeyPatch) -> None:
    search_links = [
        {"href": "https://www.facebook.com/watch/?v=901", "text": "Captcha Candidate Stream"},
    ]
    candidate_responses = [
        {"body_text": "Security check required. Please enter CAPTCHA to continue."},
    ]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        lambda: MockPlaywright(search_links, candidate_responses),
    )

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/search", json={"query": "gaming"})

    assert response.status_code == 503
    assert "security check" in response.json()["detail"].lower() or "captcha" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_search_api_returns_503_on_candidate_page_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    search_links = [
        {"href": "https://www.facebook.com/watch/?v=902", "text": "Rate Limit Candidate Stream"},
    ]
    candidate_responses = [
        {"body_text": "Rate limit exceeded. Please try again later."},
    ]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        lambda: MockPlaywright(search_links, candidate_responses),
    )

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/search", json={"query": "gaming"})

    assert response.status_code == 503
    assert "rate limit" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_search_api_returns_503_on_search_page_locator_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    search_page = {
        "links": [{"href": "https://www.facebook.com/watch/?v=903", "text": "Stream"}],
        "locator_exception": RuntimeError("Page locator detached"),
    }

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        lambda: MockPlaywright(search_page, []),
    )

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/search", json={"query": "gaming"})

    assert response.status_code == 503
    assert "content is unavailable" in response.json()["detail"].lower() or "unavailable" in response.json()["detail"].lower()


class ConfigurableFakeDiscovery:
    def __init__(self, results: list[LivestreamResult]) -> None:
        self._results = results

    async def search(self, query: str) -> list[LivestreamResult]:
        return self._results


@pytest.mark.anyio
async def test_search_api_returns_complete_result_metadata_and_facebook_handoff_url() -> None:
    verified_at = datetime(2026, 7, 21, 12, 0, 0, tzinfo=timezone.utc)
    started_at = datetime(2026, 7, 21, 11, 30, 0, tzinfo=timezone.utc)
    results = [
        LivestreamResult(
            id="live-101",
            title="Official Gaming Championship",
            source_name="Esports Channel",
            url="https://www.facebook.com/watch/?v=1000101",
            thumbnail_url="https://www.facebook.com/images/thumb101.jpg",
            started_at=started_at,
            verified_at=verified_at,
            is_live=True,
            is_replay=False,
        )
    ]
    app = create_app(ConfigurableFakeDiscovery(results))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/search", json={"query": "championship"})

    assert response.status_code == 200
    data = response.json()

    assert data["query"] == "championship"
    assert "verified_at" in data
    assert len(data["results"]) == 1

    result = data["results"][0]
    assert result["id"] == "live-101"
    assert result["title"] == "Official Gaming Championship"
    assert result["source_name"] == "Esports Channel"
    assert result["url"] == "https://www.facebook.com/watch/?v=1000101"
    assert result["url"].startswith("https://www.facebook.com/")
    assert result["thumbnail_url"] == "https://www.facebook.com/images/thumb101.jpg"
    assert "2026-07-21" in result["started_at"]
    assert "2026-07-21" in result["verified_at"]
    assert result["is_live"] is True
    assert result["is_replay"] is False


@pytest.mark.anyio
async def test_search_api_handles_results_without_thumbnail_url() -> None:
    verified_at = datetime(2026, 7, 21, 12, 0, 0, tzinfo=timezone.utc)
    results = [
        LivestreamResult(
            id="live-102",
            title="Community Stream",
            source_name="Community Page",
            url="https://www.facebook.com/watch/?v=1000102",
            thumbnail_url=None,
            started_at=None,
            verified_at=verified_at,
            is_live=True,
            is_replay=False,
        )
    ]
    app = create_app(ConfigurableFakeDiscovery(results))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/search", json={"query": "community"})

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["id"] == "live-102"
    assert result["thumbnail_url"] is None


@pytest.mark.anyio
async def test_discovery_filters_generic_facebook_site_name_to_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.discovery import FacebookBrowserDiscovery

    search_page = [{"href": "https://www.facebook.com/watch/?v=905", "text": "Generic Site Name Stream"}]
    candidate_responses = [
        {
            "body_text": "Live now streaming live event",
            "meta_contents": [
                None,
                "Facebook",
            ],
        }
    ]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        lambda: MockPlaywright(search_page, candidate_responses),
    )

    discovery = FacebookBrowserDiscovery()
    results = await discovery.search("generic")
    assert len(results) == 1
    assert results[0].source_name == "Facebook public page"


@pytest.mark.anyio
async def test_discovery_canonical_url_normalizes_paths_and_tracking_params(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.discovery import FacebookBrowserDiscovery

    search_page = [
        {"href": "https://m.facebook.com/watch/?v=777&fbclid=XYZ123&ref=search", "text": "Mobile URL with tracking"},
        {"href": "https://www.facebook.com/watch/?ref=search&v=777", "text": "Desktop URL with tracking"},
    ]
    candidate_responses = [
        {"body_text": "Live broadcast streaming now live gaming"},
        {"body_text": "Live broadcast streaming now live gaming"},
    ]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        lambda: MockPlaywright(search_page, candidate_responses),
    )

    discovery = FacebookBrowserDiscovery()
    results = await discovery.search("gaming")

    assert len(results) == 1
    assert results[0].url == "https://www.facebook.com/watch/?v=777"


@pytest.mark.anyio
async def test_discovery_extracts_thumbnail_and_source_name_when_present(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.discovery import FacebookBrowserDiscovery

    search_page = [{"href": "https://www.facebook.com/watch/?v=901", "text": "Live Event"}]
    candidate_responses = [
        {
            "body_text": "Live now streaming live event",
            "meta_contents": [
                "https://www.facebook.com/images/preview.jpg",
                "Tech Channel",
            ],
        }
    ]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        lambda: MockPlaywright(search_page, candidate_responses),
    )

    discovery = FacebookBrowserDiscovery()
    results = await discovery.search("tech")
    assert len(results) == 1
    assert results[0].thumbnail_url == "https://www.facebook.com/images/preview.jpg"
    assert results[0].source_name == "Tech Channel"


@pytest.mark.anyio
async def test_discovery_handles_missing_thumbnail_and_source_name_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.discovery import FacebookBrowserDiscovery

    search_page = [{"href": "https://www.facebook.com/watch/?v=902", "text": "Live Stream"}]
    candidate_responses = [
        {
            "body_text": "Live now playing games",
        }
    ]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        lambda: MockPlaywright(search_page, candidate_responses),
    )

    discovery = FacebookBrowserDiscovery()
    results = await discovery.search("games")
    assert len(results) == 1
    assert results[0].thumbnail_url is None
    assert results[0].source_name == "Facebook public page"