import base64
import json
import re
from collections.abc import Iterable
from typing import Protocol

from .models import CandidateBroadcast, LivestreamResult


class DiscoveryUnavailable(RuntimeError):
    pass


class DiscoveryPort(Protocol):
    async def fetch_candidates(
        self, query: str, cursor: str | None = None
    ) -> tuple[list[CandidateBroadcast], str | None]: ...

    async def verify_live_status(
        self, candidate: CandidateBroadcast
    ) -> LivestreamResult | None: ...


GENERIC_STOPWORDS = {"live", "stream", "facebook", "video", "online", "channel", "page"}
TARGET_BATCH_SIZE = 10


def normalize_query(query: str) -> str:
    return " ".join(query.split())


def extract_search_keywords(query: str) -> set[str]:
    """Extract normalized search tokens, preserving stopwords if query contains only stopwords."""
    normalized = query.lower().strip()
    tokens = set(re.findall(r"\w+", normalized))
    filtered = tokens - GENERIC_STOPWORDS
    return filtered if filtered else tokens


def is_relevant_candidate(query_keywords: set[str], candidate: CandidateBroadcast) -> bool:
    """Evaluate candidate relevance against title and source_name using word-boundary / substring matching."""
    title_norm = candidate.title.lower()
    source_norm = candidate.source_name.lower()
    for kw in query_keywords:
        if kw in title_norm or kw in source_norm:
            return True
    return False


def filter_relevant_candidates(query: str, candidates: Iterable[CandidateBroadcast]) -> list[CandidateBroadcast]:
    """Filter candidate broadcasts to only those matching query keywords."""
    keywords = extract_search_keywords(query)
    return [c for c in candidates if is_relevant_candidate(keywords, c)]


def encode_cursor_token(surface_cursor: str | None, seen_ids: set[str] | list[str]) -> str:
    data = {
        "offset": surface_cursor,
        "seen_ids": sorted(list(seen_ids)),
    }
    dumped = json.dumps(data)
    return base64.urlsafe_b64encode(dumped.encode("utf-8")).decode("utf-8")


def decode_cursor_token(cursor: str | None) -> tuple[str | None, set[str]]:
    if not cursor:
        return None, set()
    try:
        decoded_bytes = base64.urlsafe_b64decode(cursor.encode("utf-8"))
        data = json.loads(decoded_bytes.decode("utf-8"))
        offset = data.get("offset")
        seen_ids = set(data.get("seen_ids", []))
        return offset, seen_ids
    except Exception:
        return None, set()


def verified_live_results(results: Iterable[LivestreamResult]) -> list[LivestreamResult]:
    unique: dict[str, LivestreamResult] = {}

    for result in results:
        if not result.is_live or result.is_replay:
            continue
        unique.setdefault(result.id, result)

    return list(unique.values())


async def collect_verified_batch(
    discovery: DiscoveryPort,
    query: str,
    cursor: str | None = None,
) -> tuple[list[LivestreamResult], str | None, bool]:
    surface_cursor, seen_ids = decode_cursor_token(cursor)
    accumulated_results: list[LivestreamResult] = []
    candidates_inspected = 0
    current_surface_cursor = surface_cursor
    verification_errors = 0

    while len(accumulated_results) < TARGET_BATCH_SIZE:
        candidates, next_surface_cursor = await discovery.fetch_candidates(query, current_surface_cursor)
        if not candidates:
            current_surface_cursor = None
            break

        relevant_candidates = filter_relevant_candidates(query, candidates)

        for candidate in relevant_candidates:
            candidates_inspected += 1
            if candidate.id in seen_ids:
                continue

            try:
                verified = await discovery.verify_live_status(candidate)
                if verified is not None and verified.is_live and not verified.is_replay:
                    accumulated_results.append(verified)
                    seen_ids.add(verified.id)
            except DiscoveryUnavailable:
                raise
            except Exception:
                verification_errors += 1

            if len(accumulated_results) == TARGET_BATCH_SIZE:
                break

        current_surface_cursor = next_surface_cursor
        if current_surface_cursor is None:
            break

    if not accumulated_results and verification_errors > 0 and candidates_inspected > 0:
        raise DiscoveryUnavailable(
            "Facebook discovery is temporarily unavailable. Candidate verification failed."
        )

    has_more = (len(accumulated_results) == TARGET_BATCH_SIZE) and (current_surface_cursor is not None)
    next_cursor_token = encode_cursor_token(current_surface_cursor, seen_ids) if has_more else None
    return accumulated_results, next_cursor_token, has_more
