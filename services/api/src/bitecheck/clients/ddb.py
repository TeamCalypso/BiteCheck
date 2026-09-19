"""DynamoDB access. Table resources are module-level for warm-start reuse."""

from __future__ import annotations

from typing import Any


def cache_table():
    """TODO(saket)"""
    raise NotImplementedError


def catalog_table():
    """TODO(saket)"""
    raise NotImplementedError


def get_catalog_entry(asin: str) -> dict[str, Any] | None:
    """Curated product attributes: verified nutrition, FSSAI licence, category.

    Enrichment only. Verdicts always come from live retrieval.

    TODO(saket)
    """
    raise NotImplementedError
