"""core/cache.py tests against a moto-mocked DynamoDB table (see conftest.py)."""

from bitecheck.core import cache


def sample_payload(status="CLEAR", asin="B0TEST1234"):
    return {
        "requestId": "r1",
        "asin": asin,
        "cached": False,
        "verdict": {"status": status, "score": 90, "headline": "h", "summary": "s"},
        "product": {"brand": "Acme", "name": "Widget", "category": "other_food", "isFoodProduct": True},
        "findings": [],
        "disclaimer": "d",
    }


class TestGetPut:
    def test_get_returns_none_when_absent(self, ddb_tables):
        assert cache.get("B0MISSING01") is None

    def test_put_then_get_roundtrips(self, ddb_tables):
        cache.put("B0TEST1234", sample_payload(), ttl_seconds=86400)
        result = cache.get("B0TEST1234")
        assert result["asin"] == "B0TEST1234"
        assert result["verdict"]["status"] == "CLEAR"

    def test_expired_item_is_treated_as_a_miss(self, ddb_tables):
        cache.put("B0EXPIRED01", sample_payload(asin="B0EXPIRED01"), ttl_seconds=-10)
        assert cache.get("B0EXPIRED01") is None


class TestRecordHit:
    def test_increments_from_one(self, ddb_tables):
        cache.put("B0TEST1234", sample_payload(), ttl_seconds=86400)
        assert cache.record_hit("B0TEST1234") == 2
        assert cache.record_hit("B0TEST1234") == 3

    def test_creates_counter_if_never_put(self, ddb_tables):
        # DynamoDB's ADD on a missing item creates it - defensive behaviour, though in
        # practice analyze.py always put()s before a cache hit can record_hit().
        assert cache.record_hit("B0NEVERPUT1") == 1


class TestTrending:
    def test_empty_when_nothing_cached(self, ddb_tables):
        assert cache.trending() == []

    def test_orders_by_hit_count_descending(self, ddb_tables):
        cache.put("B0LOW000001", sample_payload(asin="B0LOW000001"), ttl_seconds=86400)
        cache.put("B0HIGH000001", sample_payload(asin="B0HIGH000001"), ttl_seconds=86400)
        for _ in range(5):
            cache.record_hit("B0HIGH000001")

        result = cache.trending(limit=10)
        asins = [r["asin"] for r in result]
        assert asins.index("B0HIGH000001") < asins.index("B0LOW000001")

    def test_respects_limit(self, ddb_tables):
        for i in range(5):
            cache.put(f"B0ITEM{i:06d}", sample_payload(asin=f"B0ITEM{i:06d}"), ttl_seconds=86400)
        assert len(cache.trending(limit=3)) == 3
