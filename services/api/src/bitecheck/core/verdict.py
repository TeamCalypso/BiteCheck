"""Generation half of the RAG pipeline.

Takes retrieved chunks and produces {verdict, findings} through a strict tool-use schema.
Split from rag.py so retrieval tuning and prompt tuning do not fight each other.

Whatever comes out of here is still untrusted: `findings[].citations` are built from
`citedLabels` (label strings the model chose from the excerpts it was given), and
handlers/analyze.py runs the result through `core/grounding.enforce()` before anything
reaches a user. The model never gets to originate a sourceUrl, issuer, or date itself -
those are always rewritten from the chunk's own metadata.

`score` is deliberately NOT set here: it depends on which findings survive grounding, which
this module has no visibility into. handlers/analyze.py computes the final score by calling
`score_from_findings()` again after grounding.enforce().
"""

from __future__ import annotations

import logging
from typing import Any

from bitecheck.clients import llm
from bitecheck.core.grounding import RetrievedChunk
from bitecheck.core.normalizer import NormalizedProduct

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a food safety analyst. You are given a product identity and a set of excerpts from
official regulator and laboratory documents, each tagged with a [label: ...] you must cite
by exact string when you use it.

Rules you must not break:
- Every finding must cite at least one excerpt by its exact label in `citedLabels`. Never
  invent a label that was not given to you.
- If the excerpts do not actually mention this brand or this product, return an empty
  findings list. Do not generalise from the category to the specific product - a pesticide
  finding about spices in general is not evidence against this particular brand.
- Distinguish scope carefully: a recall of specific batches is BATCH, not BRAND. A finding
  about the whole company's practices is BRAND. A finding about every product in the
  category (e.g. a regulation) is CATEGORY.
- Never infer a safety violation from marketing language alone (a bold "100% natural" claim
  is not itself evidence of anything - only cite it if an excerpt says the claim was
  found false).
- verdict.status should be CRITICAL or WARNING when a CRITICAL/HIGH finding exists, CAUTION
  for MEDIUM-only findings, CLEAR when excerpts were retrieved but none are adverse to this
  specific product, and NO_DATA when you have no basis to assess it either way.
- Write headline and summary in plain language for a shopper, not a regulator. No jargon
  without a one-clause explanation.
