"""core/local_retrieval.py tests. Index is monkeypatched to a small fixture set - no
dependency on the real (and growing) bundled corpus_index.json.
"""

from __future__ import annotations

import pytest

from bitecheck.core import local_retrieval

FIXTURE_INDEX = [
    {
        "id": "fssai/recalls/foscos-recall-11.md",
        "text": "FSSAI FoSCoS Food Recall - Recall ID 11. Everest Tikhalal chilly powder. "
        "Reason: Unsafe food. Pesticide residue exceeded limits.",
        "issuer": "FSSAI",
        "docType": "recall",
        "category": "spices_blends",
        "date": "2025-01-07",
        "brands": ["Everest Tikhalal chilly powder"],
        "hazards": [],
        "orderRef": "FoSCoS Recall ID 11",
        "sourceUrl": "https://foscos.fssai.gov.in/food-recall",
    },
    {
        "id": "fssai/recalls/foscos-recall-13.md",
        "text": "FSSAI FoSCoS Food Recall - Recall ID 13. KESHAV GHEE. Reason: not per standards.",
        "issuer": "FSSAI",
        "docType": "recall",
        "category": "oils_fats",
        "date": "2025-03-13",
        "brands": ["KESHAV GHEE"],
        "hazards": [],
        "orderRef": "FoSCoS Recall ID 13",
        "sourceUrl": "https://foscos.fssai.gov.in/food-recall",
    },
    {
        "id": "fssai/fssai_labelling_display_regulations_2020.md",
        "text": "Food Safety and Standards (Labelling and Display) Regulations, 2020. "
        "Every package of food shall carry a label with the following information...",
        "issuer": "FSSAI",
        "docType": "regulation",
        "category": "other_food",
        "date": "2025-04-03",
        "brands": [],
        "hazards": [],
        "orderRef": "FSS (Labelling and Display) Regulations, 2020",
        "sourceUrl": "https://fssai.gov.in/",
    },
]


@pytest.fixture(autouse=True)
def fixture_index(monkeypatch):
    # Clear the real lru_cache before swapping it out, in case an earlier test (or import-
    # time call) already populated it. monkeypatch reverts the attribute automatically when
    # the test ends, so there's nothing to clean up afterward.
    local_retrieval._load_index.cache_clear()
    monkeypatch.setattr(local_retrieval, "_load_index", lambda: FIXTURE_INDEX)
    yield


class TestBrandMatching:
    def test_exact_brand_match_wins(self):
        chunks = local_retrieval.retrieve(brand="Everest", product_name="Chilly Powder")
        assert chunks
        assert chunks[0].chunk_id == "fssai/recalls/foscos-recall-11.md"

    def test_brand_substring_matches_either_direction(self):
        # doc brand "Everest Tikhalal chilly powder" contains query "Everest"
        chunks = local_retrieval.retrieve(brand="Everest", product_name="anything")
        assert any(c.chunk_id == "fssai/recalls/foscos-recall-11.md" for c in chunks)

    def test_unrelated_brand_returns_nothing(self):
        chunks = local_retrieval.retrieve(brand="Totally Unrelated Brand XYZ", product_name="Widget")
        assert chunks == []

    def test_no_brand_given_falls_back_to_category_and_text(self):
        chunks = local_retrieval.retrieve(brand=None, product_name="ghee", category="oils_fats")
        assert chunks
        assert chunks[0].chunk_id == "fssai/recalls/foscos-recall-13.md"


class TestGrounding:
    def test_citations_come_from_document_metadata(self):
        chunks = local_retrieval.retrieve(brand="Everest", product_name="Chilly Powder")
        c = chunks[0]
        assert c.issuer == "FSSAI"
        assert c.label == "FoSCoS Recall ID 11"
        assert c.date == "2025-01-07"
        assert c.source_url == "https://foscos.fssai.gov.in/food-recall"

    def test_empty_index_returns_nothing_not_error(self, monkeypatch):
        monkeypatch.setattr(local_retrieval, "_load_index", lambda: [])
        assert local_retrieval.retrieve(brand="Everest", product_name="x") == []

    def test_respects_top_k(self):
        chunks = local_retrieval.retrieve(brand=None, product_name="food label package", top_k=1)
        assert len(chunks) <= 1


class TestRelevanceFloor:
    def test_weak_text_only_overlap_is_not_enough(self):
        """A document sharing a couple of generic words with the query, but no brand or
        category signal, must not be treated as grounding evidence."""
        chunks = local_retrieval.retrieve(brand="Nonexistent Co", product_name="food")
        assert chunks == []
