"""clients/gemini.py tests. The HTTP call is faked - no real network access, no real key
needed. Covers the schema conversion (the trickiest part - Gemini's Schema format differs
from the standard JSON Schema used throughout core/normalizer.py and core/verdict.py).
"""

from __future__ import annotations

import json

import pytest

from bitecheck.clients import gemini


class FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self.data = json.dumps(body).encode("utf-8")


def candidate_response(text: str):
    return {"candidates": [{"content": {"parts": [{"text": text}], "role": "model"}}]}


def fake_pool(monkeypatch, status=200, body=None):
    pool = gemini._pool()
    monkeypatch.setattr(
        pool, "request", lambda method, url, **kw: FakeResponse(status, body if body is not None else {})
    )
    return pool


def with_api_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")


class TestSchemaConversion:
    def test_basic_types(self):
        schema = {"type": "object", "properties": {"name": {"type": "string"}, "age": {"type": "integer"}}}
        result = gemini._to_gemini_schema(schema)
        assert result["type"] == "OBJECT"
        assert result["properties"]["name"]["type"] == "STRING"
        assert result["properties"]["age"]["type"] == "INTEGER"

    def test_nullable_union_type(self):
        schema = {"type": ["string", "null"]}
        result = gemini._to_gemini_schema(schema)
        assert result["type"] == "STRING"
        assert result["nullable"] is True

    def test_array_items(self):
        schema = {"type": "array", "items": {"type": "string"}}
        result = gemini._to_gemini_schema(schema)
        assert result["type"] == "ARRAY"
        assert result["items"]["type"] == "STRING"

    def test_required_preserved(self):
        schema = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]}
        result = gemini._to_gemini_schema(schema)
        assert result["required"] == ["a"]

    def test_enum_preserved(self):
        schema = {"type": "string", "enum": ["A", "B", "C"]}
        result = gemini._to_gemini_schema(schema)
        assert result["enum"] == ["A", "B", "C"]

    def test_nested_object(self):
        schema = {
            "type": "object",
            "properties": {
                "verdict": {
                    "type": "object",
                    "properties": {"status": {"type": "string"}},
                    "required": ["status"],
                }
            },
        }
        result = gemini._to_gemini_schema(schema)
        assert result["properties"]["verdict"]["type"] == "OBJECT"
        assert result["properties"]["verdict"]["properties"]["status"]["type"] == "STRING"


class TestMessageConversion:
    def test_bedrock_style_messages_convert_to_contents(self):
        messages = [{"role": "user", "content": [{"text": "hello"}]}]
        contents = gemini._messages_to_contents(messages)
        assert contents == [{"role": "user", "parts": [{"text": "hello"}]}]

    def test_assistant_role_maps_to_model(self):
        messages = [{"role": "assistant", "content": [{"text": "hi"}]}]
        contents = gemini._messages_to_contents(messages)
        assert contents[0]["role"] == "model"


class TestConverse:
    def test_missing_api_key_raises_clear_error(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
            gemini.converse("gemini-2.0-flash", "sys", [{"role": "user", "content": [{"text": "hi"}]}])

    def test_plain_text_response(self, monkeypatch):
        with_api_key(monkeypatch)
        fake_pool(monkeypatch, body=candidate_response("Hello there"))
        result = gemini.converse("gemini-2.0-flash", "sys", [{"role": "user", "content": [{"text": "hi"}]}])
        assert result == {"text": "Hello there"}

    def test_structured_response_is_parsed_as_json(self, monkeypatch):
        with_api_key(monkeypatch)
        fake_pool(monkeypatch, body=candidate_response('{"brand": "Everest", "isFoodProduct": true}'))
        result = gemini.converse(
            "gemini-2.0-flash", "sys", [{"role": "user", "content": [{"text": "hi"}]}],
            tool_schema={"type": "object", "properties": {"brand": {"type": "string"}}},
        )
        assert result == {"brand": "Everest", "isFoodProduct": True}

    def test_malformed_structured_response_raises(self, monkeypatch):
        with_api_key(monkeypatch)
        fake_pool(monkeypatch, body=candidate_response("not valid json{{"))
        with pytest.raises(RuntimeError, match="valid JSON"):
            gemini.converse(
                "gemini-2.0-flash", "sys", [{"role": "user", "content": [{"text": "hi"}]}],
                tool_schema={"type": "object"},
            )

    def test_non_200_raises(self, monkeypatch):
        with_api_key(monkeypatch)
        fake_pool(monkeypatch, status=429, body={"error": "rate limited"})
        with pytest.raises(RuntimeError, match="429"):
            gemini.converse("gemini-2.0-flash", "sys", [{"role": "user", "content": [{"text": "hi"}]}])

    def test_no_candidates_raises(self, monkeypatch):
        with_api_key(monkeypatch)
        fake_pool(monkeypatch, body={"candidates": []})
        with pytest.raises(RuntimeError, match="no candidates"):
            gemini.converse("gemini-2.0-flash", "sys", [{"role": "user", "content": [{"text": "hi"}]}])

    def test_network_exception_raises_runtime_error(self, monkeypatch):
        with_api_key(monkeypatch)
        pool = gemini._pool()

        def boom(method, url, **kw):
            raise TimeoutError("connection timed out")

        monkeypatch.setattr(pool, "request", boom)
        with pytest.raises(RuntimeError, match="Gemini request failed"):
            gemini.converse("gemini-2.0-flash", "sys", [{"role": "user", "content": [{"text": "hi"}]}])

    def test_api_key_never_appears_in_a_raised_error(self, monkeypatch):
        """A real key must never leak into logs/exceptions if a call fails."""
        monkeypatch.setenv("GEMINI_API_KEY", "SUPER-SECRET-KEY-VALUE")
        fake_pool(monkeypatch, status=500, body={"error": "server error"})
        with pytest.raises(RuntimeError) as exc_info:
            gemini.converse("gemini-2.0-flash", "sys", [{"role": "user", "content": [{"text": "hi"}]}])
        assert "SUPER-SECRET-KEY-VALUE" not in str(exc_info.value)
