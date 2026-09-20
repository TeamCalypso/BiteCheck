"""clients/llm.py tests: proves the provider dispatch actually routes to the right client
with the right model ID, and (critically) with the right calling convention - the bug this
file's tests would have caught immediately: an earlier version called bedrock.converse()
positionally instead of by keyword, which silently broke every mock in the existing test
suite that uses `lambda **kw: ...`.
"""

from __future__ import annotations

from bitecheck.clients import bedrock, gemini, llm


class TestDispatch:
    def test_bedrock_provider_calls_bedrock_with_keyword_args(self, monkeypatch):
        monkeypatch.setenv("AI_PROVIDER", "bedrock")
        monkeypatch.setenv("BEDROCK_VERDICT_MODEL", "claude-test")
        captured = {}

        def fake_converse(**kw):
            captured.update(kw)
            return {"text": "ok"}

        monkeypatch.setattr(bedrock, "converse", fake_converse)
        result = llm.converse(kind="verdict", system="sys", messages=[{"role": "user", "content": [{"text": "hi"}]}])

        assert result == {"text": "ok"}
        assert captured["model_id"] == "claude-test"
        assert captured["system"] == "sys"

    def test_gemini_provider_calls_gemini_with_keyword_args(self, monkeypatch):
        monkeypatch.setenv("AI_PROVIDER", "gemini")
        monkeypatch.setenv("GEMINI_VERDICT_MODEL", "gemini-test")
        captured = {}

        def fake_converse(**kw):
            captured.update(kw)
            return {"text": "ok"}

        monkeypatch.setattr(gemini, "converse", fake_converse)
        result = llm.converse(kind="verdict", system="sys", messages=[{"role": "user", "content": [{"text": "hi"}]}])

        assert result == {"text": "ok"}
        assert captured["model_id"] == "gemini-test"

    def test_fast_kind_picks_the_fast_model(self, monkeypatch):
        monkeypatch.setenv("AI_PROVIDER", "gemini")
        monkeypatch.setenv("GEMINI_FAST_MODEL", "gemini-fast-test")
        monkeypatch.setenv("GEMINI_VERDICT_MODEL", "gemini-verdict-test")
        captured = {}
        monkeypatch.setattr(gemini, "converse", lambda **kw: captured.update(kw) or {"text": "ok"})

        llm.converse(kind="fast", system="sys", messages=[])
        assert captured["model_id"] == "gemini-fast-test"

    def test_tool_schema_passed_through(self, monkeypatch):
        monkeypatch.setenv("AI_PROVIDER", "gemini")
        captured = {}
        monkeypatch.setattr(gemini, "converse", lambda **kw: captured.update(kw) or {})

        schema = {"type": "object"}
        llm.converse(kind="verdict", system="sys", messages=[], tool_schema=schema)
        assert captured["tool_schema"] == schema
