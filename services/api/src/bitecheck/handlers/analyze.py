"""POST /v1/analyze - the main orchestrator.

Pipeline:
  1. resolve      URL -> ASIN + slug title (never scrapes Amazon - see core/resolver.py)
  2. cache        DynamoDB lookup, return early on a warm hit
  3. catalog      merge curated attributes
  4. normalize    brand/product/category + the food gate (short-circuits non-food)
  5. nutrition    label -> Open Food Facts -> catalog, normalized to per-100g
  6. retrieve     Bedrock Retrieve against the knowledge base
  7. assess       Converse with a strict schema over those chunks
  8. ground       drop anything the chunks do not support; recompute the score from what
                  actually survives, not from the model's first draft
  9. cache write  and return

Thin by design: no business logic lives here, only sequencing and HTTP shaping. Every
branch below calls into core/ or clients/ for the actual work.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from bitecheck.clients import ddb, openfoodfacts
from bitecheck.config import DISCLAIMER, Config
from bitecheck.core import cache, grounding, normalizer, nutrition, rag, resolver, verdict
from bitecheck.responses import error_response, json_response

logger = logging.getLogger(__name__)

# Amazon's technical-details table uses inconsistent labels across listings; check all of
# them, case-insensitively.
_FSSAI_KEYS = (
    "fssai license", "fssai licence", "fssai lic. no.", "fssai license no",
    "fssai license no.", "fssai licence no.", "fssai reg. no.",
)
_NET_QTY_KEYS = ("net quantity", "net weight", "item weight", "net qty")


def _find_detail(technical_details: dict[str, str], candidates: tuple[str, ...]) -> str | None:
    for key, value in (technical_details or {}).items():
        if key.strip().lower() in candidates:
            return value
    return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _not_food_response(request_id: str, asin: str, resolved_name: str, latency_ms: int) -> dict[str, Any]:
    return {
        "requestId": request_id,
        "asin": asin,
        "cached": False,
        "generatedAt": _now_iso(),
        "product": {
            "brand": None,
            "name": resolved_name,
            "category": "non_food",
            "netQuantity": None,
            "fssaiLicense": None,
            "isFoodProduct": False,
            "imageUrl": None,
        },
        "verdict": {
            "status": "NO_DATA",
            "score": 100,
            "headline": "Not a food product",
            "summary": (
                "BiteCheck only analyses food, beverage and nutrition products regulated "
                "by FSSAI. This listing was classified as non-food, so no safety analysis "
                "was run."
            ),
        },
        "findings": [],
        "nutrition": None,
        "alternatives": [],
        "grievance": {"eligible": False, "reason": "Not a food product."},
        "meta": {
            "latencyMs": latency_ms,
            "chunksRetrieved": 0,
            "findingsDropped": 0,
            "modelId": None,
            "nutritionSource": None,
        },
        "disclaimer": DISCLAIMER,
    }


def _nutrition_to_dict(result: nutrition.Nutrition | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "basis": result.basis,
        "confidence": result.confidence,
        "source": result.source,
        "macros": result.macros,
        "flags": result.flags,
        "additives": result.additives,
        "novaGroup": result.nova_group,
    }


def _run_pipeline(body: dict[str, Any]) -> dict[str, Any]:
    """The actual orchestration. Raises resolver.UnresolvableUrlError for a bad URL;
    everything else is caught by handler() and turned into a 500 with a safe message."""
    start = time.monotonic()
    url = body.get("url", "")
    extracted = body.get("extracted") or {}
    force_refresh = bool(body.get("forceRefresh"))

    resolved = resolver.resolve(url)
    asin = resolved.asin
    request_id = str(uuid.uuid4())
    config = Config.from_env()

    # --- 2. cache -----------------------------------------------------------------
    if not force_refresh:
        cached = cache.get(asin)
        if cached is not None:
            cache.record_hit(asin)
            return {**cached, "cached": True, "requestId": request_id}

    # --- 3. catalog -----------------------------------------------------------------
    catalog_entry = ddb.get_catalog_entry(asin) or {}

    # --- 4. normalize + food gate -----------------------------------------------------
    title = resolver.best_effort_title(
        resolved.slug_title, extracted.get("title"), catalog_entry.get("name")
    )
    brand_hint = extracted.get("brand") or catalog_entry.get("brand")
    normalized = normalizer.normalize(title or "", brand_hint=brand_hint, bullets=extracted.get("bullets"))

    if not normalized.is_food_product:
        latency_ms = int((time.monotonic() - start) * 1000)
        response = _not_food_response(request_id, asin, normalized.name, latency_ms)
        cache.put(asin, response, ttl_seconds=config.cache_ttl_seconds)
        return response

    # --- 5. nutrition -----------------------------------------------------------------
    off_payload = None
    try:
        off_payload = openfoodfacts.search(normalized.brand or brand_hint, normalized.name)
    except Exception:
        # A nutrition-lookup failure must not fail the whole request - the safety verdict
        # is the important part; nutrition is an enhancement.
        logger.exception("Open Food Facts lookup failed for asin=%s", asin)

    nutrition_result = nutrition.build(
        extracted.get("nutritionTable"), off_payload, catalog_entry.get("nutrition")
    )

    # --- 6. retrieve --------------------------------------------------------------------
    chunks = rag.retrieve(normalized)

    # --- 7. assess ------------------------------------------------------------------------
    draft = verdict.assess(normalized, chunks, nutrition=_nutrition_to_dict(nutrition_result))

    # --- 8. ground --------------------------------------------------------------------------
    grounded = grounding.enforce(draft["findings"], chunks)
    findings = grounded.findings
    status = draft["verdict"]["status"]
    headline = draft["verdict"]["headline"]
    summary = draft["verdict"]["summary"]

    if not findings and status not in ("CLEAR", "NO_DATA"):
        # Everything the model proposed got dropped by the grounding guard. The honest
        # outcome is "we cannot verify this", not the model's original (now-unsupported)
        # verdict - see core/grounding.py for why this matters.
        status = "NO_DATA"
        headline = "No verifiable adverse records found for this brand or product"
        summary = (
            "Our initial check flagged a possible concern, but none of it could be "
            "confirmed against an actual source document, so we are not reporting it. "
            "This is not the same as a clean result - our records are not exhaustive."
        )

    score = verdict.score_from_findings(findings) if (findings or status == "CLEAR") else 65

    technical_details = extracted.get("technicalDetails") or {}
    fssai_license = _find_detail(technical_details, _FSSAI_KEYS)
    net_quantity = (
        normalized.net_quantity or catalog_entry.get("netQuantity") or _find_detail(technical_details, _NET_QTY_KEYS)
    )

    response: dict[str, Any] = {
        "requestId": request_id,
        "asin": asin,
        "cached": False,
        "generatedAt": _now_iso(),
        "product": {
            "brand": normalized.brand,
            "name": normalized.name,
            "category": normalized.category,
            "netQuantity": net_quantity,
            "fssaiLicense": fssai_license,
            "isFoodProduct": True,
            "imageUrl": extracted.get("imageUrl"),
        },
        "verdict": {"status": status, "score": score, "headline": headline, "summary": summary},
        "findings": findings,
        "nutrition": _nutrition_to_dict(nutrition_result),
        "alternatives": [],  # populated from the catalog in Phase 5
        "grievance": {
            "eligible": any(f["severity"] in ("CRITICAL", "HIGH") for f in findings),
            "reason": None if findings else "No CRITICAL or HIGH finding.",
        },
        "meta": {
            "latencyMs": int((time.monotonic() - start) * 1000),
            "chunksRetrieved": len(chunks),
            "findingsDropped": grounded.dropped,
            "modelId": (
                config.gemini_verdict_model if config.ai_provider == "gemini" else config.verdict_model_id
            ) or None,
            "nutritionSource": nutrition_result.source if nutrition_result else None,
        },
        "disclaimer": DISCLAIMER,
    }

    # --- 9. cache write -------------------------------------------------------------------
    cache.put(asin, response, ttl_seconds=config.cache_ttl_seconds)
    return response


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return error_response(400, "Request body must be valid JSON.")

    if not isinstance(body, dict) or not body.get("url"):
        return error_response(400, "'url' is required.")

    try:
        response_body = _run_pipeline(body)
    except resolver.UnresolvableUrlError as e:
        return error_response(400, str(e))
    except Exception:
        logger.exception("analyze handler failed for body=%r", body)
        return error_response(500, "Something went wrong analysing this product. Please try again.")

    return json_response(200, response_body)
