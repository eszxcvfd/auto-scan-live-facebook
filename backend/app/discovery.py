from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, quote_plus, urlencode, urlparse, urlunparse

from .models import LivestreamResult
from .service import DiscoveryUnavailable

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext, Page


LOGIN_WALL_MARKERS = (
    "must log in",
    "you must log in",
    "log in to view",
    "login to view",
    "log in to see",
    "login to see",
    "log in to continue",
    "login to continue",
)

CAPTCHA_MARKERS = (
    "captcha",
    "security check",
    "prove you are human",
    "enter the characters",
    "security code",
)

RATE_LIMIT_MARKERS = (
    "rate limit",
    "too many requests",
    "temporarily blocked",
    "try again later",
    "you’re temporarily blocked",
    "you're temporarily blocked",
)

REPLAY_MARKERS = (
    "replay",
    "recorded",
    "recording",
    "premiere",
    "ended",
    "was live",
    "completed",
    "broadcast completed",
    "stream ended",
    "no longer live",
    "video ended",
    "live ended",
)

TRACKING_PARAMS = {
    "ref",
    "tracking",
    "fbclid",
    "__tn__",
    "__cft__",
    "fref",
    "ti",
    "hc_ref",
    "comment_id",
    "notif_id",
    "notif_t",
    "paipv",
    "extid",
    "sfnsn",
}

LIVE_MARKER = re.compile(r"\blive\b", re.IGNORECASE)
FACEBOOK_HOSTS = {"facebook.com", "www.facebook.com", "m.facebook.com"}
GENERIC_SOURCE_NAMES = {"facebook", "facebook.com", "www.facebook.com", "m.facebook.com"}


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
                verification_errors = 0
                for candidate in candidates[: self.max_candidates]:
                    try:
                        verified = await self._verify_candidate(context, candidate)
                        if verified is not None:
                            results.append(verified)
                    except DiscoveryUnavailable:
                        raise
                    except Exception:
                        verification_errors += 1
                await browser.close()

                if not results and verification_errors > 0:
                    raise DiscoveryUnavailable(
                        "Facebook discovery is temporarily unavailable. Candidate verification failed."
                    )

                return results
        except PlaywrightTimeoutError as error:
            raise DiscoveryUnavailable(
                "Facebook did not respond before the search timed out. Try again."
            ) from error
        except DiscoveryUnavailable:
            raise
        except Exception as error:
            raise DiscoveryUnavailable(
                "Facebook discovery is temporarily unavailable. Check the browser "
                "installation and try again."
            ) from error

    async def _extract_candidates(self, page: Page) -> list[dict[str, str]]:
        await self._inspect_page_body(page, is_candidate=False)

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
            raw_url = str(link.get("href", "")).split("#", 1)[0]
            parsed = urlparse(raw_url)
            if parsed.netloc not in FACEBOOK_HOSTS:
                continue
            if not any(segment in parsed.path for segment in ("/watch", "/videos", "/live")):
                continue
            canonical_url = self._canonical_url(raw_url)
            if canonical_url in seen:
                continue
            seen.add(canonical_url)
            candidates.append({"url": canonical_url, "text": str(link.get("text", "")).strip()})
        return candidates

    async def _verify_candidate(
        self, context: BrowserContext, candidate: dict[str, str]
    ) -> LivestreamResult | None:
        page = await context.new_page()
        try:
            await page.goto(candidate["url"], wait_until="domcontentloaded", timeout=20_000)
            await page.wait_for_timeout(1_000)
            body = await self._inspect_page_body(page, is_candidate=True)
            if not self._is_live(body):
                return None
            verified_at = datetime.now(timezone.utc)
            url = candidate["url"]
            thumbnail_url = await self._extract_thumbnail_url(page)
            source_name = await self._extract_source_name(page) or "Facebook public page"
            return LivestreamResult(
                id=self._stable_id(url),
                title=candidate["text"] or "Live broadcast",
                source_name=source_name,
                url=url,
                thumbnail_url=thumbnail_url,
                verified_at=verified_at,
                is_live=True,
                is_replay=False,
            )
        finally:
            await page.close()
    async def _get_meta_content(self, page: Page, selector: str) -> str | None:
        try:
            content = await page.locator(selector).first.get_attribute("content", timeout=2_000)
            if content and content.strip():
                return content.strip()
        except Exception:
            pass
        return None

    async def _extract_thumbnail_url(self, page: Page) -> str | None:
        content = await self._get_meta_content(
            page, 'meta[property="og:image"], meta[name="twitter:image"]'
        )
        if content and content.startswith(("http://", "https://")):
            return content
        return None

    async def _extract_source_name(self, page: Page) -> str | None:
        for selector in (
            'meta[name="author"]',
            'meta[property="og:owner"]',
            'meta[property="og:site_name"]',
        ):
            name = await self._get_meta_content(page, selector)
            if name and name.lower() not in GENERIC_SOURCE_NAMES:
                return name
        return None

    async def _inspect_page_body(self, page: Page, *, is_candidate: bool = False) -> str:
        try:
            body = " ".join((await page.locator("body").inner_text()).split())
        except Exception as error:
            raise DiscoveryUnavailable("Facebook page content is unavailable.") from error

        normalized_body = body.lower()
        if any(marker in normalized_body for marker in CAPTCHA_MARKERS):
            msg = (
                "Facebook candidate page requested a security check (CAPTCHA)."
                if is_candidate
                else "Facebook requested a security check (CAPTCHA). Public discovery is temporarily unavailable."
            )
            raise DiscoveryUnavailable(msg)
        if any(marker in normalized_body for marker in RATE_LIMIT_MARKERS):
            msg = (
                "Facebook candidate page rate limit reached."
                if is_candidate
                else "Facebook rate limit reached. Public discovery is temporarily unavailable."
            )
            raise DiscoveryUnavailable(msg)

        return body

    @staticmethod
    def _is_live(text: str) -> bool:
        normalized = text.lower()
        if any(marker in normalized for marker in LOGIN_WALL_MARKERS):
            return False
        if any(marker in normalized for marker in REPLAY_MARKERS):
            return False
        return bool(LIVE_MARKER.search(text))

    @staticmethod
    def _canonical_url(url: str) -> str:
        parsed = urlparse(url)
        netloc = "www.facebook.com" if parsed.netloc in FACEBOOK_HOSTS else parsed.netloc

        if parsed.query:
            query_pairs = parse_qs(parsed.query, keep_blank_values=True)
            filtered_pairs = [
                (k, v)
                for k, vlist in query_pairs.items()
                if k not in TRACKING_PARAMS
                for v in vlist
            ]
            filtered_pairs.sort(key=lambda x: (x[0], x[1]))
            new_query = urlencode(filtered_pairs)
        else:
            new_query = ""

        path = parsed.path or "/"
        return urlunparse((parsed.scheme or "https", netloc, path, parsed.params, new_query, ""))

    @staticmethod
    def _stable_id(url: str) -> str:
        canonical = FacebookBrowserDiscovery._canonical_url(url)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
