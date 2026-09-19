"""GET /v1/trending - most-requested products from the cache GSI.

Pure DynamoDB query, no AI, no Bedrock cost. Feeds the web app's live advisories panel.
"""

from __future__ import annotations

from typing import Any


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """TODO(saket)"""
    raise NotImplementedError
