"""Entity normalization and the food gate.

Amazon titles and regulator circulars never use the same words. A listing says
"Everest Super Garam Masala 100g Pouch (Pack of 2)" while a circular says
"Everest Food Products Pvt Ltd - Garam Masala Powder". String matching fails here, so a
cheap Bedrock model collapses both into {brand, product, category} before retrieval.

The same call answers "is this even food?", which is the gate the web flow needs before
spending money on RAG (see handlers/analyze.py: isFoodProduct=false short-circuits to
NO_DATA immediately).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from bitecheck.clients import bedrock
from bitecheck.config import Config

logger = logging.getLogger(__name__)

# Keep in sync with the Category enum in contract/analyze.schema.json.
_CATEGORIES = [
    "spices_blends", "supplements_protein", "dairy_perishable", "packaged_snacks",
    "beverages", "infant_food", "oils_fats", "staples_grains", "confectionery",
    "ready_to_eat", "other_food", "non_food",
]

_TOOL_SCHEMA = {
    "type": "object",
    "required": ["brand", "name", "category", "isFoodProduct"],
    "properties": {
        "brand": {
            "type": ["string", "null"],
            "description": "The manufacturer/brand name, as a regulator would refer to it, or null if not identifiable.",
        },
        "name": {
            "type": "string",
            "description": "A clean, canonical product name - no pack-size counts or marketing filler.",
        },
        "category": {"type": "string", "enum": _CATEGORIES},
        "isFoodProduct": {
            "type": "boolean",
            "description": "False for anything not eaten, drunk, or taken as a supplement (electronics, clothing, kitchenware, books, toys, etc).",
        },
        "netQuantity": {
            "type": ["string", "null"],
            "description": "e.g. '100 g', '1 kg', '500 ml', only if clearly stated.",
        },
        "confidence": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
    },
}

_SYSTEM_PROMPT = """\
You normalize noisy Amazon India product listings into a clean product identity for a food
safety lookup. You are given a raw listing title, an optional brand hint from the page
byline, and optional bullet points.

Rules:
- Strip marketing language, pack-size counts, and promotional phrasing from `name`; keep
  only what identifies the product itself, e.g. "Garam Masala Powder" not
  "NEW! Everest Super Garam Masala 100g Value Pack (Pack of 2) - FSSAI Certified".
- `brand` should match how a regulator would refer to the company, not the Amazon
  storefront name (e.g. "Everest", not "Everest Food Products Pvt Ltd Official Store").
- Set isFoodProduct to false for anything that is not eaten, drunk, or taken as a
  supplement.
- If genuinely unsure of the category, prefer "other_food" (if it is food) rather than
  guessing a specific category wrong.
- Set confidence to LOW if the title is too sparse or ambiguous to be sure of any of this.
"""


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
    """Collapse a raw listing title into a canonical product identity via Bedrock."""
    if not title or not title.strip():
        # No title to work with at all - the honest outcome is "we cannot identify this",
        # not a guess. handlers/analyze.py treats isFoodProduct=False as NO_DATA/notFood.
        return NormalizedProduct(
            brand=None, name="Unknown product", category="non_food",
            is_food_product=False, confidence="LOW",
        )

    user_text = f"Title: {title}"
    if brand_hint:
        user_text += f"\nBrand (from page byline): {brand_hint}"
    if bullets:
        user_text += "\nListing bullet points:\n" + "\n".join(f"- {b}" for b in bullets[:5])

    config = Config.from_env()
    try:
        result = bedrock.converse(
            model_id=config.fast_model_id,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": [{"text": user_text}]}],
            tool_schema=_TOOL_SCHEMA,
        )
    except Exception:
        logger.exception("normalize() Bedrock call failed for title=%r", title)
        # Fail toward attempting the analysis as food with low confidence, not toward a
        # false "not food" - retrieval will legitimately come up NO_DATA if this guess is
        # wrong, whereas a false "not food" silently tells a shopper nothing was checked.
        return NormalizedProduct(
            brand=brand_hint, name=title, category="other_food",
            is_food_product=True, confidence="LOW",
        )

    return NormalizedProduct(
        brand=result.get("brand"),
        name=result.get("name") or title,
        category=result.get("category", "other_food"),
        is_food_product=bool(result.get("isFoodProduct", True)),
        net_quantity=result.get("netQuantity"),
        confidence=result.get("confidence", "MEDIUM"),
    )


def build_retrieval_query(product: NormalizedProduct) -> str:
    """Phrase the knowledge base query in the language regulators use, not marketing copy."""
    parts = []
    if product.brand:
        parts.append(product.brand)
    parts.append(product.name)
    parts.append(
        "recall OR contamination OR adulteration OR pesticide residue OR ethylene oxide "
        "OR mislabelling OR misleading claim OR safety notice"
    )
    return " ".join(parts)
