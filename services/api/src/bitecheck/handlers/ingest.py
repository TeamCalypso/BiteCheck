"""Scheduled corpus refresh (EventBridge, daily). No HTTP route.

Pulls new alerts from the public sources, normalizes them into the corpus bucket, and
triggers a Bedrock knowledge base ingestion job. This is what makes the knowledge base a
living pipeline rather than a one-time upload.
"""

from __future__ import annotations

from typing import Any


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """TODO(saket)"""
    raise NotImplementedError
