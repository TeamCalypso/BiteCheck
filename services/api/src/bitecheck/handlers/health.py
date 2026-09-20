"""GET /v1/health - liveness plus a cheap config sanity check.

Reports whether the active provider's config is actually wired, which is the failure we
hit most often after a redeploy. Provider-aware since AI_PROVIDER can be "bedrock" or
"gemini" (see docs/TRD.md's "AI provider" section) - checking Bedrock env vars while
Gemini is active would misreport a working deploy as broken, and vice versa.
"""

from __future__ import annotations

import json
import os
from typing import Any

# Deploys before real Bedrock access existed used this sentinel for the four Bedrock
# parameters (see infra/samconfig.toml) - a non-empty string, but not a real value. Treat
# it as "not configured" rather than reporting a false "true".
_PLACEHOLDER = "PENDING-BEDROCK-ACCESS"


def _is_set(value: str | None) -> bool:
    return bool(value) and value != _PLACEHOLDER


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    provider = os.environ.get("AI_PROVIDER", "bedrock")

    if provider == "gemini":
        provider_config = {
            "geminiApiKey": _is_set(os.environ.get("GEMINI_API_KEY")),
            "geminiVerdictModel": _is_set(os.environ.get("GEMINI_VERDICT_MODEL")),
            "geminiFastModel": _is_set(os.environ.get("GEMINI_FAST_MODEL")),
        }
    else:
        provider_config = {
            "knowledgeBase": _is_set(os.environ.get("KNOWLEDGE_BASE_ID")),
            "verdictModel": _is_set(os.environ.get("BEDROCK_VERDICT_MODEL")),
            "fastModel": _is_set(os.environ.get("BEDROCK_FAST_MODEL")),
        }

    body = {
        "status": "ok",
        "version": os.environ.get("APP_VERSION", "0.1.0"),
        "region": os.environ.get("AWS_REGION", "unknown"),
        "aiProvider": provider,
        "config": {
            "cacheTable": _is_set(os.environ.get("CACHE_TABLE")),
            **provider_config,
        },
    }
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
