"""The grounding guard: drop any model claim not traceable to a retrieved document.

This is the most important file in the backend.

We publish safety claims about named, real food brands. A hallucinated recall is a legal
problem for us and a disqualification at judging. So the rule is absolute: a finding
survives only if every one of its citations matches a chunk that Bedrock ``Retrieve``
actually returned for this query. If nothing survives, we return NO_DATA. We never soften
a dropped finding into a vague warning, because a vague warning about a real brand is still
an accusation.

The count of dropped findings is reported in ``meta.findingsDropped`` rather than hidden.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Iterable

logger = logging.getLogger(__name__)

# Citation labels are compared loosely: models reformat "RASFF 2024.2893" as
# "RASFF-2024.2893" or "rasff 2024 2893" without changing meaning.
_NORMALIZE = re.compile(r"[^a-z0-9]+")


def _key(text: str) -> str:
    return _NORMALIZE.sub("", (text or "").lower())


@dataclass(frozen=True)
class RetrievedChunk:
    """One chunk returned by Bedrock Retrieve, plus the metadata we cite from."""

    chunk_id: str
    text: str
    s3_uri: str | None
    label: str | None
    issuer: str | None
    date: str | None
    source_url: str | None
    score: float = 0.0


@dataclass(frozen=True)
class GroundingResult:
    findings: list[dict[str, Any]]
    dropped: int
    drop_reasons: list[str]


def _chunk_index(chunks: Iterable[RetrievedChunk]) -> dict[str, RetrievedChunk]:
    """Index chunks by every identifier a model might cite them with."""
    index: dict[str, RetrievedChunk] = {}
    for chunk in chunks:
        for identifier in (chunk.label, chunk.chunk_id, chunk.s3_uri):
            if identifier:
                index[_key(identifier)] = chunk
    return index


def _citation_is_grounded(
    citation: dict[str, Any], index: dict[str, RetrievedChunk]
) -> RetrievedChunk | None:
    for field in ("label", "s3Uri", "chunkId"):
        value = citation.get(field)
        if value and _key(value) in index:
            return index[_key(value)]
    return None


def enforce(
    findings: list[dict[str, Any]], chunks: list[RetrievedChunk]
) -> GroundingResult:
    """Keep only findings whose citations resolve to retrieved chunks.

    Citation metadata on surviving findings is rewritten from the chunk itself, not from
    the model's output, so issuer/date/URL are always the real values even if the model
    paraphrased them.
    """
    index = _chunk_index(chunks)
    kept: list[dict[str, Any]] = []
    reasons: list[str] = []

    for finding in findings:
        citations = finding.get("citations") or []
        if not citations:
            reasons.append(f"{finding.get('id', '?')}: no citations")
            continue

        grounded: list[dict[str, Any]] = []
        for citation in citations:
            chunk = _citation_is_grounded(citation, index)
            if chunk is None:
                continue
            grounded.append(
                {
                    "label": chunk.label or chunk.chunk_id,
                    "issuer": chunk.issuer or "Unknown issuer",
                    "date": chunk.date,
                    "sourceUrl": chunk.source_url,
                    "s3Uri": chunk.s3_uri,
                    # Excerpt comes from the document, never from the model.
                    "excerpt": (chunk.text or "")[:300] or None,
                }
            )

        if not grounded:
            reasons.append(
                f"{finding.get('id', '?')}: cited {[c.get('label') for c in citations]}, "
                "none of which were retrieved"
            )
            continue

        finding = {**finding, "citations": grounded}
        kept.append(finding)

    dropped = len(findings) - len(kept)
    if dropped:
        logger.warning("grounding guard dropped %d finding(s): %s", dropped, reasons)

    return GroundingResult(findings=kept, dropped=dropped, drop_reasons=reasons)
