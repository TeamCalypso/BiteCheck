"""handlers/trending.py tests against a moto-mocked DynamoDB (see conftest.py)."""

import json

from bitecheck.core import cache
from bitecheck.handlers import trending


def sample_payload(asin):
    return {
        "requestId": "r1", "asin": asin, "cached": False,
        "verdict": {"status": "CLEAR", "score": 90, "headline": "h", "summary": "s"},
        "product": {"brand": "Acme", "name": "Widget", "category": "other_food", "isFoodProduct": True},
        "findings": [], "disclaimer": "d",
    }


class TestTrendingHandler:
    def test_empty_when_nothing_cached(self, ddb_tables):
        result = trending.handler({}, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["items"] == []
        assert body["count"] == 0

    def test_returns_cached_items_ordered_by_hits(self, ddb_tables):
        cache.put("B0LOW000001", sample_payload("B0LOW000001"), ttl_seconds=86400)
        cache.put("B0HIGH000001", sample_payload("B0HIGH000001"), ttl_seconds=86400)
        for _ in range(3):
            cache.record_hit("B0HIGH000001")

        result = trending.handler({}, None)
        body = json.loads(result["body"])
        assert body["items"][0]["asin"] == "B0HIGH000001"

    def test_respects_limit_query_param(self, ddb_tables):
        for i in range(5):
            cache.put(f"B0ITEM{i:06d}", sample_payload(f"B0ITEM{i:06d}"), ttl_seconds=86400)

        result = trending.handler({"queryStringParameters": {"limit": "2"}}, None)
        body = json.loads(result["body"])
        assert body["count"] == 2

    def test_invalid_limit_falls_back_to_default(self, ddb_tables):
        result = trending.handler({"queryStringParameters": {"limit": "not-a-number"}}, None)
        assert result["statusCode"] == 200
