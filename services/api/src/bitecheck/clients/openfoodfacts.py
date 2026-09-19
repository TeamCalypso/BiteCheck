"""Open Food Facts client - free, no API key, good Indian coverage.

Treated as strictly optional. If it is slow or down we return the analysis without
nutrition rather than failing the request: a safety verdict with no swarm is far better
than no verdict at all. Every failure mode here (timeout, non-200, malformed JSON, no
match) returns None - this function must never raise.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any
from urllib.parse import urlencode

import urllib3

logger = logging.getLogger(__name__)

SEARCH_URL = "https://world.openfoodfacts.org/api/v2/search"
FIELDS = "code,product_name,brands,nutriments,additives_tags,nova_group,ingredients_text"
USER_AGENT = "BiteCheck/0.1 (hackathon project; https://github.com/TeamCalypso/BiteCheck)"


@lru_cache(maxsize=1)
def _pool() -> urllib3.PoolManager:
    return urllib3.PoolManager()


def _best_match(products: list[dict[str, Any]], brand: str | None) -> dict[str, Any] | None:
    """Open Food Facts' own relevance ranking is decent but brand-blind. If we have a
    brand hint, prefer the first result whose `brands` field actually contains it."""
    if not products:
        return None
    if brand:
        brand_lower = brand.lower()
        for product in products:
            if brand_lower in (product.get("brands") or "").lower():
                return product
    return products[0]


def search(brand: str | None, product: str, timeout_s: float = 2.5) -> dict[str, Any] | None:
    """Best matching product, or None. Never raises - callers treat failure as 'no data'.

    Returns the raw OFF product object (with `nutriments`, `additives_tags`, `nova_group`,
    etc.) as-is; core/nutrition.py's `_from_off_payload()` is what actually interprets it.
    """
    query = f"{brand} {product}".strip() if brand else product
    if not query:
        return None

    params = urlencode({"search_terms": query, "fields": FIELDS, "page_size": 5, "json": 1})
    url = f"{SEARCH_URL}?{params}"

    try:
        response = _pool().request(
            "GET",
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=urllib3.Timeout(connect=1.5, read=timeout_s),
            retries=False,
        )
    except Exception:
        logger.warning("Open Food Facts request failed for query=%r", query, exc_info=True)
        return None

    if response.status != 200:
        logger.warning("Open Food Facts returned status %s for query=%r", response.status, query)
        return None

    try:
        payload = json.loads(response.data.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.warning("Open Food Facts returned unparseable JSON for query=%r", query)
        return None

    return _best_match(payload.get("products") or [], brand)
