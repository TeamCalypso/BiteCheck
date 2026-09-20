"""Nutrition module tests.

This is the file whose output the web app's swarm visual depends on directly - if pct
doesn't sum to 100, the split animation is visibly wrong. Test that invariant hard.
"""

import pytest

from bitecheck.clients import bedrock
from bitecheck.core.nutrition import build, close_to_hundred, parse_label_value


class TestParseLabelValue:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("24 g", 24.0),
            ("24g", 24.0),
            ("1.2mg", 0.0012),
            ("500 mcg", 0.0005),
            ("<0.5 g", 0.5),
            ("~1 g", 1.0),
            ("1,200mg", 1.2),
            ("0 g", 0.0),
        ],
    )
    def test_parses_common_formats(self, raw, expected):
        assert parse_label_value(raw) == pytest.approx(expected)

    def test_energy_units_return_none(self):
        assert parse_label_value("120 kcal") is None
        assert parse_label_value("500 kJ") is None

    @pytest.mark.parametrize("raw", [None, "", "n/a", "not a number"])
    def test_unparseable_returns_none(self, raw):
        assert parse_label_value(raw) is None


class TestCloseToHundred:
    def test_adds_other_bucket_for_remainder(self):
        macros = [{"key": "protein", "label": "Protein", "grams": 24.0, "class": "GOOD"}]
        result = close_to_hundred(macros)
        keys = {m["key"] for m in result}
        assert "other" in keys
        assert sum(m["pct"] for m in result) == pytest.approx(100.0, abs=0.05)

    def test_no_other_bucket_when_already_100(self):
        macros = [
            {"key": "protein", "label": "Protein", "grams": 60.0, "class": "GOOD"},
            {"key": "fat", "label": "Fat", "grams": 40.0, "class": "NEUTRAL"},
        ]
        result = close_to_hundred(macros)
        assert not any(m["key"] == "other" for m in result)
        assert sum(m["pct"] for m in result) == pytest.approx(100.0, abs=0.05)

    def test_scales_down_when_over_100(self):
        """Bad source data that overshoots 100g must not produce a negative 'other'."""
        macros = [
            {"key": "protein", "label": "Protein", "grams": 70.0, "class": "GOOD"},
            {"key": "fat", "label": "Fat", "grams": 50.0, "class": "NEUTRAL"},
        ]
        result = close_to_hundred(macros)
        assert all(m["pct"] >= 0 for m in result)
        assert sum(m["pct"] for m in result) == pytest.approx(100.0, abs=0.05)

    def test_rounding_drift_absorbed_not_left_over(self):
        macros = [
            {"key": "protein", "label": "Protein", "grams": 33.33, "class": "GOOD"},
            {"key": "fat", "label": "Fat", "grams": 33.33, "class": "NEUTRAL"},
            {"key": "carbohydrate", "label": "Carbs", "grams": 33.34, "class": "NEUTRAL"},
        ]
        result = close_to_hundred(macros)
        assert sum(m["pct"] for m in result) == pytest.approx(100.0, abs=0.01)

    def test_empty_input_yields_a_single_unknown_bucket(self):
        """No data at all still has to render *something* in the swarm - a 100% unknown
        slice is more honest and more useful than an empty list."""
        result = close_to_hundred([])
        assert result == [{"key": "other", "label": "Unspecified", "grams": 100.0, "class": "UNKNOWN", "pct": 100.0}]


