from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import create_app
from backend.app.models import CandidateBroadcast, LivestreamResult


class FakeDiscovery:
    async def fetch_candidates(
        self, query: str, cursor: str | None = None
    ) -> tuple[list[CandidateBroadcast], str | None]:
        assert query == "gaming"
        candidates = [
            CandidateBroadcast(
                id="live-1",
                title="Gaming live now",
                source_name="Public Page",
                url="https://www.facebook.com/watch/live-1",
            ),
            CandidateBroadcast(
                id="replay-1",
                title="Gaming replay",
                source_name="Public Page",
                url="https://www.facebook.com/watch/replay-1",
            ),
            CandidateBroadcast(
                id="live-1",
                title="Gaming live now",
                source_name="Public Page",
                url="https://www.facebook.com/watch/live-1",
            ),
        ]
        return candidates, None

    async def verify_live_status(
        self, candidate: CandidateBroadcast
    ) -> LivestreamResult | None:
        verified_at = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        if candidate.id == "replay-1":
            return LivestreamResult(
                id=candidate.id,
                title=candidate.title,
                source_name=candidate.source_name,
                url=candidate.url,
                thumbnail_url=None,
                started_at=None,
                verified_at=verified_at,
                is_live=False,
                is_replay=True,
            )
        return LivestreamResult(
            id=candidate.id,
            title=candidate.title,
            source_name=candidate.source_name,
            url=candidate.url,
            thumbnail_url=None,
            started_at=None,
            verified_at=verified_at,
            is_live=True,
            is_replay=False,
        )

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
    async def fetch_candidates(
        self, query: str, cursor: str | None = None
    ) -> tuple[list[CandidateBroadcast], str | None]:
        return [], None

    async def verify_live_status(
        self, candidate: CandidateBroadcast
    ) -> LivestreamResult | None:
        return None

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
    async def fetch_candidates(
        self, query: str, cursor: str | None = None
    ) -> tuple[list[CandidateBroadcast], str | None]:
        from backend.app.service import DiscoveryUnavailable

        raise DiscoveryUnavailable("Facebook service is down")

    async def verify_live_status(
        self, candidate: CandidateBroadcast
    ) -> LivestreamResult | None:
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
        expected_url: str = "",
        links: list[dict[str, str]] | None = None,
        body_text: str = "",
        meta_contents: list[str | None] | None = None,
        goto_exception: Exception | None = None,
        locator_exception: Exception | None = None,
    ) -> None:
        self.url = url
        self._expected_url = expected_url
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
            if self._expected_url and self.url != self._expected_url:
                return MockLocator(links=[], exception=self._locator_exception)
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
        page_counter: list[int] | None = None,
    ) -> None:
        if isinstance(search_page, list):
            self._search_page: dict[str, object] = {"links": search_page}
        else:
            self._search_page = search_page or {}
        self._candidate_responses = candidate_responses or []
        self._page_counter = page_counter if page_counter is not None else [0]

    async def new_page(self) -> MockPage:
        current_idx = self._page_counter[0]
        self._page_counter[0] += 1

        if current_idx == 0:
            links = self._search_page.get("links")
            expected_url = str(self._search_page.get("expected_url", ""))
            body_text = str(self._search_page.get("body_text", ""))
            goto_exc = self._search_page.get("exception")
            loc_exc = self._search_page.get("locator_exception")
            return MockPage(
                expected_url=expected_url,
                links=links if isinstance(links, list) else None,
                body_text=body_text,
                goto_exception=goto_exc if isinstance(goto_exc, Exception) else None,
                locator_exception=loc_exc if isinstance(loc_exc, Exception) else None,
            )

        resp_idx = current_idx - 1
        resp = self._candidate_responses[resp_idx] if resp_idx < len(self._candidate_responses) else {}
        meta_contents = resp.get("meta_contents")

        return MockPage(
            body_text=str(resp.get("body_text", "")),
            meta_contents=meta_contents if isinstance(meta_contents, list) else None,
            goto_exception=resp.get("exception") if isinstance(resp.get("exception"), Exception) else None,
            locator_exception=resp.get("locator_exception") if isinstance(resp.get("locator_exception"), Exception) else None,
        )


