"""Local retrieval: brand/keyword matching over the bundled corpus index, used in place of
Bedrock Knowledge Bases while Bedrock access is unavailable (see docs/TRD.md's AI provider
section for the full story - this is a pivot, not the original plan).

No embeddings, no vector database. At ~250 short, well-tagged documents (each FoSCoS
record already carries the real brand name in its metadata), direct matching against that
metadata is both simpler to build and more precise than semantic search would be for this
corpus - we are not searching prose for meaning, we are looking up known brand names.

Returns the same `RetrievedChunk` shape `core/rag.py`'s Bedrock path returns, so
`core/verdict.py` and `core/grounding.py` need zero changes regardless of which retrieval
path is active. `core/rag.py::retrieve()` dispatches to this module when
`Config.ai_provider != "bedrock"`.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from bitecheck.core.grounding import RetrievedChunk

_INDEX_PATH = Path(__file__).resolve().parents[1] / "data" / "corpus_index.json"

# Tokens too generic to count as a meaningful brand-name match on their own.
_STOPWORDS = {
    "the", "and", "of", "for", "pvt", "ltd", "private", "limited", "company", "co",
    "foods", "food", "products", "product", "industries", "industry", "enterprises",
    "trading", "traders", "brand", "brands", "india", "indian",
}


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", " ", (text or "").lower()).strip()


def _tokens(text: str) -> set[str]:
    return {t for t in _normalize(text).split() if t and t not in _STOPWORDS and len(t) > 2}


@lru_cache(maxsize=1)
def _load_index() -> list[dict]:
    if not _INDEX_PATH.exists():
        return []
    return json.loads(_INDEX_PATH.read_text(encoding="utf-8"))


def _brand_score(query_brand: str, doc_brands: list[str]) -> float:
    """1.0 for a strong match, 0.0 for none. Substring match is checked first since it
    catches the common case (query "Everest" inside doc "Everest Tikhalal chilly powder")
    without needing token overlap at all."""
    if not query_brand or not doc_brands:
        return 0.0

    q_norm = _normalize(query_brand)
    q_tokens = _tokens(query_brand)
    best = 0.0

    for doc_brand in doc_brands:
        d_norm = _normalize(doc_brand)
        if not d_norm:
            continue
        if q_norm and (q_norm in d_norm or d_norm in q_norm):
            return 1.0  # substring match either direction - as strong as it gets here

        d_tokens = _tokens(doc_brand)
        if q_tokens and d_tokens:
            overlap = len(q_tokens & d_tokens) / len(q_tokens | d_tokens)
            best = max(best, overlap)

    return best


def _text_score(query: str, doc_text: str) -> float:
    q_tokens = _tokens(query)
    if not q_tokens:
        return 0.0
    d_tokens = _tokens(doc_text[:2000])  # cap - documents are short, but stay defensive
    if not d_tokens:
        return 0.0
    return len(q_tokens & d_tokens) / len(q_tokens)


def retrieve(
    brand: str | None,
    product_name: str,
    category: str | None = None,
    top_k: int = 8,
) -> list[RetrievedChunk]:
    """Score every indexed document against the query, return the top_k above a minimum
    relevance floor. Never raises - an empty/missing index just yields no chunks, which
    core/verdict.py and core/grounding.py already treat as a legitimate NO_DATA outcome.
    """
    index = _load_index()
    if not index:
        return []

    scored: list[tuple[float, dict]] = []
    for doc in index:
        brand_score = _brand_score(brand or "", doc.get("brands") or [])
        category_score = 0.3 if category and doc.get("category") == category else 0.0
        text_score = _text_score(f"{brand or ''} {product_name}", doc.get("text", ""))

        # Brand match dominates - a document about the right company is worth far more
        # than a document merely in the right category or sharing a few words.
        score = (brand_score * 3.0) + category_score + (text_score * 0.5)
        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda pair: pair[0], reverse=True)

    # Relevance floor: without this, a query for a brand with zero real matches would
    # still return the "closest" documents by weak text overlap, and the model might treat
    # a thin, unrelated document as license to say something. Require at least a partial
    # brand or category signal, not text overlap alone.
    chunks = []
    for score, doc in scored[:top_k]:
        if score < 0.3:
            continue
        chunks.append(
            RetrievedChunk(
                chunk_id=doc["id"],
                text=doc.get("text", ""),
                s3_uri=None,
                label=doc.get("orderRef") or doc.get("issuer"),
                issuer=doc.get("issuer"),
                date=doc.get("date"),
                source_url=doc.get("sourceUrl"),
                score=score,
            )
        )
    return chunks
