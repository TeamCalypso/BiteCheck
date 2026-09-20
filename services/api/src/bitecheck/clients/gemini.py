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
from functools import lru_cache
from typing import Any

import urllib3

from bitecheck.config import Config

logger = logging.getLogger(__name__)

_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_READ_TIMEOUT_S = 20
_CONNECT_TIMEOUT_S = 5


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


def converse(
    model_id: str,
    system: str,
    messages: list[dict[str, Any]],
    tool_schema: dict | None = None,
) -> dict[str, Any]:
    """Single Gemini generateContent call, matching clients/bedrock.py::converse()'s
    contract: with tool_schema, returns the parsed structured object directly; without,
    returns {"text": <response text>}.
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

    if response.status != 200:
        raise RuntimeError(
            f"Gemini returned HTTP {response.status} for model {model_id}: "
            f"{response.data.decode('utf-8', errors='replace')[:500]}"
        )

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
