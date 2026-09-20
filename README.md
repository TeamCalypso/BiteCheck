# BiteCheck

A food-safety layer over Indian e-commerce. FSSAI bans, lab-test failures, and recall
notices for adulterated spices, unapproved protein powders, and mislabeled products exist
— but they live in PDF circulars nobody reads. BiteCheck cross-references the product
you're looking at against a Bedrock RAG knowledge base of regulator and lab documents, and
shows a grounded verdict with the exact circular or order reference, right on the page.

Built for the **WeMakeDevs × AWS First Commit** hackathon (Sept 17–20, 2026), **Ship It**
track.

- **Live web app:** https://main.d3koyuekptkg0v.amplifyapp.com
- **Live API:** https://5607b13rz9.execute-api.us-east-1.amazonaws.com/prod (`/v1/health`,
  `/v1/trending` are fully live; `/v1/analyze` and `/v1/grievance` are deployed but will
  error until Bedrock access clears — see `docs/TRD.md`'s Region & account section)
- **Demo video:** _add the YouTube link here_
- **Chrome extension:** load unpacked from `apps/extension/` (see below) — Chrome Web
  Store listing is out of scope for the hackathon deadline

## What it does

Two surfaces, one backend:

1. **Chrome extension (MV3)** — activates on `amazon.in` product pages, reads the page
   (title, brand, FSSAI licence number, nutrition table) directly in the user's own
   browser, and injects an inline verdict pill under the buy box. Click it for a slide-over
   drawer with findings, citations, nutrition, and a one-click FoSCoS grievance draft.
2. **Web app** — paste any Amazon.in product link and get the same analysis, rendered as a
   three.js particle swarm that splits into clusters proportional to the product's macro
   composition. This is the project's public, testable URL for the Ship It track.

Both call the same backend endpoint, `POST /v1/analyze` — see `contract/` for the frozen
API shape.

## Why it's trustworthy, not just plausible

Every finding BiteCheck shows is required to cite a document that was actually retrieved
from the knowledge base for that query. `services/api/src/bitecheck/core/grounding.py`
enforces this after generation: any claim that doesn't trace to a retrieved chunk is
dropped, and if nothing survives, the response is `NO_DATA` rather than a softened,
unsourced warning. We are making public claims about real food brands; a hallucinated
recall is not an acceptable failure mode. See `docs/TRD.md` for the retrieval design that
makes this checkable.

## Architecture

```
Chrome Extension (MV3)            Web App (Amplify Hosting)
  content script reads DOM          paste URL → parse ASIN + slug
        │                                   │
        └───────────► API Gateway (HTTP API, CORS) ◄──────┘
                              │
                    Lambda: AnalyzeFunction
                              │
        ┌─────────┬───────────┼────────────┬─────────────┐
        ▼         ▼           ▼            ▼             ▼
   DynamoDB   DynamoDB    Bedrock      Bedrock KB    Open Food
   cache      catalog     Converse     Retrieve      Facts API
   (TTL 24h)  (seeded)    (normalize   (S3 Vectors)  (nutrition
              │            + verdict)       │         fallback)
              │                             │
              │                    S3 corpus bucket
              │                    (FSSAI / RASFF / FDA / CFS docs)
              ▼
        GET /v1/trending  ──► web app "live advisories" panel
```

### AWS services and why

| Service | Role |
|---|---|
| **Amazon Bedrock Knowledge Bases** (S3 Vectors) | Managed RAG over the regulator/lab document corpus. S3 Vectors chosen over OpenSearch Serverless specifically to avoid its ~$350/mo OCU floor — see `docs/TRD.md`. |
| **Amazon Bedrock** (Converse) | Entity normalization + food gate (cheap model), and strict-schema verdict generation (stronger model). Model IDs resolved at bootstrap, never hardcoded. |
| **AWS Lambda** | Stateless orchestration for every route — `infra/template.yaml`. |
| **Amazon API Gateway** (HTTP API) | Public HTTPS entry point for both the extension and the web app, CORS-enabled. |
| **Amazon DynamoDB** | Global response cache (24h TTL, atomic hit counter, `TrendingIndex` GSI) and the curated demo catalog. |
| **Amazon S3** | Corpus storage for the knowledge base's data source. |
| **AWS Amplify Hosting** | Deploys the web app from this repo — the project's submission URL. |
| **Amazon EventBridge** | Scheduled daily corpus refresh (`handlers/ingest.py`, Phase 5). |

No self-managed infrastructure: everything above is a managed AWS service, entirely
serverless, zero idle compute cost when nobody is browsing.

## Repository layout

```
apps/web/            Web app (Vite + three.js particle swarm) — owner: Ritvik
apps/extension/       Chrome MV3 extension — owner: Ritvik
services/api/          Lambda backend (Python 3.12) — owner: Saket
contract/               Frozen API schema + fixtures — the boundary between all three lanes
infra/                  AWS SAM template
data/                   Knowledge base corpus + seed catalog — owner: Mahek
scripts/                 One-time/ops scripts: KB bootstrap, corpus build, seeding, teardown
docs/                    PRD, TRD, app flow, UI/UX brief, backend schema, data sources, demo script
```

See `CLAUDE.md` for lane ownership and non-negotiable engineering rules (most importantly:
**never scrape amazon.in server-side** — see `docs/TRD.md` for why that's structurally
impossible from Lambda, and how the resolver works around it).

## Setup

Prerequisites: Python 3.12, Node 18+, AWS SAM CLI, an AWS account with Bedrock model access
granted for Titan Text Embeddings v2 and your chosen Claude/Nova models (Bedrock console →
Model access — this is a manual approval step, request it early).

```bash
# backend tests (no AWS credentials required)
cd services/api && pip install -r requirements-dev.txt && python -m pytest -q

# one-time knowledge base bootstrap (creates S3 buckets, vector index, Bedrock KB)
python scripts/bootstrap_kb.py --corpus-bucket <your-bucket-name>

# fill in infra/samconfig.toml's parameter_overrides with the IDs bootstrap_kb.py printed,
# then deploy the app stack
sam build -t infra/template.yaml && sam deploy -t infra/template.yaml

# seed the demo catalog
python scripts/seed_dynamo.py

# load the extension: chrome://extensions → Developer mode → Load unpacked → apps/extension/
```

Tear everything down after judging:

```bash
bash scripts/teardown.sh
```

## Status

Early scaffold — see `implementation_plan.md` for the live step tracker across all three
lanes.

## License

See `LICENSE`.
