"""GET /v1/trending - most-requested products from the cache GSI.

Pure DynamoDB query, no AI, no Bedrock cost. Feeds the web app's live advisories panel -
see core/cache.py::trending() for the actual query against the TrendingIndex GSI.
"""

from __future__ import annotations

from typing import Any

from bitecheck.core import cache
from bitecheck.responses import error_response, json_response

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 50


def _parse_limit(event: dict[str, Any]) -> int:
    raw = (event.get("queryStringParameters") or {}).get("limit")
    if not raw:
        return _DEFAULT_LIMIT
    try:
        limit = int(raw)
    except ValueError:
        return _DEFAULT_LIMIT
    return max(1, min(limit, _MAX_LIMIT))


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    try:
        items = cache.trending(limit=_parse_limit(event))
    except Exception:
        # A trending-panel failure should degrade to "show nothing" for the caller, not a
        # 500 - but we do want it visible in logs, so this still surfaces as an error the
        # frontend can handle gracefully (empty state) rather than crash the page.
        return error_response(500, "Could not load trending products right now.")

    return json_response(200, {"items": items, "count": len(items)})
