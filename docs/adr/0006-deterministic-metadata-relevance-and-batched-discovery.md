# Filter candidate broadcasts by normalized metadata keywords and return in batches of 10

LiveScout will filter candidate livestreams using deterministic normalized keyword matching on candidate title and source metadata, and will return discovery results in batches of 10 verified live broadcasts per search or continuation request. This prevents broad queries like `news` from returning off-topic broadcasts surfaced by Facebook's discovery algorithms, maintains local deterministic execution without external AI dependencies, and provides predictable pagination and exhaustion signaling.

## Status

Accepted

## Considered Options

- **Rely solely on Facebook search page ranking**: Rejected because Facebook search surfaces frequently include recommended or trending broadcasts that have no relation to the requested query (e.g. gaming broadcasts returned for `news`).
- **Use external AI / ML topic classification**: Rejected because it introduces external API costs, network dependencies, non-determinism, and latency, violating the local-first web application principles.
- **Fixed-size candidate page fetching without live-verification target**: Rejected because candidate streams frequently fail live verification (ended, replay, login wall), resulting in unpredictable batch sizes if verification happens after pagination.

## Consequences

- Candidate discovery engine must scan public surfaces iteratively until 10 verified, relevant, live broadcasts are collected or public discovery surface is exhausted.
- Query normalization must identify non-generic keywords for relevance matching.
- The `POST /api/search` contract must support pagination parameters (e.g. `cursor`/`offset`) and an explicit `has_more` field.