"""

_TOOL_SCHEMA = {
    "type": "object",
    "required": ["verdict", "findings"],
    "properties": {
        "verdict": {
            "type": "object",
            "required": ["status", "headline", "summary"],
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["CRITICAL", "WARNING", "CAUTION", "CLEAR", "NO_DATA"],
                },
                "headline": {"type": "string", "description": "One sentence, <120 chars."},
                "summary": {"type": "string", "description": "2-3 plain-language sentences."},
            },
        },
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["severity", "type", "scope", "title", "detail", "citedLabels"],
                "properties": {
                    "severity": {"type": "string", "enum": ["CRITICAL", "HIGH", "MEDIUM", "INFO"]},
                    "type": {
                        "type": "string",
                        "enum": [
                            "CONTAMINANT", "RECALL", "LABEL_CLAIM", "ADDITIVE",
                            "LICENSE", "COLD_CHAIN", "ADJUDICATION",
                        ],
                    },
                    "scope": {"type": "string", "enum": ["BRAND", "PRODUCT", "BATCH", "CATEGORY"]},
                    "title": {"type": "string", "description": "<140 chars."},
                    "detail": {"type": "string"},
                    "batches": {"type": "array", "items": {"type": "string"}},
                    "citedLabels": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string"},
                        "description": "Exact [label: ...] value(s) this finding is based on.",
                    },
                },
            },
        },
    },
}

_NO_DATA_VERDICT = {
    "status": "NO_DATA",
    "headline": "No adverse regulator records found for this brand or product",
    "summary": (
        "We searched our knowledge base and found no matching records for this product. "
        "Absence of a record is not a guarantee of purity - our corpus is not exhaustive."
    ),
}


def _format_nutrition_summary(nutrition: dict[str, Any]) -> str:
    """Renders the resolved macros/flags as a short line the model can cross-check listing
    claims against - this is what lets a LABEL_CLAIM finding say a declared number doesn't
    match the panel, instead of only catching claims an excerpt happens to mention."""
    macros = nutrition.get("macros") or []
    macro_line = ", ".join(f"{m['label']} {m['grams']}g" for m in macros)
    flags = nutrition.get("flags") or []
    flag_line = "; ".join(f.get("label", "") for f in flags)
    parts = [f"Declared nutrition (per 100g): {macro_line}" if macro_line else ""]
    if flag_line:
        parts.append(f"Automated label flags: {flag_line}")
    return "\n".join(p for p in parts if p)


def _format_chunks(chunks: list[RetrievedChunk]) -> str:
    blocks = []
    for chunk in chunks:
        label = chunk.label or chunk.chunk_id
        blocks.append(
            f"[label: {label}] ({chunk.issuer or 'unknown issuer'}, {chunk.date or 'undated'})\n"
            f"{chunk.text}"
        )
    return "\n\n---\n\n".join(blocks)


def assess(
    product: NormalizedProduct,
    chunks: list[RetrievedChunk],
    nutrition: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return {"verdict": {...}, "findings": [...]} - unvalidated, pre-grounding.

    If no chunks were retrieved, short-circuits to NO_DATA without calling Bedrock at all:
    there is nothing to ground a finding in, so asking the model would only spend money to
    produce something grounding.enforce() will discard anyway.
    """
    if not chunks:
        return {"verdict": dict(_NO_DATA_VERDICT), "findings": []}

    product_desc = f"Brand: {product.brand or 'unknown'}\nProduct: {product.name}\nCategory: {product.category}"
    nutrition_block = _format_nutrition_summary(nutrition) if nutrition else ""
    user_text = (
        f"{product_desc}\n\n"
        + (f"{nutrition_block}\n\n" if nutrition_block else "")
        + f"Excerpts retrieved from the knowledge base for this product "
        f"(cite ONLY these, by their exact label):\n\n{_format_chunks(chunks)}"
    )

    try:
        result = llm.converse(
            kind="verdict",
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": [{"text": user_text}]}],
            tool_schema=_TOOL_SCHEMA,
        )
    except Exception:
        logger.exception("verdict.assess() Bedrock call failed for product=%r", product.name)
        # Fail toward "we don't know", never toward a guessed verdict about a real brand.
        return {"verdict": dict(_NO_DATA_VERDICT), "findings": []}

    findings = []
    for i, raw in enumerate(result.get("findings", [])):
        cited_labels = raw.get("citedLabels") or []
        if not cited_labels:
            continue  # a finding with no citation cannot survive grounding anyway
        findings.append(
            {
                "id": f"f{i + 1}",
                "severity": raw.get("severity", "INFO"),
                "type": raw.get("type", "CONTAMINANT"),
                "scope": raw.get("scope", "PRODUCT"),
                "title": raw.get("title", ""),
                "detail": raw.get("detail", ""),
                "batches": raw.get("batches", []),
                # Placeholder citations keyed only by label - grounding.enforce() resolves
                # each label against the real retrieved chunk and rebuilds the full
                # citation (issuer/date/sourceUrl/excerpt) from that chunk's own metadata.
                "citations": [{"label": label} for label in cited_labels],
            }
        )

    verdict = result.get("verdict") or {}
    return {
        "verdict": {
            "status": verdict.get("status", "NO_DATA"),
            "headline": verdict.get("headline") or _NO_DATA_VERDICT["headline"],
            "summary": verdict.get("summary") or _NO_DATA_VERDICT["summary"],
        },
        "findings": findings,
    }


# Fixed, explainable penalty per severity rather than a model-guessed number - a judge (or
# a teammate) can read this table and understand exactly how score maps to findings.
_SEVERITY_PENALTY = {"CRITICAL": 45, "HIGH": 25, "MEDIUM": 12, "INFO": 3}


def score_from_findings(findings: list[dict[str, Any]]) -> int:
    """Map (post-grounding) findings onto the 0-100 gauge value.

    Called by handlers/analyze.py AFTER core/grounding.enforce(), not by assess() above -
    the score must reflect what actually survived grounding, not the model's first draft.
    """
    if not findings:
        return 95  # not 100: "nothing survived grounding" isn't the same certainty as an
                   # explicit CLEAR verdict over full corpus coverage
    score = 100
    for finding in findings:
        score -= _SEVERITY_PENALTY.get(finding.get("severity", "INFO"), 3)
    return max(0, min(100, score))
