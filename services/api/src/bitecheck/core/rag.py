"""Retrieval half of the RAG pipeline.

Dispatches to one of two implementations based on `Config.ai_provider` (see
docs/TRD.md's "AI provider" section for why this switch exists):

- `"bedrock"` - Bedrock Knowledge Bases `Retrieve` (not `RetrieveAndGenerate`:
  RetrieveAndGenerate hands back prose we'd have to re-parse, and its citation structure
  isn't ours to control; Retrieve gives us raw chunks plus metadata, which is exactly what
  grounding.py needs to verify the model later).
- `"gemini"` (current default - Bedrock is account-blocked) - `core/local_retrieval.py`'s
  brand/keyword matching over the bundled corpus index.

Both paths return the same `RetrievedChunk` list, so `core/verdict.py` and
`core/grounding.py` are completely unaware of which one ran.
"""

from __future__ import annotations

from bitecheck.clients import bedrock
from bitecheck.config import Config
from bitecheck.core import local_retrieval
from bitecheck.core.grounding import RetrievedChunk
from bitecheck.core.normalizer import NormalizedProduct, build_retrieval_query


def _category_filter(category: str | None) -> dict | None:
    """Bedrock Knowledge Bases metadata filter restricting retrieval to one category.

    Deliberately unused (returns None -> no filter): the corpus is small and
    `core/normalizer.py`'s category guess is itself uncertain, so a filter risks excluding
    a real match because the upstream category call was wrong. The metadata field is
    already there for when it's needed:

        {"equals": {"key": "category", "value": category}}
    """
    return None


def _retrieve_bedrock(product: NormalizedProduct, top_k: int) -> list[RetrievedChunk]:
    config = Config.from_env()
    query = build_retrieval_query(product)
    raw = bedrock.retrieve(
        knowledge_base_id=config.knowledge_base_id,
        query=query,
        top_k=top_k,
        metadata_filter=_category_filter(product.category),
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


def retrieve(product: NormalizedProduct, top_k: int | None = None) -> list[RetrievedChunk]:
    """Find grounding candidates for this product. Never raises for "nothing found" - an
    empty result list just yields an empty chunk list, which core/verdict.py and
    core/grounding.py both already treat as a legitimate NO_DATA outcome. Genuine
    provider errors (bad KB ID, throttling, access denied, a Gemini HTTP failure) do
    propagate, since those are configuration problems the caller needs to know about, not
    "no adverse records" results.
    """
    config = Config.from_env()
    resolved_top_k = top_k or config.retrieval_top_k

    if config.ai_provider == "bedrock":
        return _retrieve_bedrock(product, resolved_top_k)

    return local_retrieval.retrieve(
        brand=product.brand,
        product_name=product.name,
        category=product.category,
        top_k=resolved_top_k,
    )
