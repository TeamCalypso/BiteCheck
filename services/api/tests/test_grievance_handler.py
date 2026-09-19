"""handlers/grievance.py tests. bedrock.converse is monkeypatched, DynamoDB is moto."""

import json

from bitecheck.clients import bedrock
from bitecheck.core import cache
from bitecheck.handlers import grievance


def event(body):
    return {"body": json.dumps(body)}


def eligible_payload(asin="B0GRIEV0001"):
    return {
        "requestId": "r1", "asin": asin, "cached": False,
        "verdict": {"status": "CRITICAL", "score": 55, "headline": "h", "summary": "s"},
        "product": {"brand": "Demo Co", "name": "Garam Masala", "category": "spices_blends", "isFoodProduct": True},
        "findings": [
            {
                "id": "f1", "severity": "CRITICAL", "type": "CONTAMINANT", "scope": "BATCH",
                "title": "ETO above limit", "detail": "0.24 mg/kg found",
                "citations": [{"label": "RASFF 2024.2893", "issuer": "EU RASFF", "date": "2024-04-22"}],
            }
        ],
        "grievance": {"eligible": True, "reason": None},
        "disclaimer": "d",
    }


def not_eligible_payload(asin="B0CLEAN0001"):
    p = eligible_payload(asin)
    p["findings"] = []
    p["grievance"] = {"eligible": False, "reason": "No CRITICAL or HIGH finding."}
    return p


class TestGrievanceHandler:
    def test_missing_asin_returns_400(self, ddb_tables):
        result = grievance.handler(event({}), None)
        assert result["statusCode"] == 400

    def test_malformed_json_returns_400(self, ddb_tables):
        result = grievance.handler({"body": "{not json"}, None)
        assert result["statusCode"] == 400

    def test_no_cached_analysis_returns_404(self, ddb_tables):
        result = grievance.handler(event({"asin": "B0NEVERSEEN"}), None)
        assert result["statusCode"] == 404

    def test_ineligible_product_returns_400(self, ddb_tables):
        cache.put("B0CLEAN0001", not_eligible_payload(), ttl_seconds=86400)
        result = grievance.handler(event({"asin": "B0CLEAN0001"}), None)
        assert result["statusCode"] == 400

    def test_happy_path_returns_a_draft(self, ddb_tables, monkeypatch):
        cache.put("B0GRIEV0001", eligible_payload(), ttl_seconds=86400)
        monkeypatch.setattr(bedrock, "converse", lambda **kw: {"text": "Dear FoSCoS, ..."})

        result = grievance.handler(event({"asin": "B0GRIEV0001"}), None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["asin"] == "B0GRIEV0001"
        assert "FoSCoS" in body["draft"]

    def test_bedrock_failure_returns_500(self, ddb_tables, monkeypatch):
        cache.put("B0GRIEV0001", eligible_payload(), ttl_seconds=86400)

        def boom(**kw):
            raise RuntimeError("Bedrock unavailable")

        monkeypatch.setattr(bedrock, "converse", boom)
        result = grievance.handler(event({"asin": "B0GRIEV0001"}), None)
        assert result["statusCode"] == 500

    def test_findings_citations_reach_the_prompt(self, ddb_tables, monkeypatch):
        cache.put("B0GRIEV0001", eligible_payload(), ttl_seconds=86400)
        captured = {}

        def fake_converse(**kw):
            captured.update(kw)
            return {"text": "draft text"}

        monkeypatch.setattr(bedrock, "converse", fake_converse)
        grievance.handler(event({"asin": "B0GRIEV0001"}), None)

        user_text = captured["messages"][0]["content"][0]["text"]
        assert "RASFF 2024.2893" in user_text
        assert "B0GRIEV0001" in user_text
