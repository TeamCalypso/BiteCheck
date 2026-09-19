"""Generation half of the RAG pipeline.

Takes retrieved chunks and produces {verdict, findings} through a strict tool-use schema.
Split from rag.py so retrieval tuning and prompt tuning do not fight each other.

Whatever comes out of here is still untrusted: it goes through grounding.enforce() before
it reaches a user.
"""

from __future__ import annotations

from typing import Any

from bitecheck.core.grounding import RetrievedChunk
from bitecheck.core.normalizer import NormalizedProduct

SYSTEM_PROMPT = """\
You are a food safety analyst. You are given a product identity and a set of excerpts from
official regulator and laboratory documents.

Rules you must not break:
- Every finding must cite at least one excerpt by its exact label. Never cite a document
  that is not in the excerpts provided.
- If the excerpts do not mention this brand or product, say so by returning no findings.
  Do not generalise from the category to the product.
- Distinguish scope carefully: a recall of specific batches is BATCH, not BRAND.
- Never infer a violation from marketing language alone.
- Plain language. The reader is a shopper, not a regulator.
"""


def assess(
    product: NormalizedProduct,
    chunks: list[RetrievedChunk],
    nutrition: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return {"verdict": {...}, "findings": [...]} - unvalidated, pre-grounding.

    TODO(saket/mahek)
    """
    raise NotImplementedError


def score_from_findings(findings: list[dict[str, Any]]) -> int:
    """Map findings onto the 0-100 gauge value.

    TODO(saket)
    """
    raise NotImplementedError