class TestBuild:
    def test_prefers_label_rows_over_everything(self):
        label_rows = [
            {"name": "Protein", "per100g": "24 g"},
            {"name": "Total Carbohydrate", "per100g": "50 g"},
            {"name": "Total Fat", "per100g": "10 g"},
        ]
        n = build(label_rows, off_payload={"nutriments": {"proteins_100g": 999}}, catalog_nutrition=None)
        assert n.source == "amazon_label"
        assert n.confidence == "HIGH"

    def test_falls_back_to_openfoodfacts(self):
        off = {"nutriments": {
            "proteins_100g": 24, "carbohydrates_100g": 50, "fat_100g": 10,
        }}
        n = build(label_rows=None, off_payload=off, catalog_nutrition={"protein": 1})
        assert n.source == "openfoodfacts"

    def test_falls_back_to_catalog(self):
        catalog = {"protein": 24.0, "carbohydrate": 50.0, "fat": 10.0}
        n = build(label_rows=None, off_payload=None, catalog_nutrition=catalog)
        assert n.source == "catalog"

    def test_returns_none_when_nothing_available(self):
        assert build(None, None, None) is None

    def test_sparse_label_rows_do_not_count_as_a_source(self):
        """A single stray matched row (e.g. only 'Sodium') should not be trusted alone."""
        label_rows = [{"name": "Sodium", "per100g": "400mg"}]
        off = {"nutriments": {"proteins_100g": 10, "carbohydrates_100g": 20, "fat_100g": 5}}
        n = build(label_rows, off, None)
        assert n.source == "openfoodfacts"

    def test_macros_always_sum_to_100(self):
        label_rows = [
            {"name": "Protein", "per100g": "13.5 g"},
            {"name": "Total Carbohydrate", "per100g": "41.2 g"},
            {"name": "Total Fat", "per100g": "15.0 g"},
            {"name": "Dietary Fiber", "per100g": "22.1 g"},
            {"name": "Sodium", "per100g": "1.2 g"},
        ]
        n = build(label_rows, None, None)
        assert sum(m["pct"] for m in n.macros) == pytest.approx(100.0, abs=0.05)

    def test_sugar_is_netted_out_of_carbohydrate(self):
        """Sugar is a subset of total carbs - the swarm needs disjoint slices."""
        label_rows = [
            {"name": "Protein", "per100g": "10 g"},
            {"name": "Total Carbohydrate", "per100g": "20 g"},
            {"name": "Total Sugars", "per100g": "8 g"},
            {"name": "Total Fat", "per100g": "5 g"},
        ]
        n = build(label_rows, None, None)
        by_key = {m["key"]: m for m in n.macros}
        assert by_key["carbohydrate"]["grams"] == pytest.approx(12.0)  # 20 - 8
        assert by_key["sugar"]["grams"] == pytest.approx(8.0)

    def test_saturated_fat_is_netted_out_of_fat(self):
        label_rows = [
            {"name": "Protein", "per100g": "10 g"},
            {"name": "Total Carbohydrate", "per100g": "20 g"},
            {"name": "Total Fat", "per100g": "15 g"},
            {"name": "Saturated Fat", "per100g": "5 g"},
        ]
        n = build(label_rows, None, None)
        by_key = {m["key"]: m for m in n.macros}
        assert by_key["fat"]["grams"] == pytest.approx(10.0)  # 15 - 5
        assert by_key["saturated_fat"]["grams"] == pytest.approx(5.0)

    def test_high_sugar_flag(self):
        label_rows = [
            {"name": "Protein", "per100g": "5 g"},
            {"name": "Total Carbohydrate", "per100g": "30 g"},
            {"name": "Total Sugars", "per100g": "15 g"},
            {"name": "Total Fat", "per100g": "2 g"},
        ]
        n = build(label_rows, None, None)
        codes = {f["code"] for f in n.flags}
        assert "ADDED_SUGAR_HIGH" in codes

    def test_openfoodfacts_sodium_falls_back_to_salt(self):
        off = {"nutriments": {
            "proteins_100g": 10, "carbohydrates_100g": 20, "fat_100g": 5, "salt_100g": 2.5,
        }}
        n = build(None, off, None)
        by_key = {m["key"]: m for m in n.macros}
        assert by_key["sodium"]["grams"] == pytest.approx(1.0)  # 2.5 / 2.5

    def test_nova_group_passed_through(self):
        off = {"nutriments": {"proteins_100g": 10, "carbohydrates_100g": 20, "fat_100g": 5}, "nova_group": 4}
        n = build(None, off, None)
        assert n.nova_group == 4

    def test_additives_extracted_from_off_tags(self):
        off = {
            "nutriments": {"proteins_100g": 10, "carbohydrates_100g": 20, "fat_100g": 5},
            "additives_tags": ["en:e951", "en:e322"],
        }
        n = build(None, off, None)
        names = {a["ins"] for a in n.additives}
        assert "E951" in names and "E322" in names


class TestAiEstimateFallback:
    """The last-resort path for products with no label, no OFF match, and no catalog
    entry - e.g. a judge pasting an arbitrary Amazon link that isn't one of the seeded
    demo ASINs. See the module docstring for why this is safe (never touches findings[]
    or the grounding guard) and always low-confidence."""

    def test_not_attempted_without_a_product_name(self, monkeypatch):
        called = []
        monkeypatch.setattr(bedrock, "converse", lambda **kw: called.append(kw) or {})
        assert build(None, None, None) is None
        assert called == []

    def test_falls_back_to_ai_estimate_when_every_real_source_is_empty(self, monkeypatch):
        monkeypatch.setattr(
            bedrock,
            "converse",
            lambda **kw: {"protein": 8.0, "carbohydrate": 60.0, "fat": 3.0, "sodium": 0.02},
        )
        n = build(None, None, None, brand="Everest", name="Garam Masala", category="spices_blends")
        assert n is not None
        assert n.source == "ai_estimate"
        assert n.confidence == "LOW"

    def test_ai_estimate_is_flagged_for_transparency(self, monkeypatch):
        monkeypatch.setattr(
            bedrock,
            "converse",
            lambda **kw: {"protein": 8.0, "carbohydrate": 60.0, "fat": 3.0},
        )
        n = build(None, None, None, brand=None, name="Some Unrecognized Snack", category="packaged_snacks")
        codes = {f["code"] for f in n.flags}
        assert "AI_ESTIMATED_NUTRITION" in codes

    def test_ai_estimate_macros_still_sum_to_100(self, monkeypatch):
        monkeypatch.setattr(
            bedrock,
            "converse",
            lambda **kw: {"protein": 12.5, "carbohydrate": 55.0, "fat": 9.0},
        )
        n = build(None, None, None, brand="Acme", name="Mystery Cereal", category="packaged_snacks")
        assert sum(m["pct"] for m in n.macros) == pytest.approx(100.0, abs=0.05)

    def test_sparse_ai_response_is_rejected(self, monkeypatch):
        """Only one usable macro back - same 'don't trust a lone value' rule as label rows."""
        monkeypatch.setattr(bedrock, "converse", lambda **kw: {"protein": 8.0})
        assert build(None, None, None, brand="Acme", name="Mystery Item") is None

    def test_llm_failure_degrades_to_no_nutrition_not_an_exception(self, monkeypatch):
        def boom(**kw):
            raise RuntimeError("quota exceeded")

        monkeypatch.setattr(bedrock, "converse", boom)
        assert build(None, None, None, brand="Acme", name="Mystery Item") is None

    def test_never_attempted_when_a_real_source_already_worked(self, monkeypatch):
        called = []
        monkeypatch.setattr(bedrock, "converse", lambda **kw: called.append(kw) or {})
        catalog = {"protein": 24.0, "carbohydrate": 50.0, "fat": 10.0}
        n = build(None, None, catalog, brand="Everest", name="Garam Masala")
        assert n.source == "catalog"
        assert called == []
