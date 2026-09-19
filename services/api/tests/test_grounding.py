"""Grounding guard tests.

This is the file that proves we cannot publish an invented recall. Treat a failure here as
a release blocker, not a flaky test.
"""

from bitecheck.core.grounding import RetrievedChunk, enforce


def chunk(label, chunk_id="c1", issuer="EU RASFF", text="ethylene oxide 0.24 mg/kg"):
    return RetrievedChunk(
        chunk_id=chunk_id,
        text=text,
        s3_uri=f"s3://bitecheck-corpus/{chunk_id}.md",
        label=label,
        issuer=issuer,
        date="2024-04-22",
        source_url="https://example.org/notice",
    )


def finding(fid="f1", labels=("RASFF 2024.2893",)):
    return {
        "id": fid,
        "severity": "CRITICAL",
        "type": "CONTAMINANT",
        "scope": "BATCH",
        "title": "Ethylene oxide above limit",
        "detail": "...",
        "citations": [{"label": lbl} for lbl in labels],
    }


class TestEnforce:
    def test_keeps_grounded_finding(self):
        result = enforce([finding()], [chunk("RASFF 2024.2893")])
        assert len(result.findings) == 1
        assert result.dropped == 0

    def test_drops_finding_citing_a_document_not_retrieved(self):
        result = enforce([finding(labels=("RASFF 9999.0000",))], [chunk("RASFF 2024.2893")])
        assert result.findings == []
        assert result.dropped == 1
        assert "none of which were retrieved" in result.drop_reasons[0]

    def test_drops_finding_with_no_citations(self):
        bare = {**finding(), "citations": []}
        result = enforce([bare], [chunk("RASFF 2024.2893")])
        assert result.findings == []
        assert result.dropped == 1

    def test_empty_retrieval_drops_everything(self):
        """The corpus-is-empty case. Must yield nothing, never a softened warning."""
        result = enforce([finding(), finding("f2")], [])
        assert result.findings == []
        assert result.dropped == 2

    def test_citation_matching_tolerates_reformatting(self):
        """Models rewrite 'RASFF 2024.2893' as 'rasff-2024-2893'. Same document."""
        f = finding(labels=("rasff-2024-2893",))
        result = enforce([f], [chunk("RASFF 2024.2893")])
        assert len(result.findings) == 1

    def test_citation_metadata_comes_from_the_document_not_the_model(self):
        """A model that invents an issuer or a URL must not have it survive."""
        f = finding()
        f["citations"][0].update({"issuer": "Totally Made Up Authority",
                                  "sourceUrl": "https://evil.example/fake"})
        result = enforce([f], [chunk("RASFF 2024.2893")])
        citation = result.findings[0]["citations"][0]
        assert citation["issuer"] == "EU RASFF"
        assert citation["sourceUrl"] == "https://example.org/notice"

    def test_partially_grounded_finding_keeps_only_real_citations(self):
        f = finding(labels=("RASFF 2024.2893", "FSSAI Invented 12/2024"))
        result = enforce([f], [chunk("RASFF 2024.2893")])
        assert len(result.findings) == 1
        assert len(result.findings[0]["citations"]) == 1

    def test_matches_on_s3_uri(self):
        f = finding()
        f["citations"] = [{"s3Uri": "s3://bitecheck-corpus/c1.md"}]
        result = enforce([f], [chunk("RASFF 2024.2893")])
        assert len(result.findings) == 1

    def test_does_not_mutate_input(self):
        original = finding()
        enforce([original], [chunk("RASFF 2024.2893")])
        assert original["citations"] == [{"label": "RASFF 2024.2893"}]
