"""POST /v1/grievance - draft a FoSCoS consumer complaint from a prior analysis.

Takes the ASIN of a product BiteCheck has already analysed (looked up from the same cache
core/cache.py writes to - there is no separate requestId index, the ASIN is the cache key),
and drafts a formal complaint citing the specific violation references on file. Only
drafts: BiteCheck never submits anything to FoSCoS on the user's behalf. The user reviews,
edits, and files it themselves.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from bitecheck.clients import bedrock
from bitecheck.config import Config
from bitecheck.core import cache
from bitecheck.responses import error_response, json_response

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You draft formal consumer grievances for India's FoSCoS (Food Safety Compliance System)
portal on behalf of a shopper. You are given a product's brand, name, ASIN, and a list of
confirmed findings with their regulator citations.

Rules:
- Use only the findings and citations you are given. Never add a claim, a regulation
  number, or a date that was not provided to you.
- Write in the first person, as the shopper filing the complaint, in a formal but plain
  register - no legal jargon that hides the actual claim.
- Structure: (1) product identification including the Amazon ASIN, (2) the specific
  concern with its citation, (3) a request for FSSAI/FoSCoS to review the product listing
  and, where applicable, the manufacturer's batch. Keep it under 250 words.
- End with a note that this draft is informational and the filer should verify all details
  before submission - you are not a legal document.
"""


def _format_findings(findings: list[dict[str, Any]]) -> str:
    blocks = []
    for f in findings:
        citations = "; ".join(f"{c.get('label')} ({c.get('issuer')}, {c.get('date') or 'undated'})" for c in f.get("citations", []))
        blocks.append(f"- [{f.get('severity')}] {f.get('title')}: {f.get('detail')} | Sources: {citations}")
    return "\n".join(blocks)


def _draft(cached: dict[str, Any]) -> str:
    product = cached.get("product", {})
    findings = cached.get("findings", [])
    user_text = (
        f"Product: {product.get('brand') or 'Unknown brand'} {product.get('name')}\n"
        f"Amazon ASIN: {cached.get('asin')}\n\n"
        f"Confirmed findings on file:\n{_format_findings(findings)}"
    )
    config = Config.from_env()
    result = bedrock.converse(
        model_id=config.verdict_model_id,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": [{"text": user_text}]}],
    )
    return result.get("text", "").strip()


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return error_response(400, "Request body must be valid JSON.")

    asin = body.get("asin")
    if not asin:
        return error_response(400, "'asin' is required.")

    cached = cache.get(asin)
    if cached is None:
        return error_response(
            404,
            "No analysis on file for this product yet. Run an analysis first, then request a grievance draft.",
        )

    if not cached.get("grievance", {}).get("eligible"):
        return error_response(
            400,
            "No CRITICAL or HIGH severity finding is on file for this product, so there is nothing to draft a formal complaint about.",
        )

    try:
        draft_text = _draft(cached)
    except Exception:
        logger.exception("grievance draft failed for asin=%s", asin)
        return error_response(500, "Could not draft the complaint right now. Please try again.")

    if not draft_text:
        return error_response(500, "Could not draft the complaint right now. Please try again.")

    return json_response(
        200,
        {
            "asin": asin,
            "draft": draft_text,
            "disclaimer": "This is an informational draft. Review and verify every detail before submitting it to FoSCoS.",
        },
    )
