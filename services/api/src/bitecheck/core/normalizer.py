"""Entity normalization and the food gate.

Amazon titles and regulator circulars never use the same words. A listing says
"Everest Super Garam Masala 100g Pouch (Pack of 2)" while a circular says
"Everest Food Products Pvt Ltd - Garam Masala Powder". String matching fails here, so a
cheap Bedrock model collapses both into {brand, product, category} before retrieval.

The same call answers "is this even food?", which is the gate the web flow needs before
spending money on RAG.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedProduct:
    brand: str | None
    name: str
    category: str
    is_food_product: bool
    net_quantity: str | None = None
    confidence: str = "MEDIUM"


def normalize(
    title: str,
    brand_hint: str | None = None,
    bullets: list[str] | None = None,
) -> NormalizedProduct:
    """Collapse a raw listing title into a canonical product identity.

    TODO(saket): Bedrock Converse against config.fast_model_id with a tool-use schema.
    """
    raise NotImplementedError


def build_retrieval_query(product: NormalizedProduct) -> str:
    """Phrase the knowledge base query in the language regulators use, not marketing copy.

    TODO(saket)
    """
    raise NotImplementedError
