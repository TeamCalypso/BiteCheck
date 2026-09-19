"""core/verdict.py tests. bedrock.converse is monkeypatched - no AWS access needed."""

import pytest

from bitecheck.clients import bedrock
from bitecheck.core import verdict
from bitecheck.core.grounding import RetrievedChunk
from bitecheck.core.normalizer import NormalizedProduct


def product(**overrides):
    defaults = dict(brand="Everest", name="Garam Masala", category="spices_blends", is_food_product=True)
    return NormalizedProduct(**{**defaults, **overrides})


def chunk(label="RASFF 2024.2893"):
    return RetrievedChunk(
        chunk_id="c1", text="ethylene oxide detected", s3_uri="s3://x/c1.md",
        label=label, issuer="EU RASFF", date="2024-04-22", source_url="https://example.org",
    )


class TestAssess:
    def test_no_chunks_short_circuits_without_calling_bedrock(self, monkeypatch):
        called = []
        monkeypatch.setattr(bedrock, "converse", lambda **kw: called.append(kw))
        result = verdict.assess(product(), chunks=[])
        assert result["verdict"]["status"] == "NO_DATA"
        assert result["findings"] == []
        assert called == []

    def test_happy_path_maps_bedrock_response(self, monkeypatch):
        monkeypatch.setattr(
            bedrock,
            "converse",
            lambda **kw: {
                "verdict": {
                    "status": "CRITICAL",
                    "headline": "Ethylene oxide detected",
                    "summary": "This batch failed a residue test.",
                },
                "findings": [
                    {
                        "severity": "CRITICAL",
                        "type": "CONTAMINANT",
                        "scope": "BATCH",
                        "title": "ETO above limit",
                        "detail": "0.24 mg/kg found",
                        "batches": ["E24/09"],
                        "citedLabels": ["RASFF 2024.2893"],
                    }
                ],
            },
        )
        result = verdict.assess(product(), chunks=[chunk()])
        assert result["verdict"]["status"] == "CRITICAL"
        assert len(result["findings"]) == 1
        f = result["findings"][0]
        assert f["id"] == "f1"
        assert f["citations"] == [{"label": "RASFF 2024.2893"}]

    def test_finding_with_no_cited_labels_is_dropped_before_grounding(self, monkeypatch):
        monkeypatch.setattr(
            bedrock,
            "converse",
            lambda **kw: {
                "verdict": {"status": "CAUTION", "headline": "h", "summary": "s"},
                "findings": [
                    {
                        "severity": "MEDIUM", "type": "LABEL_CLAIM", "scope": "PRODUCT",
                        "title": "t", "detail": "d", "citedLabels": [],
                    }
                ],
            },
        )
        result = verdict.assess(product(), chunks=[chunk()])
        assert result["findings"] == []

    def test_bedrock_failure_falls_back_to_no_data(self, monkeypatch):
        def boom(**kw):
            raise RuntimeError("Bedrock unavailable")

        monkeypatch.setattr(bedrock, "converse", boom)
        result = verdict.assess(product(), chunks=[chunk()])
        assert result["verdict"]["status"] == "NO_DATA"
        assert result["findings"] == []

    def test_missing_verdict_fields_get_safe_defaults(self, monkeypatch):
        monkeypatch.setattr(bedrock, "converse", lambda **kw: {"verdict": {}, "findings": []})
        result = verdict.assess(product(), chunks=[chunk()])
        assert result["verdict"]["status"] == "NO_DATA"
        assert result["verdict"]["headline"]
        assert result["verdict"]["summary"]


class TestScoreFromFindings:
    def test_no_findings_scores_95_not_100(self):
        # 95, not 100: distinct from an explicit CLEAR verdict over full corpus coverage.
        assert verdict.score_from_findings([]) == 95

    def test_critical_finding_drops_score_significantly(self):
        score = verdict.score_from_findings([{"severity": "CRITICAL"}])
        assert score == 55

    def test_multiple_findings_stack(self):
        score = verdict.score_from_findings([{"severity": "HIGH"}, {"severity": "MEDIUM"}])
        assert score == 100 - 25 - 12

    def test_score_never_goes_below_zero(self):
        findings = [{"severity": "CRITICAL"}] * 5
        assert verdict.score_from_findings(findings) == 0

    def test_unknown_severity_uses_info_penalty(self):
        assert verdict.score_from_findings([{"severity": "WHATEVER"}]) == 97
