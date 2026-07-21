from collections.abc import Iterable
from typing import Protocol

from .models import LivestreamResult


class DiscoveryUnavailable(RuntimeError):
    pass


class DiscoveryPort(Protocol):
    async def search(self, query: str) -> list[LivestreamResult]: ...


def normalize_query(query: str) -> str:
    return " ".join(query.split())


def verified_live_results(results: Iterable[LivestreamResult]) -> list[LivestreamResult]:
    unique: dict[str, LivestreamResult] = {}

    for result in results:
        if not result.is_live or result.is_replay:
            continue
        unique.setdefault(result.id, result)

    return list(unique.values())
