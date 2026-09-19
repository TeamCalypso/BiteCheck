"""End-to-end test of handlers/analyze.py: the full pipeline wired together.

Bedrock and Open Food Facts are faked (no real AWS/network); DynamoDB is backed by moto
(see conftest.py). This is the test that proves the orchestration in handlers/analyze.py
is actually correct - not just its individual pieces - and that a real response validates
against contract/analyze.schema.json, the same contract the frontend builds against.
"""

from __future__ import annotations

import json

from bitecheck.clients import bedrock, openfoodfacts
from bitecheck.core.grounding import RetrievedChunk
from bitecheck.handlers import analyze


def api_event(body: dict) -> dict:
    return {"body": json.dumps(body), "isBase64Encoded": False}


def fake_converse_factory(normalizer_result: dict, verdict_result: dict):
    """Routes a converse() call to the right canned response by inspecting which tool
    schema was requested - the normalizer schema requires 'isFoodProduct', the verdict
    schema requires 'verdict'."""

    def fake_converse(*, model_id, system, messages, tool_schema=None):
        required = (tool_schema or {}).get("required", [])
        if "isFoodProduct" in required:
            return normalizer_result
        if "verdict" in required:
            return verdict_result
        raise AssertionError(f"unexpected converse() call, required={required}")

    return fake_converse


def fake_retrieve_returning(chunks: list[RetrievedChunk]):
    def fake_retrieve(knowledge_base_id, query, top_k, metadata_filter=None):
        return {
            "retrievalResults": [
                {
                    "content": {"text": c.text},
                    "location": {"s3Location": {"uri": c.s3_uri}},
                    "metadata": {
                        "orderRef": c.label, "issuer": c.issuer,
                        "date": c.date, "sourceUrl": c.source_url,
                    },
                    "score": c.score,
                }
                for c in chunks
            ]
        }

    return fake_retrieve


NORMALIZER_FOOD = {
    "brand": "Demo Masala Co.", "name": "Garam Masala Blend", "category": "spices_blends",
    "isFoodProduct": True, "netQuantity": "100 g", "confidence": "HIGH",
}
NORMALIZER_NON_FOOD = {
    "brand": None, "name": "Wireless Mouse", "category": "non_food", "isFoodProduct": False,
}
VERDICT_CRITICAL = {
    "verdict": {"status": "CRITICAL", "headline": "ETO detected", "summary": "This batch failed a residue test."},
    "findings": [
        {
            "severity": "CRITICAL", "type": "CONTAMINANT", "scope": "BATCH",
            "title": "Ethylene oxide above limit", "detail": "0.24 mg/kg found",
            "batches": ["E24/09"], "citedLabels": ["RASFF 2024.2893"],
        }
    ],
}
VERDICT_UNGROUNDED = {
    "verdict": {"status": "CRITICAL", "headline": "x", "summary": "y"},
    "findings": [
        {
            "severity": "CRITICAL", "type": "CONTAMINANT", "scope": "BATCH",
            "title": "t", "detail": "d", "citedLabels": ["A Label That Was Never Retrieved"],
        }
    ],
}

SAMPLE_CHUNK = RetrievedChunk(
    chunk_id="s3://corpus/rasff.md",
    text="ethylene oxide 0.24 mg/kg detected in spice blend",
    s3_uri="s3://corpus/rasff.md",
    label="RASFF 2024.2893",
    issuer="EU RASFF",
    date="2024-04-22",
    source_url="https://example.org/notice",
)


