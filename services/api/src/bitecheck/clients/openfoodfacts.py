"""Open Food Facts client - free, no API key, good Indian coverage.

Treated as strictly optional. If it is slow or down we return the analysis without
nutrition rather than failing the request: a safety verdict with no swarm is far better
than no verdict at all.
"""

from __future__ import annotations

from typing import Any

SEARCH_URL = "https://world.openfoodfacts.org/api/v2/search"
FIELDS = "code,product_name,brands,nutriments,additives_tags,nova_group,ingredients_text"
USER_AGENT = "BiteCheck/0.1 (hackathon project; https://github.com/TeamCalypso/BiteCheck)"


def search(brand: str | None, product: str, timeout_s: float = 2.5) -> dict[str, Any] | None:
    """Best matching product, or None. Never raises - callers treat failure as 'no data'.

    TODO(saket)
    """
    raise NotImplementedError
