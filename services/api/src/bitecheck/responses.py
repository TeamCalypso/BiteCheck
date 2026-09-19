"""Small helpers for shaping API Gateway HTTP API (Lambda proxy) responses.

CORS itself is handled by API Gateway's own CorsConfiguration (see infra/template.yaml) -
these helpers just keep every handler's JSON envelope and error shape consistent.
"""

from __future__ import annotations

import json
from typing import Any


def json_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=str),
    }


def error_response(status_code: int, message: str, **extra: Any) -> dict[str, Any]:
    return json_response(status_code, {"error": message, **extra})