class TestHappyPath:
    def test_full_pipeline_produces_a_schema_valid_critical_response(
        self, ddb_tables, monkeypatch, analyze_schema_validator
    ):
        monkeypatch.setattr(bedrock, "converse", fake_converse_factory(NORMALIZER_FOOD, VERDICT_CRITICAL))
        monkeypatch.setattr(bedrock, "retrieve", fake_retrieve_returning([SAMPLE_CHUNK]))
        monkeypatch.setattr(openfoodfacts, "search", lambda *a, **kw: None)

        event = api_event({"source": "web", "url": "https://www.amazon.in/Demo-Masala/dp/B0TESTASIN"})
        result = analyze.handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        errors = list(analyze_schema_validator.iter_errors(body))
        assert not errors, [e.message for e in errors]

        assert body["asin"] == "B0TESTASIN"
        assert body["cached"] is False
        assert body["verdict"]["status"] == "CRITICAL"
        assert len(body["findings"]) == 1
        assert body["findings"][0]["citations"][0]["issuer"] == "EU RASFF"
        assert body["findings"][0]["citations"][0]["sourceUrl"] == "https://example.org/notice"
        assert body["grievance"]["eligible"] is True
        assert body["meta"]["chunksRetrieved"] == 1
        assert body["meta"]["findingsDropped"] == 0

    def test_second_request_for_same_asin_is_served_from_cache(
        self, ddb_tables, monkeypatch, analyze_schema_validator
    ):
        converse_calls = []

        def counting_converse(*, model_id, system, messages, tool_schema=None):
            converse_calls.append(tool_schema)
            required = (tool_schema or {}).get("required", [])
            return NORMALIZER_FOOD if "isFoodProduct" in required else VERDICT_CRITICAL

        monkeypatch.setattr(bedrock, "converse", counting_converse)
        monkeypatch.setattr(bedrock, "retrieve", fake_retrieve_returning([SAMPLE_CHUNK]))
        monkeypatch.setattr(openfoodfacts, "search", lambda *a, **kw: None)

        event = api_event({"source": "web", "url": "https://www.amazon.in/Demo-Masala/dp/B0TESTASIN"})
        first = json.loads(analyze.handler(event, None)["body"])
        assert first["cached"] is False
        calls_after_first = len(converse_calls)
        assert calls_after_first > 0

        second_result = analyze.handler(event, None)
        second = json.loads(second_result["body"])

        errors = list(analyze_schema_validator.iter_errors(second))
        assert not errors, [e.message for e in errors]
        assert second["cached"] is True
        assert second["asin"] == first["asin"]
        assert second["verdict"] == first["verdict"]
        # The whole point of the cache: zero new Bedrock calls on a hit.
        assert len(converse_calls) == calls_after_first


class TestNonFood:
    def test_non_food_short_circuits_before_retrieval(self, ddb_tables, monkeypatch, analyze_schema_validator):
        retrieve_calls = []
        monkeypatch.setattr(bedrock, "converse", fake_converse_factory(NORMALIZER_NON_FOOD, VERDICT_CRITICAL))
        monkeypatch.setattr(bedrock, "retrieve", lambda **kw: retrieve_calls.append(kw) or {"retrievalResults": []})

        event = api_event({"source": "web", "url": "https://www.amazon.in/Wireless-Mouse/dp/B0NONFOOD1"})
        body = json.loads(analyze.handler(event, None)["body"])

        errors = list(analyze_schema_validator.iter_errors(body))
        assert not errors, [e.message for e in errors]
        assert body["product"]["isFoodProduct"] is False
        assert body["verdict"]["status"] == "NO_DATA"
        assert body["nutrition"] is None
        assert body["findings"] == []
        assert retrieve_calls == []  # never even queried the knowledge base


class TestGroundingIntegration:
    def test_ungrounded_finding_is_dropped_and_status_forced_to_no_data(
        self, ddb_tables, monkeypatch, analyze_schema_validator
    ):
        """The model claims a CRITICAL finding citing a document that was never actually
        retrieved. The final response must not contain it, and must not claim CRITICAL."""
        monkeypatch.setattr(bedrock, "converse", fake_converse_factory(NORMALIZER_FOOD, VERDICT_UNGROUNDED))
        monkeypatch.setattr(bedrock, "retrieve", fake_retrieve_returning([SAMPLE_CHUNK]))
        monkeypatch.setattr(openfoodfacts, "search", lambda *a, **kw: None)

        event = api_event({"source": "web", "url": "https://www.amazon.in/Demo-Masala/dp/B0UNGROUND"})
        body = json.loads(analyze.handler(event, None)["body"])

        errors = list(analyze_schema_validator.iter_errors(body))
        assert not errors, [e.message for e in errors]
        assert body["findings"] == []
        assert body["verdict"]["status"] == "NO_DATA"
        assert body["meta"]["findingsDropped"] == 1
        assert body["grievance"]["eligible"] is False


class TestValidation:
    def test_missing_url_returns_400(self, ddb_tables):
        result = analyze.handler(api_event({"source": "web"}), None)
        assert result["statusCode"] == 400

    def test_malformed_json_body_returns_400(self, ddb_tables):
        result = analyze.handler({"body": "{not json"}, None)
        assert result["statusCode"] == 400

    def test_unresolvable_url_returns_400(self, ddb_tables):
        result = analyze.handler(api_event({"source": "web", "url": "https://www.flipkart.com/x"}), None)
        assert result["statusCode"] == 400
