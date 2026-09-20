# Build It track fallback — scoping only, not yet committed to

Written as insurance while we wait on the AWS support case / a working account. Not
executed unless we explicitly decide to switch tracks. If we do switch, the target is: run
everything locally, demo via screen recording, submit under the hackathon's "Open source,
on your machine" track instead of "Ship It."

## The key insight: almost nothing changes

`core/rag.py` and `clients/bedrock.py` are the *only* files that talk to Bedrock. Every
other module (`resolver.py`, `grounding.py`, `nutrition.py`, `normalizer.py`, `verdict.py`,
`cache.py`, all the handlers, the whole `contract/`) is untouched — they call `rag.retrieve()`
and `bedrock.converse()` through the same function signatures regardless of what's actually
behind them. That's the payoff of the client/core split from day one.

## What would actually need to change

1. **`clients/bedrock.py::converse()`** — swap the `bedrock-runtime` call for a call to a
   locally-run open model via [Ollama](https://ollama.com) (e.g. `llama3.2` or `phi3.5`,
   both small enough to run on a laptop CPU). Same input (`system`, `messages`,
   `tool_schema`) and output shape (`{"text": ...}` or the parsed tool-call dict) — Ollama
   supports both a chat endpoint and structured/JSON output, close enough to swap in.

2. **`clients/bedrock.py::retrieve()` / `core/rag.py`** — replace Bedrock Knowledge Base
   Retrieve with a small local semantic search:
   - `sentence-transformers` (e.g. `all-MiniLM-L6-v2`) to embed `data/corpus/**/*.md` once
     at startup
   - cosine similarity (plain numpy, no need for faiss/OpenSearch at this corpus size —
     ~250 documents) to rank chunks for a query
   - same `RetrievedChunk` dataclass as the output, so `grounding.py` doesn't change at all

3. **Deployment shape** — instead of `sam deploy`, run the same handler functions behind a
   plain local HTTP server (FastAPI or even Python's `http.server` wrapping the existing
   `handler(event, context)` functions with a hand-built `event` dict). `apps/web/` and
   `apps/extension/` just point `API_BASE_URL` at `http://localhost:8000` instead of an
   API Gateway URL — both already support an env-configurable base URL, no changes needed
   there.

4. **DynamoDB** — either run `docker run amazon/dynamodb-local` (real DynamoDB API, zero
   code changes to `clients/ddb.py`), or skip caching entirely for the demo (analyze.py's
   `cache.get()`/`cache.put()` calls would need a no-op fallback - small change).

## What we lose

- No live URL → not eligible for the "Ship It" grand prize track specifically, only "Build
  It." Per the hackathon rules this is still a real prize track (2nd place), not a
  consolation.
- Weaker "fully managed AWS" story for judges — but the RAG design, the grounding guard,
  and the zero-hallucination architecture are unchanged and still the strongest part of
  the pitch.

## Rough time estimate if we commit to this

- `clients/bedrock.py` swap: ~45 min (mostly prompt-format adjustting for a smaller local
  model, which will need simpler/more explicit prompts than Claude)
- Local retrieval swap: ~30 min (sentence-transformers + numpy cosine sim is genuinely
  quick to wire up)
- Local server wrapper + smoke test: ~30 min
- Re-run the full `pytest` suite (should pass unchanged - it already mocks the Bedrock
  boundary, not Bedrock's actual output)
- Buffer for local-model prompt-following being weaker than Claude (may need 1-2 rounds of
  prompt simplification to get valid tool-call JSON reliably): ~30-60 min

**Total: ~2.5-3 hours from a cold start.** Worth starting only once we're confident the AWS
path won't resolve in time - not before.
