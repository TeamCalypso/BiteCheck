"""The global cache.

A trending product should not cost a Bedrock call every time someone looks at it. Results
are keyed by ASIN in DynamoDB with a 24h TTL and an atomic hit counter; the TrendingIndex
GSI turns that counter into the "live advisories" list the web app shows on load
(`GET /v1/trending`, see handlers/trending.py).
"""

from __future__ import annotations

import json
import time
from typing import Any

from bitecheck.clients import ddb

TREND_BUCKET = "TREND"


def _now() -> int:
    return int(time.time())


def get(asin: str) -> dict[str, Any] | None:
    """Return a cached analysis if one exists and has not expired.

    DynamoDB's own TTL deletion is a background sweep that can lag by minutes to hours
    after the ttl timestamp passes, so we also check `ttl` ourselves rather than trusting
    that an expired item is already gone.
    """
    try:
        response = ddb.cache_table().get_item(Key={"asin": asin})
    except Exception:
        return None

    item = response.get("Item")
    if not item:
        return None
    if item.get("ttl") and int(item["ttl"]) < _now():
        return None

    try:
        return json.loads(item["payload"])
    except (KeyError, TypeError, json.JSONDecodeError):
        return None


def put(asin: str, payload: dict[str, Any], ttl_seconds: int) -> None:
    """Store an analysis and initialise its counters (hitCount starts at 1: this write
    itself represents the request that produced it)."""
    verdict = payload.get("verdict") or {}
    product = payload.get("product") or {}
    ddb.cache_table().put_item(
        Item={
            "asin": asin,
            "payload": json.dumps(payload),
            "verdictStatus": verdict.get("status", "NO_DATA"),
            "brand": product.get("brand") or "",
            "productName": product.get("name") or "",
            "hitCount": 1,
            "lastAccessed": _now(),
            "ttl": _now() + ttl_seconds,
            "trendBucket": TREND_BUCKET,
        }
    )


def record_hit(asin: str) -> int:
    """Atomically increment hitCount and refresh lastAccessed. Returns the new count."""
    response = ddb.cache_table().update_item(
        Key={"asin": asin},
        UpdateExpression="ADD hitCount :one SET lastAccessed = :now",
        ExpressionAttributeValues={":one": 1, ":now": _now()},
        ReturnValues="UPDATED_NEW",
    )
    return int(response["Attributes"]["hitCount"])


def trending(limit: int = 20) -> list[dict[str, Any]]:
    """Query TrendingIndex descending by hitCount. No Bedrock cost - pure DynamoDB read."""
    response = ddb.cache_table().query(
        IndexName="TrendingIndex",
        KeyConditionExpression="trendBucket = :t",
        ExpressionAttributeValues={":t": TREND_BUCKET},
        ScanIndexForward=False,
        Limit=limit,
    )
    return [
        {
            "asin": item["asin"],
            "brand": item.get("brand") or None,
            "productName": item.get("productName") or None,
            "verdictStatus": item.get("verdictStatus"),
            "hitCount": int(item.get("hitCount", 0)),
        }
        for item in response.get("Items", [])
    ]
