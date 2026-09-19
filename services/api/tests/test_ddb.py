"""clients/ddb.py tests against a moto-mocked DynamoDB table (see conftest.py)."""

from bitecheck.clients import ddb


class TestGetCatalogEntry:
    def test_returns_none_when_absent(self, ddb_tables):
        assert ddb.get_catalog_entry("B0MISSING01") is None

    def test_returns_item_when_present(self, ddb_tables):
        ddb.catalog_table().put_item(Item={"asin": "B0CATALOG1", "brand": "Acme", "name": "Widget"})
        entry = ddb.get_catalog_entry("B0CATALOG1")
        assert entry["brand"] == "Acme"

    def test_returns_none_on_table_error_instead_of_raising(self, ddb_tables, monkeypatch):
        """A catalog hiccup must not fail the whole analyze request."""

        def boom(**kwargs):
            raise RuntimeError("simulated DynamoDB failure")

        monkeypatch.setattr(ddb.catalog_table(), "get_item", boom)
        assert ddb.get_catalog_entry("B0ANY") is None
