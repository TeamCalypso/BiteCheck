"""clients/openfoodfacts.py tests. The HTTP call is faked - no real network access."""

import json

import pytest

from bitecheck.clients import openfoodfacts


class FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self.data = json.dumps(body).encode("utf-8")


def fake_pool(monkeypatch, status=200, body=None):
    pool = openfoodfacts._pool()

    def fake_request(method, url, **kwargs):
        return FakeResponse(status, body if body is not None else {"products": []})

    monkeypatch.setattr(pool, "request", fake_request)
    return pool


class TestSearch:
    def test_returns_none_for_empty_query(self, monkeypatch):
        assert openfoodfacts.search(brand=None, product="") is None

    def test_returns_none_when_no_products_found(self, monkeypatch):
        fake_pool(monkeypatch, body={"products": []})
        assert openfoodfacts.search("Everest", "Garam Masala") is None

    def test_returns_first_result_when_no_brand_given(self, monkeypatch):
        products = [{"code": "1", "product_name": "A"}, {"code": "2", "product_name": "B"}]
        fake_pool(monkeypatch, body={"products": products})
        result = openfoodfacts.search(None, "Garam Masala")
        assert result["code"] == "1"

    def test_prefers_result_matching_the_brand_hint(self, monkeypatch):
        products = [
            {"code": "1", "brands": "Some Other Brand"},
            {"code": "2", "brands": "Everest Food Products"},
        ]
        fake_pool(monkeypatch, body={"products": products})
        result = openfoodfacts.search("Everest", "Garam Masala")
        assert result["code"] == "2"

    def test_falls_back_to_first_result_if_brand_not_found_in_any(self, monkeypatch):
        products = [{"code": "1", "brands": "Unrelated Brand"}]
        fake_pool(monkeypatch, body={"products": products})
        result = openfoodfacts.search("Everest", "Garam Masala")
        assert result["code"] == "1"

    def test_non_200_status_returns_none(self, monkeypatch):
        fake_pool(monkeypatch, status=503, body={})
        assert openfoodfacts.search("Everest", "Garam Masala") is None

    def test_network_exception_returns_none_not_raises(self, monkeypatch):
        pool = openfoodfacts._pool()

        def boom(method, url, **kwargs):
            raise TimeoutError("connection timed out")

        monkeypatch.setattr(pool, "request", boom)
        assert openfoodfacts.search("Everest", "Garam Masala") is None

    def test_malformed_json_returns_none(self, monkeypatch):
        pool = openfoodfacts._pool()

        class BadResponse:
            status = 200
            data = b"not json{{{"

        monkeypatch.setattr(pool, "request", lambda method, url, **kw: BadResponse())
        assert openfoodfacts.search("Everest", "Garam Masala") is None
