"""core/normalizer.py tests. bedrock.converse is monkeypatched - no AWS access needed."""

import pytest

from bitecheck.clients import bedrock
from bitecheck.core import normalizer


class TestNormalize:
    def test_empty_title_short_circuits_without_calling_bedrock(self, monkeypatch):
        called = []
        monkeypatch.setattr(bedrock, "converse", lambda **kw: called.append(kw))
        result = normalizer.normalize("")
        assert result.is_food_product is False
        assert called == []

    def test_happy_path_maps_bedrock_response(self, monkeypatch):
        monkeypatch.setattr(
            bedrock,
            "converse",
            lambda **kw: {
                "brand": "Everest",
                "name": "Garam Masala Powder",
                "category": "spices_blends",
                "isFoodProduct": True,
                "netQuantity": "100 g",
                "confidence": "HIGH",
            },
        )
        result = normalizer.normalize(
            "Everest Super Garam Masala 100g Pouch (Pack of 2)", brand_hint="Everest Store"
        )
        assert result.brand == "Everest"
        assert result.name == "Garam Masala Powder"
        assert result.category == "spices_blends"
        assert result.is_food_product is True
        assert result.net_quantity == "100 g"
        assert result.confidence == "HIGH"

    def test_non_food_flag_is_honoured(self, monkeypatch):
        monkeypatch.setattr(
            bedrock,
            "converse",
            lambda **kw: {"brand": None, "name": "Wireless Mouse", "category": "non_food", "isFoodProduct": False},
        )
        result = normalizer.normalize("Wireless Mouse, 2.4 GHz")
        assert result.is_food_product is False
        assert result.category == "non_food"

    def test_bedrock_failure_falls_back_to_low_confidence_food_guess(self, monkeypatch):
        def boom(**kw):
            raise RuntimeError("Bedrock unavailable")

        monkeypatch.setattr(bedrock, "converse", boom)
        result = normalizer.normalize("Some Product Title")
        # Fails toward "attempt the analysis", not toward a false "not food" - see the
        # reasoning comment in normalizer.py.
        assert result.is_food_product is True
        assert result.confidence == "LOW"
        assert result.name == "Some Product Title"

    def test_brand_hint_and_bullets_reach_the_prompt(self, monkeypatch):
        captured = {}

        def fake_converse(**kw):
            captured.update(kw)
            return {"brand": "X", "name": "Y", "category": "other_food", "isFoodProduct": True}

        monkeypatch.setattr(bedrock, "converse", fake_converse)
        normalizer.normalize("Title", brand_hint="Brand Hint", bullets=["Bullet one", "Bullet two"])

        user_text = captured["messages"][0]["content"][0]["text"]
        assert "Brand Hint" in user_text
        assert "Bullet one" in user_text


class TestBuildRetrievalQuery:
    def test_includes_brand_and_name(self):
        product = normalizer.NormalizedProduct(
            brand="Everest", name="Garam Masala", category="spices_blends", is_food_product=True
        )
        query = normalizer.build_retrieval_query(product)
        assert "Everest" in query
        assert "Garam Masala" in query

    def test_omits_brand_when_none(self):
        product = normalizer.NormalizedProduct(
            brand=None, name="Turmeric Powder", category="spices_blends", is_food_product=True
        )
        query = normalizer.build_retrieval_query(product)
        assert query.startswith("Turmeric Powder")
