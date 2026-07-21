from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus, urlparse

from .models import LivestreamResult
from .service import DiscoveryUnavailable


REPLAY_MARKERS = ("replay", "recorded", "recording", "premiere", "ended")
LIVE_MARKER = re.compile(r"\blive\b", re.IGNORECASE)
FACEBOOK_HOSTS = {"facebook.com", "www.facebook.com", "m.facebook.com"}


class FacebookBrowserDiscovery:
    """Discover and verify public Facebook broadcasts without automated login."""

    def __init__(self, max_candidates: int = 20) -> None:
        self.max_candidates = max_candidates

    async def search(self, query: str) -> list[LivestreamResult]:
        try:
            from playwright.async_api import TimeoutError as PlaywrightTimeoutError
            from playwright.async_api import async_playwright
        except ImportError as error:
            raise DiscoveryUnavailable(
                "Playwright is not installed. Run `uv sync --extra dev` and "
                "`uv run playwright install chromium`."
            ) from error

        search_url = f"https://www.facebook.com/search/videos/?q={quote_plus(query)}"
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    headless=os.getenv("FACEBOOK_HEADLESS", "true").lower() != "false"
                )
                context = await browser.new_context(
                    locale="en-US",
                    timezone_id="UTC",
                    viewport={"width": 1440, "height": 1000},
                )
                page = await context.new_page()
                await page.goto(search_url, wait_until="domcontentloaded", timeout=30_000)
                await page.wait_for_timeout(1_500)
                candidates = await self._extract_candidates(page)

                results: list[LivestreamResult] = []
                for candidate in candidates[: self.max_candidates]:
                    verified = await self._verify_candidate(context, candidate)
                    if verified is not None:
                        results.append(verified)

                await browser.close()
                return results
        except PlaywrightTimeoutError as error:
            raise DiscoveryUnavailable(
                "Facebook did not respond before the search timed out. Try again."
            ) from error
        except Exception as error:
            raise DiscoveryUnavailable(
                "Facebook discovery is temporarily unavailable. Check the browser "
                "installation and try again."
            ) from error

    async def _extract_candidates(self, page: object) -> list[dict[str, str]]:
        links = await page.locator("a[href]").evaluate_all(
            """
            anchors => anchors.map(anchor => ({
              href: anchor.href,
              text: anchor.innerText || anchor.getAttribute('aria-label') || ''
            }))
            """
        )
        candidates: list[dict[str, str]] = []
        seen: set[str] = set()
        for link in links:
            url = str(link.get("href", "")).split("#", 1)[0]
            parsed = urlparse(url)
            if parsed.netloc not in FACEBOOK_HOSTS:
                continue
            if not any(segment in parsed.path for segment in ("/watch", "/videos", "/live")):
                continue
            if url in seen:
                continue
            seen.add(url)
            candidates.append({"url": url, "text": str(link.get("text", "")).strip()})
        return candidates

    async def _verify_candidate(
        self, context: object, candidate: dict[str, str]
    ) -> LivestreamResult | None:
        page = await context.new_page()
        try:
            await page.goto(candidate["url"], wait_until="domcontentloaded", timeout=20_000)
            await page.wait_for_timeout(1_000)
            body = " ".join((await page.locator("body").inner_text()).split())
            if not self._is_live(body):
                return None
            verified_at = datetime.now(timezone.utc)
            return LivestreamResult(
                id=self._stable_id(candidate["url"]),
                title=candidate["text"] or "Live broadcast",
                source_name="Facebook public page",
                url=candidate["url"],
                verified_at=verified_at,
                is_live=True,
                is_replay=False,
            )
        finally:
            await page.close()

    @staticmethod
    def _is_live(text: str) -> bool:
        normalized = text.lower()
        if any(marker in normalized for marker in REPLAY_MARKERS):
            return False
        return bool(LIVE_MARKER.search(text))

    @staticmethod
    def _stable_id(url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
