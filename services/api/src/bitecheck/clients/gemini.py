"""Google Gemini client, plugged in via clients/llm.py while Bedrock access is blocked
(see docs/TRD.md's "AI provider" section). Plain HTTP via urllib3, not the google-genai
SDK - keeps the Lambda package small and matches the existing pattern in
clients/openfoodfacts.py, rather than adding a new heavy dependency for one endpoint.

`converse()` matches clients/bedrock.py::converse()'s exact signature and return shape, so
core/normalizer.py and core/verdict.py are completely unaware of which provider is active -
they always import from clients/llm.py, which dispatches to whichever provider
Config.ai_provider names.
"""

from __future__ import annotations

import json
import logging
import time
from functools import lru_cache
from typing import Any

import urllib3

from bitecheck.config import Config

logger = logging.getLogger(__name__)

_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Sized against a hard constraint, not a guess: AnalyzeFunction's Lambda timeout is 29s
# (infra/template.yaml - already at the HTTP API integration's own 30s ceiling, so it
# cannot go higher), and a single cache-miss request can make up to THREE sequential
# Gemini calls - normalizer.normalize() (entity extraction), nutrition.py's
# _from_gemini_estimate() (only when no label/OFF/catalog match), and verdict.assess().
# At the old 20s read timeout, three calls could cost up to 60s on their own before ever
# considering the rest of the pipeline - observed live, 2026-09-22: Gemini itself was
# degraded (reads not completing at all, not just slow), so real requests were hitting a
# hard platform-level Lambda timeout with no clean response, which is worse than an honest
# NO_DATA: the client never even gets JSON back to show a real error. 8s bounds the worst
# case at 3 x 8s = 24s, leaving headroom for the rest of the pipeline (resolve, cache,
# Open Food Facts' own 2.5s timeout, retrieval, grounding) - and it's still generous for a
# healthy call, which has been observed completing in 2-8s.
_READ_TIMEOUT_S = 8
_CONNECT_TIMEOUT_S = 5

# Google's free-tier models return these when overloaded (observed live, 2026-09-20:
# gemini-3.5-flash returning 503 "currently experiencing high demand"). They fail fast,
# not by exhausting the read timeout, so one quick retry is cheap - and worth having,
# because verdict.py deliberately degrades to NO_DATA on any LLM failure rather than
# guessing (see its docstring), so an unretried transient error looks identical to a
# genuinely clean product instead of surfacing as an error. Kept to a single retry with a
# short fixed delay - see _READ_TIMEOUT_S above for why this whole module has to stay
# cheap: up to three of these calls can happen in one request, inside a fixed 29s budget.
_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
_RETRY_DELAY_S = 0.5


@lru_cache(maxsize=1)
def _pool() -> urllib3.PoolManager:
    return urllib3.PoolManager()


def _to_gemini_type(json_schema_type: Any) -> str:
    """JSON Schema type -> Gemini Schema type. Gemini's Schema object uses uppercase type
    names and does not support a type union (["string","null"]) - callers that need an
    optional field express it with "nullable": true instead (handled in _to_gemini_schema)."""
    t = json_schema_type[0] if isinstance(json_schema_type, list) else json_schema_type
    return {
        "object": "OBJECT",
        "array": "ARRAY",
        "string": "STRING",
        "number": "NUMBER",
        "integer": "INTEGER",
        "boolean": "BOOLEAN",
    }.get(t, "STRING")