class MockBrowser:
    def __init__(
        self,
        search_page: dict[str, object] | list[dict[str, str]],
        candidate_responses: list[dict[str, object]] | None = None,
        page_counter: list[int] | None = None,
    ) -> None:
        self._search_page = search_page
        self._candidate_responses = candidate_responses
        self._page_counter = page_counter

    async def new_context(self, **kwargs: object) -> MockContext:
        return MockContext(self._search_page, self._candidate_responses, self._page_counter)

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
        self._page_counter: list[int] = [0]

    async def launch(self, **kwargs: object) -> MockBrowser:
        return MockBrowser(self._search_page, self._candidate_responses, self._page_counter)
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


def make_mock_playwright(
    search_page: dict[str, object] | list[dict[str, str]],
    candidate_responses: list[dict[str, object]] | None = None,
) -> object:
    mock = MockPlaywright(search_page, candidate_responses)
    return lambda: mock

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        pass
@pytest.mark.anyio
async def test_discovery_excludes_candidates_requiring_login(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.discovery import FacebookBrowserDiscovery

    search_links = [
        {"href": "https://www.facebook.com/watch/?v=101", "text": "Public Gaming Stream"},
        {"href": "https://www.facebook.com/watch/?v=102", "text": "Private Gaming Stream"},
    ]
    candidate_responses = [
        {"body_text": "Live broadcast streaming now live gaming"},
        {"body_text": "Log In to Facebook. You must log in to view this live video."},
    ]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        make_mock_playwright(search_links, candidate_responses),
    )

    discovery = FacebookBrowserDiscovery()
    results = await discovery.search("gaming")

    assert len(results) == 1
    assert results[0].url == "https://www.facebook.com/watch/?v=101"


@pytest.mark.anyio
async def test_discovery_excludes_ended_livestreams_with_was_live_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.discovery import FacebookBrowserDiscovery

    search_links = [
        {"href": "https://www.facebook.com/watch/?v=201", "text": "Ended Gaming Stream"},
    ]
    candidate_responses = [
        {"body_text": "Page Name was live 2 hours ago. Broadcast completed."},
    ]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        make_mock_playwright(search_links, candidate_responses),
    )

    discovery = FacebookBrowserDiscovery()
    results = await discovery.search("gaming")

    assert len(results) == 0


@pytest.mark.anyio
async def test_discovery_resilient_to_single_candidate_verification_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.discovery import FacebookBrowserDiscovery

    search_links = [
        {"href": "https://www.facebook.com/watch/?v=301", "text": "Failing Gaming Candidate"},
        {"href": "https://www.facebook.com/watch/?v=302", "text": "Healthy Gaming Candidate"},
    ]
    candidate_responses = [
        {"exception": RuntimeError("Playwright navigation failed")},
        {"body_text": "Gaming broadcast is live right now"},
    ]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        make_mock_playwright(search_links, candidate_responses),
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
        {"href": "https://www.facebook.com/watch/?v=401", "text": "Gaming Stream standard URL"},
        {"href": "https://www.facebook.com/watch/?v=401&ref=search&tracking=xyz123", "text": "Gaming Stream tracked URL"},
    ]
    candidate_responses = [
        {"body_text": "Live broadcast streaming now live gaming"},
        {"body_text": "Live broadcast streaming now live gaming"},
    ]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        make_mock_playwright(search_links, candidate_responses),
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
        {"href": "https://www.facebook.com/watch/?v=501", "text": "Public Gaming Stream"},
    ]
    candidate_responses = [
        {"body_text": "See more on Facebook. Log In or Create New Account. Gaming stream is live now."},
    ]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        make_mock_playwright(search_links, candidate_responses),
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
        {"href": "https://www.facebook.com/watch/?v=601", "text": "Failing Gaming Stream"},
        {"href": "https://www.facebook.com/watch/?v=602", "text": "Ended Gaming Stream"},
    ]
    candidate_responses = [
        {"exception": RuntimeError("Navigation timeout")},
        {"body_text": "Stream ended 1 hour ago"},
    ]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        make_mock_playwright(search_links, candidate_responses),
    )

    discovery = FacebookBrowserDiscovery()
    with pytest.raises(DiscoveryUnavailable):
        await discovery.search("gaming")

