# Backend Schema

## DynamoDB tables

Both `PAY_PER_REQUEST` (on-demand) — no capacity planning needed for a hackathon traffic
pattern, and it avoids the OpenSearch-Serverless-style fixed-cost floor entirely (see
`docs/TRD.md` for why that mattered for the vector store decision too). Defined in
`infra/template.yaml`.

### `bitecheck-cache`

The global cache: the mechanism behind "if a product is trending, don't re-run Bedrock for
every shopper looking at it."

| Attribute | Type | Notes |
|---|---|---|
| `asin` (PK) | S | partition key |
| `payload` | S | full `AnalyzeResponse` JSON, as returned to clients |
| `verdictStatus` | S | denormalized from `payload.verdict.status`, for quick filtering |
| `brand` | S | denormalized |
| `productName` | S | denormalized |
| `hitCount` | N | incremented atomically on every read; also the GSI sort key |
| `lastAccessed` | N | epoch seconds |
| `ttl` | N | epoch seconds, 24h out; DynamoDB TTL is enabled on this attribute |
| `trendBucket` | S | constant `"TREND"` on every item — see GSI below |

**GSI: `TrendingIndex`** — PK `trendBucket` (always `"TREND"`), SK `hitCount` (N).
`GET /v1/trending` is one `Query` against this index with `ScanIndexForward=false` and a
`Limit`, returning the top-N most-requested products with no Bedrock cost and no table
scan. This is the entire implementation of the "trending products cache instantly"
requirement from the original project brief.

Access pattern:
- `GetItem(asin)` — cache lookup on every `/v1/analyze` call, before anything else runs.
- `UpdateItem(asin)` — atomic `ADD hitCount :one SET lastAccessed = :now` on a hit.
- `PutItem` — write-through after a fresh RAG pipeline run.
- `Query(TrendingIndex)` — `GET /v1/trending`.

### `bitecheck-catalog`

Curated enrichment data, seeded once from `data/seed/products.json` by
`scripts/seed_dynamo.py`. **Never a substitute for live retrieval** — see the
non-negotiable rule in the repo's `CLAUDE.md`. Its job is to make demo ASINs resolve to a
clean, human-verified identity instantly instead of depending on the normalizer guessing
right under demo pressure.

| Attribute | Type | Notes |
|---|---|---|
| `asin` (PK) | S | partition key |
| `brand` | S | |
| `name` | S | |
| `category` | S | matches the `Category` enum in `contract/analyze.schema.json` |
| `netQuantity` | S | optional |
| `fssaiLicense` | S | optional |
| `nutrition` | M | optional, per-100g map, used only if the label/OFF path finds nothing |
| `notes` | S | optional, free text |

Access pattern: `GetItem(asin)`, read-only from the API's perspective (writes only happen
via the seed script).

## S3 buckets

Managed outside `infra/template.yaml` by `scripts/bootstrap_kb.py` (see `docs/TRD.md` for
why these are bootstrapped separately from the redeployed stack):

- **Corpus bucket** — normalized markdown + `.metadata.json` sidecars, the Bedrock
  Knowledge Base's data source. Structure mirrors `data/corpus/<issuer>/<slug>.md` +
  `<slug>.md.metadata.json` (see `scripts/build_corpus.py`).
- **S3 Vectors bucket + index** — the embedding store the KB queries against. Cosine
  distance, Titan Text Embeddings v2, 1024 dimensions.

## Knowledge base document metadata shape

Each corpus document's `.metadata.json` sidecar (see `scripts/build_corpus.py`'s
`CorpusDoc` dataclass):

```jsonc
{
  "issuer": "EU RASFF",                          // required
  "docType": "recall",                            // required: recall|alert|regulation|judgment|lab_report|guideline
  "category": "spices_blends",                     // required, matches contract's Category enum
  "date": "2024-04-22",                            // required
  "brands": ["Everest"],
  "hazards": ["ethylene_oxide"],
  "orderRef": "RASFF 2024.2893",
  "sourceUrl": "https://webgate.ec.europa.eu/rasff-window/..."
}
```

Kept lean deliberately: S3 Vectors caps attached metadata at 35 keys / 1KB filterable per
vector (`docs/TRD.md`). `scripts/build_corpus.py::validate_metadata()` enforces the
required fields and the size limit before anything is uploaded.

## Retrieved-chunk shape (runtime, not stored)

What `core/rag.py::retrieve()` returns and what `core/grounding.py::RetrievedChunk` models
— this is the bridge between the KB's metadata and a finding's citation:

```python
RetrievedChunk(
    chunk_id: str,       # Bedrock's chunk identifier
    text: str,            # the chunk content, used for excerpt + as the grounding source of truth
    s3_uri: str | None,   # source document location
    label: str | None,    # human label, e.g. from metadata.orderRef
    issuer: str | None,
    date: str | None,
    source_url: str | None,
    score: float = 0.0,   # retrieval relevance score
)
```

`core/grounding.py::enforce()` rewrites every surviving citation's `issuer`/`date`/
`sourceUrl`/`excerpt` from this struct, never from the model's own output — see the
grounding guard's docstring for why.
