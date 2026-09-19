"""Retrieval half of the RAG pipeline.

We deliberately call Bedrock `Retrieve` rather than `RetrieveAndGenerate`. RetrieveAndGenerate
hands back prose we would then have to re-parse, and its citation structure is not ours to
control. Retrieve gives us the raw chunks plus their metadata, which is exactly what
grounding.py needs to verify the model later.
"""

from __future__ import annotations

from bitecheck.core.grounding import RetrievedChunk


def retrieve(query: str, category: str | None = None, top_k: int = 8) -> list[RetrievedChunk]:
    """Query the knowledge base, optionally filtered by document category metadata.

    TODO(saket): bedrock-agent-runtime.retrieve with vectorSearchConfiguration filter.
    """
    raise NotImplementedError