@pytest.mark.anyio
async def test_search_api_returns_503_on_search_page_captcha(monkeypatch: pytest.MonkeyPatch) -> None:
    search_page = {
        "links": [{"href": "https://www.facebook.com/watch/?v=701", "text": "Gaming Stream"}],
        "body_text": "Security Check. Please enter the CAPTCHA characters to continue.",
    }

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        make_mock_playwright(search_page, []),
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
        "links": [{"href": "https://www.facebook.com/watch/?v=801", "text": "Gaming Stream"}],
        "body_text": "Rate limit exceeded. You're temporarily blocked.",
    }

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        make_mock_playwright(search_page, []),
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
        {"href": "https://www.facebook.com/watch/?v=901", "text": "Captcha Candidate Gaming Stream"},
    ]
    candidate_responses = [
        {"body_text": "Security check required. Please enter CAPTCHA to continue."},
    ]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        make_mock_playwright(search_links, candidate_responses),
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
        {"href": "https://www.facebook.com/watch/?v=902", "text": "Rate Limit Candidate Gaming Stream"},
    ]
    candidate_responses = [
        {"body_text": "Rate limit exceeded. Please try again later."},
    ]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        make_mock_playwright(search_links, candidate_responses),
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
        make_mock_playwright(search_page, []),
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

    async def fetch_candidates(
        self, query: str, cursor: str | None = None
    ) -> tuple[list[CandidateBroadcast], str | None]:
        candidates = [
            CandidateBroadcast(
                id=r.id,
                title=r.title,
                source_name=r.source_name,
                url=r.url,
                thumbnail_url=r.thumbnail_url,
            )
            for r in self._results
        ]
        return candidates, None

    async def verify_live_status(
        self, candidate: CandidateBroadcast
    ) -> LivestreamResult | None:
        for r in self._results:
            if r.id == candidate.id:
                return r
        return None

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
        make_mock_playwright(search_page, candidate_responses),
    )

    discovery = FacebookBrowserDiscovery()
    results = await discovery.search("generic")
    assert len(results) == 1
    assert results[0].source_name == "Facebook public page"


@pytest.mark.anyio
async def test_discovery_canonical_url_normalizes_paths_and_tracking_params(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.discovery import FacebookBrowserDiscovery

    search_page = [
        {"href": "https://m.facebook.com/watch/?v=777&fbclid=XYZ123&ref=search", "text": "Mobile Gaming URL with tracking"},
        {"href": "https://www.facebook.com/watch/?ref=search&v=777", "text": "Desktop Gaming URL with tracking"},
    ]
    candidate_responses = [
        {"body_text": "Live broadcast streaming now live gaming"},
        {"body_text": "Live broadcast streaming now live gaming"},
    ]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        make_mock_playwright(search_page, candidate_responses),
    )

    discovery = FacebookBrowserDiscovery()
    results = await discovery.search("gaming")

    assert len(results) == 1
    assert results[0].url == "https://www.facebook.com/watch/?v=777"


@pytest.mark.anyio
async def test_discovery_extracts_thumbnail_and_source_name_when_present(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.discovery import FacebookBrowserDiscovery

    search_page = [{"href": "https://www.facebook.com/watch/?v=901", "text": "Live Tech Event"}]
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
        make_mock_playwright(search_page, candidate_responses),
    )

    discovery = FacebookBrowserDiscovery()
    results = await discovery.search("tech")
    assert len(results) == 1
    assert results[0].thumbnail_url == "https://www.facebook.com/images/preview.jpg"
    assert results[0].source_name == "Tech Channel"


@pytest.mark.anyio
async def test_discovery_handles_missing_thumbnail_and_source_name_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.discovery import FacebookBrowserDiscovery

    search_page = [{"href": "https://www.facebook.com/watch/?v=902", "text": "Live Games Stream"}]
    candidate_responses = [
        {
            "body_text": "Live now playing games",
        }
    ]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        make_mock_playwright(search_page, candidate_responses),
    )

    discovery = FacebookBrowserDiscovery()
    results = await discovery.search("games")
    assert len(results) == 1
    assert results[0].thumbnail_url is None
    assert results[0].source_name == "Facebook public page"


@pytest.mark.anyio
async def test_discovery_uses_watch_live_search_surface(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.discovery import FacebookBrowserDiscovery

    search_page = {
        "expected_url": "https://www.facebook.com/watch/live/?q=football",
        "links": [{"href": "https://www.facebook.com/watch/?v=999", "text": "Football Match Stream"}],
    }
    candidate_responses = [{"body_text": "Live now streaming football match"}]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        make_mock_playwright(search_page, candidate_responses),
    )

    discovery = FacebookBrowserDiscovery()
    results = await discovery.search("football")

    assert len(results) == 1
    assert results[0].url == "https://www.facebook.com/watch/?v=999"


