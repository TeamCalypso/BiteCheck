"""Bedrock clients: runtime (Converse) and agent-runtime (Retrieve).

Clients are module-level so they are reused across warm Lambda invocations. Timeouts are
short and explicit: a slow Bedrock call must fail fast rather than burn the API Gateway
29-second budget.
"""

from __future__ import annotations

from typing import Any


def converse(model_id: str, system: str, messages: list[dict[str, Any]], tool_schema: dict | None = None) -> dict:
    """Single Converse call. When tool_schema is given, force a tool-use JSON response.

    TODO(saket)
    """
    raise NotImplementedError


def retrieve(knowledge_base_id: str, query: str, top_k: int, metadata_filter: dict | None = None) -> dict:
    """Raw bedrock-agent-runtime.retrieve response.

    TODO(saket)
    """
    raise NotImplementedError


def resolve_model_ids() -> dict[str, str]:
    """Discover callable model/inference-profile IDs for this account.

    Newer Claude models require an inference profile ID rather than a bare model ID, and
    which are enabled varies per account, so we never hardcode them.

    TODO(saket): used by scripts/bootstrap_kb.py, not at request time.
    """
    raise NotImplementedError
