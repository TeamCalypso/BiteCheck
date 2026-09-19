"""Retrieval half of the RAG pipeline.

We deliberately call Bedrock `Retrieve` rather than `RetrieveAndGenerate`. RetrieveAndGenerate
hands back prose we would then have to re-parse, and its citation structure is not ours to
control. Retrieve gives us the raw chunks plus their metadata, which is exactly what
grounding.py needs to verify the model later - see docs/TRD.md for the full reasoning.
"""

from __future__ import annotations

from bitecheck.clients import bedrock
from bitecheck.config import Config
from bitecheck.core.grounding import RetrievedChunk


def _category_filter(category: str | None) -> dict | None:
    """Bedrock Knowledge Bases metadata filter restricting retrieval to one category.

    Deliberately unused (returns None -> no filter) for this build: the corpus is small
    (40-60 documents) and `core/normalizer.py`'s category guess is itself uncertain, so a
    filter risks excluding a real match because the upstream category call was wrong.
    Worth revisiting once the corpus and category accuracy both grow - the metadata field
    (`category` in each document's .metadata.json) is already there for when it's needed:

        {"equals": {"key": "category", "value": category}}
    """
    return None


def retrieve(query: str, category: str | None = None, top_k: int | None = None) -> list[RetrievedChunk]:
    """Query the knowledge base, returning ranked, citation-ready chunks.

    Never raises for "nothing found" - an empty retrievalResults list just yields an empty
    chunk list, which core/verdict.py and core/grounding.py both already treat as a
    legitimate NO_DATA outcome. Genuine Bedrock errors (bad KB ID, throttling, access
    denied) do propagate, since those are configuration problems the caller needs to know
    about, not "no adverse records" results.
    """
    config = Config.from_env()
    raw = bedrock.retrieve(
        knowledge_base_id=config.knowledge_base_id,
        query=query,
        top_k=top_k or config.retrieval_top_k,
        metadata_filter=_category_filter(category),
    )

    chunks: list[RetrievedChunk] = []
    for result in raw.get("retrievalResults", []):
        content = result.get("content") or {}
        location = result.get("location") or {}
        metadata = result.get("metadata") or {}
        s3_location = location.get("s3Location") or {}
        s3_uri = s3_location.get("uri")

        chunks.append(
            RetrievedChunk(
                # Bedrock's own chunk id isn't in the metadata dict by default; fall back
                # to the S3 URI, which is unique per source document and good enough for
                # grounding.py's index (it also indexes by label and s3_uri).
                chunk_id=s3_uri or "",
                text=content.get("text", ""),
                s3_uri=s3_uri,
                # These three come from each document's .metadata.json sidecar (see
                # scripts/build_corpus.py / docs/backend-schema.md) and are what
                # core/grounding.py rewrites every surviving citation from.
                label=metadata.get("orderRef") or metadata.get("issuer"),
                issuer=metadata.get("issuer"),
                date=metadata.get("date"),
                source_url=metadata.get("sourceUrl"),
                score=result.get("score", 0.0),
            )
        )
    return chunks