def _to_gemini_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Recursively convert a standard JSON Schema (as used throughout core/normalizer.py
    and core/verdict.py's _TOOL_SCHEMA) into Gemini's OpenAPI-subset Schema format."""
    result: dict[str, Any] = {"type": _to_gemini_type(schema.get("type", "string"))}

    raw_type = schema.get("type")
    if isinstance(raw_type, list) and "null" in raw_type:
        result["nullable"] = True

    if "description" in schema:
        result["description"] = schema["description"]
    if "enum" in schema:
        result["enum"] = schema["enum"]

    if result["type"] == "OBJECT" and "properties" in schema:
        result["properties"] = {
            key: _to_gemini_schema(value) for key, value in schema["properties"].items()
        }
        if "required" in schema:
            result["required"] = schema["required"]

    if result["type"] == "ARRAY" and "items" in schema:
        result["items"] = _to_gemini_schema(schema["items"])

    return result


def _messages_to_contents(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Bedrock Converse message format -> Gemini contents format. Both are
    [{"role": ..., <text-bearing list>}], just with a different key name and role vocab."""
    contents = []
    for message in messages:
        role = "model" if message.get("role") == "assistant" else "user"
        text = "".join(block.get("text", "") for block in message.get("content", []))
        contents.append({"role": role, "parts": [{"text": text}]})
    return contents


def _post(url: str, body: dict[str, Any], model_id: str) -> Any:
    """One HTTP attempt, with a single fast retry on a transient status - see the module
    constants above for why. Raises RuntimeError on any non-retryable or exhausted failure.

    Deliberately does NOT retry a raw request exception (connection error, read timeout,
    etc.) - only a retryable HTTP status. A status-code failure means the server already
    responded quickly, so a retry is cheap; a connection/read timeout means we already spent
    up to _READ_TIMEOUT_S finding that out, and retrying could spend it again, risking the
    Lambda's 25s budget outright (observed live, 2026-09-20: an earlier version that also
    retried on exceptions hit exactly this and timed out the whole request).
    """
    try:
        response = _pool().request(
            "POST",
            url,
            body=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            timeout=urllib3.Timeout(connect=_CONNECT_TIMEOUT_S, read=_READ_TIMEOUT_S),
            retries=False,
        )
    except Exception as e:
        raise RuntimeError(f"Gemini request failed for model {model_id}: {e}") from e

    if response.status == 200:
        return response

    if response.status not in _RETRYABLE_STATUSES:
        raise RuntimeError(
            f"Gemini returned HTTP {response.status} for model {model_id}: "
            f"{response.data.decode('utf-8', errors='replace')[:500]}"
        )

    logger.warning("Retrying Gemini call for model %s after HTTP %s", model_id, response.status)
    time.sleep(_RETRY_DELAY_S)

    try:
        response = _pool().request(
            "POST",
            url,
            body=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            timeout=urllib3.Timeout(connect=_CONNECT_TIMEOUT_S, read=_READ_TIMEOUT_S),
            retries=False,
        )
    except Exception as e:
        raise RuntimeError(f"Gemini request failed for model {model_id} on retry: {e}") from e

    if response.status == 200:
        return response

    raise RuntimeError(
        f"Gemini returned HTTP {response.status} for model {model_id} (after one retry): "
        f"{response.data.decode('utf-8', errors='replace')[:500]}"
    )


def converse(
    model_id: str,
    system: str,
    messages: list[dict[str, Any]],
    tool_schema: dict | None = None,
) -> dict[str, Any]:
    """Single Gemini generateContent call (with one fast retry on a transient failure -
    see _post), matching clients/bedrock.py::converse()'s contract: with tool_schema,
    returns the parsed structured object directly; without, returns {"text": ...}.
    """
    config = Config.from_env()
    if not config.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Get a free key at https://aistudio.google.com/apikey "
            "and set it as a Lambda environment variable (see infra/samconfig.toml)."
        )

    body: dict[str, Any] = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": _messages_to_contents(messages),
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 2048,
        },
    }

    if tool_schema is not None:
        body["generationConfig"]["responseMimeType"] = "application/json"
        body["generationConfig"]["responseSchema"] = _to_gemini_schema(tool_schema)

    url = f"{_API_BASE}/{model_id}:generateContent?key={config.gemini_api_key}"

    response = _post(url, body, model_id)
    payload = json.loads(response.data.decode("utf-8"))
    candidates = payload.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"Gemini returned no candidates for model {model_id}: {payload}")

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)

    if tool_schema is not None:
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Gemini's structured response wasn't valid JSON despite responseSchema: {e}. "
                f"Raw text: {text[:500]}"
            ) from e

    return {"text": text}
