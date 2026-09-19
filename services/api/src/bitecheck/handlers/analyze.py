"""POST /v1/analyze - the main orchestrator.

Pipeline:
  1. resolve      URL -> ASIN + slug title
  2. cache        DynamoDB lookup, return early on a warm hit
  3. catalog      merge curated attributes
  4. normalize    brand/product/category + the food gate (short-circuits non-food)
  5. nutrition    label -> Open Food Facts -> catalog, normalized to per-100g
  6. retrieve     Bedrock Retrieve against the knowledge base
  7. assess       Converse with a strict schema over those chunks
  8. ground       drop anything the chunks do not support
  9. cache write  and return

Thin by design: no logic lives here, only sequencing and HTTP shaping.
"""

from __future__ import annotations

from typing import Any


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """TODO(saket)"""
    raise NotImplementedError