@pytest.mark.anyio
async def test_discovery_accepts_and_normalizes_regional_facebook_hosts(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.discovery import FacebookBrowserDiscovery

    search_page = [
        {"href": "https://en-gb.facebook.com/watch/?v=888", "text": "Regional Football Broadcast"},
    ]
    candidate_responses = [{"body_text": "Live broadcast streaming now"}]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        make_mock_playwright(search_page, candidate_responses),
    )

    discovery = FacebookBrowserDiscovery()
    results = await discovery.search("football")

    assert len(results) == 1
    assert results[0].url == "https://www.facebook.com/watch/?v=888"


@pytest.mark.anyio
async def test_discovery_excludes_generic_navigation_links_from_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.discovery import FacebookBrowserDiscovery

    search_page = [
        {"href": "https://www.facebook.com/watch/", "text": "Video Nav"},
        {"href": "https://www.facebook.com/watch/live/?ref=watch", "text": "Live Nav"},
        {"href": "https://www.facebook.com/watch/explore/", "text": "Explore Nav"},
        {"href": "https://www.facebook.com/watch/?v=777", "text": "Real Football Video"},
    ]
    candidate_responses = [{"body_text": "Live stream active now"}]

    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        make_mock_playwright(search_page, candidate_responses),
    )

    discovery = FacebookBrowserDiscovery()
    results = await discovery.search("football")

    assert len(results) == 1
    assert results[0].url == "https://www.facebook.com/watch/?v=777"
def test_extract_search_keywords_normalizes_and_filters_stopwords() -> None:
    from backend.app.service import extract_search_keywords

    assert extract_search_keywords("  News  LIVE Stream ") == {"news"}
    assert extract_search_keywords("quantum computing live") == {"quantum", "computing"}
    assert extract_search_keywords("live stream video") == {"live", "stream", "video"}


def test_filter_relevant_candidates_matches_title_and_source_name() -> None:
    from backend.app.models import CandidateBroadcast
    from backend.app.service import filter_relevant_candidates

    candidates = [
        CandidateBroadcast(
            id="1",
            title="Sky News Live Stream",
            source_name="Sky News",
            url="https://www.facebook.com/watch/?v=1",
        ),
        CandidateBroadcast(
            id="2",
            title="Minecraft Survival Day 30",
            source_name="GamerOne",
            url="https://www.facebook.com/watch/?v=2",
        ),
        CandidateBroadcast(
            id="3",
            title="Breaking Headlines Today",
            source_name="Daily News Channel",
            url="https://www.facebook.com/watch/?v=3",
        ),
    ]

    filtered = filter_relevant_candidates("news", candidates)
    assert [c.id for c in filtered] == ["1", "3"]


def test_encode_and_decode_cursor_token_roundtrips() -> None:
    from backend.app.service import decode_cursor_token, encode_cursor_token

    token = encode_cursor_token("surface:15", {"fb-live-101", "fb-live-102"})
    assert isinstance(token, str)

    surface_cursor, seen_ids = decode_cursor_token(token)
    assert surface_cursor == "surface:15"
    assert seen_ids == {"fb-live-101", "fb-live-102"}

    assert decode_cursor_token(None) == (None, set())
    assert decode_cursor_token("invalid_base64!!!") == (None, set())
class FakePaginatedDiscoveryAdapter:
    def __init__(self, candidates: list[CandidateBroadcast], next_surface_cursor: str | None = None) -> None:
        self.candidates = candidates
        self.next_surface_cursor = next_surface_cursor
        self.verified_calls: list[str] = []

    async def fetch_candidates(
        self, query: str, cursor: str | None = None
    ) -> tuple[list[CandidateBroadcast], str | None]:
        offset = 0
        if cursor:
            try:
                if cursor.startswith("surface:"):
                    offset = int(cursor.split(":", 1)[1])
                elif cursor.startswith("offset:"):
                    offset = int(cursor.split(":", 1)[1])
                else:
                    offset = int(cursor)
            except ValueError:
                offset = 0

        sliced = self.candidates[offset : offset + 10]
        next_offset = offset + len(sliced)
        if next_offset < len(self.candidates):
            next_surface = f"surface:{next_offset}"
        else:
            next_surface = self.next_surface_cursor
        return sliced, next_surface
    async def verify_live_status(
        self, candidate: CandidateBroadcast
    ) -> LivestreamResult | None:
        self.verified_calls.append(candidate.id)
        verified_at = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)
        return LivestreamResult(
            id=candidate.id,
            title=candidate.title,
            source_name=candidate.source_name,
            url=candidate.url,
            thumbnail_url=candidate.thumbnail_url,
            started_at=None,
            verified_at=verified_at,
            is_live=True,
            is_replay=False,
        )


