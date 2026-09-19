"""GET /v1/health - liveness plus a cheap config sanity check.

Reports whether the knowledge base ID and model IDs are actually wired, which is the
failure we hit most often after a redeploy.
"""

from __future__ import annotations

import json
import os
from typing import Any


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    body = {
        "status": "ok",
        "version": os.environ.get("APP_VERSION", "0.1.0"),
        "region": os.environ.get("AWS_REGION", "unknown"),
        "config": {
            "knowledgeBase": bool(os.environ.get("KNOWLEDGE_BASE_ID")),
            "verdictModel": bool(os.environ.get("BEDROCK_VERDICT_MODEL")),
            "fastModel": bool(os.environ.get("BEDROCK_FAST_MODEL")),
            "cacheTable": bool(os.environ.get("CACHE_TABLE")),
        },
    }
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
