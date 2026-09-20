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
        monkeypatch.setattr(gemini.time, "sleep", lambda *_: None)
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
        monkeypatch.setattr(gemini.time, "sleep", lambda *_: (_ for _ in ()).throw(AssertionError("should not sleep/retry on a raw exception")))
        pool = gemini._pool()
        calls = []

        def boom(method, url, **kw):
            calls.append(1)
            raise TimeoutError("connection timed out")

        monkeypatch.setattr(pool, "request", boom)
        with pytest.raises(RuntimeError, match="Gemini request failed"):
            gemini.converse("gemini-2.0-flash", "sys", [{"role": "user", "content": [{"text": "hi"}]}])
        # A raw exception (connection error, read timeout) is NOT retried - see _post()'s
        # docstring: unlike a fast-failing HTTP status, a timeout already spent the full
        # read-timeout budget once, and retrying risks blowing the Lambda's 25s limit
        # outright (this is exactly what happened live before this was scoped down).
        assert len(calls) == 1

    def test_api_key_never_appears_in_a_raised_error(self, monkeypatch):
        """A real key must never leak into logs/exceptions if a call fails."""
        monkeypatch.setenv("GEMINI_API_KEY", "SUPER-SECRET-KEY-VALUE")
        monkeypatch.setattr(gemini.time, "sleep", lambda *_: None)
        fake_pool(monkeypatch, status=500, body={"error": "server error"})
        with pytest.raises(RuntimeError) as exc_info:
            gemini.converse("gemini-2.0-flash", "sys", [{"role": "user", "content": [{"text": "hi"}]}])
        assert "SUPER-SECRET-KEY-VALUE" not in str(exc_info.value)


class TestRetry:
    """A single fast retry on a transient status - added 2026-09-20 after gemini-3.5-flash
    started returning 503 'high demand' errors live, which verdict.assess() would silently
    turn into a false NO_DATA (see its docstring: it deliberately never guesses a verdict on
    an LLM failure, so an unretried transient error looked identical to a genuinely clean
    product). See clients/gemini.py's module-level comment for the full reasoning."""

    def test_retries_once_on_503_then_succeeds(self, monkeypatch):
        with_api_key(monkeypatch)
        monkeypatch.setattr(gemini.time, "sleep", lambda *_: None)
        pool = gemini._pool()
        calls = []

        def flaky(method, url, **kw):
            calls.append(1)
            if len(calls) == 1:
                return FakeResponse(503, {"error": {"message": "high demand"}})
            return FakeResponse(200, candidate_response("Hello there"))

        monkeypatch.setattr(pool, "request", flaky)
        result = gemini.converse("gemini-3.5-flash", "sys", [{"role": "user", "content": [{"text": "hi"}]}])
        assert result == {"text": "Hello there"}
        assert len(calls) == 2

    def test_gives_up_after_two_failures(self, monkeypatch):
        with_api_key(monkeypatch)
        monkeypatch.setattr(gemini.time, "sleep", lambda *_: None)
        pool = gemini._pool()
        calls = []

        def always_503(method, url, **kw):
            calls.append(1)
            return FakeResponse(503, {"error": {"message": "high demand"}})

        monkeypatch.setattr(pool, "request", always_503)
        with pytest.raises(RuntimeError, match="503"):
            gemini.converse("gemini-3.5-flash", "sys", [{"role": "user", "content": [{"text": "hi"}]}])
        assert len(calls) == 2

    def test_non_retryable_status_does_not_retry(self, monkeypatch):
        """A 400 Bad Request (e.g. a malformed schema) is our own bug, not a transient
        provider hiccup - retrying it wastes the request budget for nothing."""
        with_api_key(monkeypatch)
        monkeypatch.setattr(gemini.time, "sleep", lambda *_: (_ for _ in ()).throw(AssertionError("should not sleep/retry on a 400")))
        pool = gemini._pool()
        calls = []

        def bad_request(method, url, **kw):
            calls.append(1)
            return FakeResponse(400, {"error": {"message": "bad request"}})

        monkeypatch.setattr(pool, "request", bad_request)
        with pytest.raises(RuntimeError, match="400"):
            gemini.converse("gemini-3.5-flash", "sys", [{"role": "user", "content": [{"text": "hi"}]}])
        assert len(calls) == 1