@pytest.mark.anyio
async def test_search_api_contract_initial_batching_and_has_more_true() -> None:
    candidates = [
        CandidateBroadcast(
            id=f"news-{i}",
            title=f"Global News Live Stream {i}",
            source_name="News Network",
            url=f"https://www.facebook.com/watch/?v={i}",
        )
        for i in range(1, 16)
    ]
    adapter = FakePaginatedDiscoveryAdapter(candidates, next_surface_cursor="surface:15")
    app = create_app(adapter)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/search", json={"query": "news"})

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 10
    assert data["has_more"] is True
    assert data["next_cursor"] is not None


@pytest.mark.anyio
async def test_search_api_contract_continuation_returns_next_batch_zero_duplicates() -> None:
    candidates = [
        CandidateBroadcast(
            id=f"news-{i}",
            title=f"Global News Live Stream {i}",
            source_name="News Network",
            url=f"https://www.facebook.com/watch/?v={i}",
        )
        for i in range(1, 16)
    ]
    adapter = FakePaginatedDiscoveryAdapter(candidates, next_surface_cursor="surface:15")
    app = create_app(adapter)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp1 = await client.post("/api/search", json={"query": "news"})
        data1 = resp1.json()
        cursor1 = data1["next_cursor"]

        adapter.next_surface_cursor = None

        resp2 = await client.post("/api/search", json={"query": "news", "cursor": cursor1})
        data2 = resp2.json()

    assert resp2.status_code == 200
    assert len(data2["results"]) == 5
    assert data2["has_more"] is False
    assert data2["next_cursor"] is None

    ids1 = {r["id"] for r in data1["results"]}
    ids2 = {r["id"] for r in data2["results"]}
    assert ids1.isdisjoint(ids2)


@pytest.mark.anyio
async def test_search_api_contract_early_relevance_filtering_skips_unnecessary_verification() -> None:
    candidates = [
        CandidateBroadcast(
            id=f"news-{i}",
            title=f"Global News Stream {i}",
            source_name="News Channel",
            url=f"https://www.facebook.com/watch/?v=news-{i}",
        )
        for i in range(1, 6)
    ] + [
        CandidateBroadcast(
            id=f"game-{i}",
            title=f"Fortnite Live Stream {i}",
            source_name="Gamer Channel",
            url=f"https://www.facebook.com/watch/?v=game-{i}",
        )
        for i in range(1, 6)
    ]
    adapter = FakePaginatedDiscoveryAdapter(candidates, next_surface_cursor=None)
    app = create_app(adapter)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/search", json={"query": "news"})

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 5
    assert data["has_more"] is False
    assert adapter.verified_calls == [f"news-{i}" for i in range(1, 6)]


@pytest.mark.anyio
async def test_search_api_contract_partial_batch_with_has_more_true_when_surface_not_exhausted() -> None:
    candidates = [
        CandidateBroadcast(
            id=f"news-{i}",
            title=f"Global News Stream {i}",
            source_name="News Channel",
            url=f"https://www.facebook.com/watch/?v={i}",
        )
        for i in range(1, 7)
    ]
    adapter = FakePaginatedDiscoveryAdapter(candidates, next_surface_cursor="surface:40")
    app = create_app(adapter)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/search", json={"query": "news"})

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 6
    assert data["has_more"] is True
    assert data["next_cursor"] is not None


@pytest.mark.anyio
async def test_search_api_contract_surface_exhaustion_returns_has_more_false() -> None:
    candidates = [
        CandidateBroadcast(
            id=f"news-{i}",
            title=f"Global News Stream {i}",
            source_name="News Channel",
            url=f"https://www.facebook.com/watch/?v={i}",
        )
        for i in range(1, 5)
    ]
    adapter = FakePaginatedDiscoveryAdapter(candidates, next_surface_cursor=None)
    app = create_app(adapter)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/search", json={"query": "news"})

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 4
    assert data["has_more"] is False
    assert data["next_cursor"] is None
