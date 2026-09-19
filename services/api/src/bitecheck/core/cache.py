"""The global cache.

A trending product should not cost a Bedrock call every time someone looks at it. Results
are keyed by ASIN in DynamoDB with a 24h TTL and an atomic hit counter; the TrendingIndex
GSI turns that counter into the "live advisories" list the web app shows on load.
"""

from __future__ import annotations

from typing import Any

TREND_BUCKET = "TREND"


def get(asin: str) -> dict[str, Any] | None:
    """Return a cached analysis if one exists and has not expired.

    TODO(saket)
    """
    raise NotImplementedError


def put(asin: str, payload: dict[str, Any], ttl_seconds: int) -> None:
    """Store an analysis and initialise its counters.

    TODO(saket)
    """
    raise NotImplementedError


def record_hit(asin: str) -> int:
    """Atomically increment hitCount and refresh lastAccessed. Returns the new count.

    TODO(saket)
    """
    raise NotImplementedError


def trending(limit: int = 20) -> list[dict[str, Any]]:
    """Query TrendingIndex descending by hitCount.

    TODO(saket)
    """
    raise NotImplementedError
