"""DynamoDB access. Table resources are module-level for warm-start reuse.

Resources are created lazily (not at import time) so this module can be imported in tests
without live AWS credentials, and so a moto-mocked test can patch boto3 before the first
real call happens. `_config()`/`_dynamodb()` are cached with `lru_cache` for the lifetime
of a warm Lambda; tests that need a fresh mock call `.cache_clear()` on both between runs
(see tests/conftest.py).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import boto3

from bitecheck.config import Config


@lru_cache(maxsize=1)
def _config() -> Config:
    return Config.from_env()


@lru_cache(maxsize=1)
def _dynamodb():
    return boto3.resource("dynamodb", region_name=_config().region)


def cache_table():
    return _dynamodb().Table(_config().cache_table)


def catalog_table():
    return _dynamodb().Table(_config().catalog_table)


def get_catalog_entry(asin: str) -> dict[str, Any] | None:
    """Curated product attributes: verified nutrition, FSSAI licence, category.

    Enrichment only - verdicts always come from live retrieval, never from this table.
    Returns None on any DynamoDB error rather than raising: a catalog miss (or a catalog
    table hiccup) must not fail the whole analyze request.
    """
    try:
        response = catalog_table().get_item(Key={"asin": asin})
    except Exception:
        return None
    return response.get("Item")
