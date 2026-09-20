# BiteCheck

A food-safety layer over Indian e-commerce. FSSAI bans, lab-test failures, and recall
notices for adulterated spices, unapproved protein powders, and mislabeled products exist
— but they live in PDF circulars nobody reads. BiteCheck cross-references the product
you're looking at against a Bedrock RAG knowledge base of regulator and lab documents, and
shows a grounded verdict with the exact circular or order reference, right on the page.

Built for the **WeMakeDevs × AWS First Commit** hackathon (Sept 17–20, 2026), **Ship It**
track.

- **Live web app:** https://main.d3koyuekptkg0v.amplifyapp.com
- **Live API:** https://5607b13rz9.execute-api.us-east-1.amazonaws.com/prod — all four
  routes (`/v1/health`, `/v1/trending`, `/v1/analyze`, `/v1/grievance`) are live on real
  AWS with real AI calls (see "Why Gemini, not Bedrock, is live" below)
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

## Why Gemini, not Bedrock, is live

BiteCheck was designed and built around **Amazon Bedrock** end-to-end: Bedrock Converse for
entity extraction and verdict generation, Bedrock Knowledge Bases (S3 Vectors) for
retrieval. That code is fully written, tested, and still in the repo — it is simply not
what answers requests right now.

Partway through the build, Bedrock model invocation started failing account-wide with
`AccessDeniedException: Your account is currently being verified.` We spent significant
time ruling out region, IAM policy, Organizations SCPs, service quotas, and model choice as
the cause (see `docs/TRD.md`'s "Region & account" section for the full investigation) — the
hold is on AWS's side, on this specific account, and a support case is open. It did not
clear before the deadline.

The hackathon organizers confirmed Bedrock is not a requirement — only that the solution be
deployed on AWS — so we pivoted the LLM calls to **Google Gemini** (`gemini-3.5-flash` /
`gemini-3.5-flash-lite`, free tier) and replaced Bedrock Knowledge Bases with a **local
brand/keyword retrieval module** (`core/local_retrieval.py`) over a bundled index of the
same ~250-document regulator corpus. At this corpus size, keyword/brand matching finds the
right documents without needing embeddings at all.

Two things worth noting about how this was done:

- **Nothing Bedrock-related was deleted.** `clients/bedrock.py`, the Bedrock retrieval path
  in `core/rag.py`, and every Bedrock IAM policy and SAM parameter in `infra/template.yaml`
  are fully intact. A provider-agnostic dispatch facade (`clients/llm.py`) routes calls to
  Bedrock or Gemini based on one config flag, `AI_PROVIDER`. If Bedrock access clears,
  switching back is a one-parameter redeploy, not a rewrite.
- **This is genuine RAG, not a downgrade in rigor.** The grounding guard
  (`core/grounding.py`) runs identically regardless of which provider retrieved the chunks
  or generated the verdict — every finding still has to trace to an actually-retrieved
  document, or it's dropped. Verified live end-to-end: a real product title through Gemini
  normalization → local retrieval against the real corpus → Gemini verdict generation → the
  grounding guard → a correctly cited, real FSSAI/FoSCoS recall finding, batch number and
  all.

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
   DynamoDB   DynamoDB   clients/llm.py  core/rag.py   Open Food
   cache      catalog    (AI_PROVIDER    (AI_PROVIDER  Facts API
   (TTL 24h)  (seeded)    dispatch)       dispatch)    (nutrition
              │               │               │         fallback)
              │          ┌────┴────┐     ┌────┴────┐
              │          ▼         ▼     ▼         ▼
              │      Bedrock    Gemini  Bedrock   local_retrieval.py
              │      Converse   API     Retrieve  (bundled corpus
              │      (blocked-  (LIVE)  (blocked- index, brand/
              │       account)          account)  keyword match)
              │                             │           │
              │                    S3 corpus bucket   (same index,
              │                    (FSSAI / RASFF /    bundled at
              │                     FDA / CFS docs)     deploy time)
              ▼
        GET /v1/trending  ──► web app "live advisories" panel
```

Live path today is `AI_PROVIDER=gemini`: Gemini + `local_retrieval.py`. The Bedrock
Converse and Bedrock Retrieve boxes are fully implemented and deployed but idle, blocked by
the account-verification hold described above — see "Why Gemini, not Bedrock, is live."

### AWS services and why

| Service | Role |
|---|---|
| **Amazon Bedrock** (Converse + Knowledge Bases / S3 Vectors) | Built and deployed for entity normalization, verdict generation, and retrieval — currently idle pending account verification, but live-switchable via `AI_PROVIDER`. S3 Vectors was chosen over OpenSearch Serverless specifically to avoid its ~$350/mo OCU floor — see `docs/TRD.md`. |
| **Google Gemini** (not AWS — see note above) | Currently active LLM for entity normalization and verdict generation, dispatched through the same `clients/llm.py` facade Bedrock uses. |
| **AWS Lambda** | Stateless orchestration for every route — `infra/template.yaml`. |
| **Amazon API Gateway** (HTTP API) | Public HTTPS entry point for both the extension and the web app, CORS-enabled. |
| **Amazon DynamoDB** | Global response cache (24h TTL, atomic hit counter, `TrendingIndex` GSI) and the curated demo catalog. |
| **Amazon S3** | Corpus storage for the knowledge base's data source (Bedrock path). |
| **AWS Amplify Hosting** | Deploys the web app from this repo — the project's submission URL. |
| **Amazon EventBridge** | Scheduled daily corpus refresh (`handlers/ingest.py`) — written, not yet enabled; see the plan's cut list. |

Everything except the Gemini API call itself is a managed AWS service, entirely
serverless, with zero idle compute cost when nobody is browsing. The AWS integration is not
just Bedrock — Lambda, API Gateway, DynamoDB, S3, and Amplify Hosting are all real,
deployed, and load-bearing regardless of which AI provider answers a given request.

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

Prerequisites: Python 3.12, Node 18+, AWS SAM CLI, Docker (for `sam build --use-container`,
needed because the Lambda runtime is arm64/Python 3.12 and local dev machines often aren't).

```bash
# backend tests (no AWS account or credentials required — Bedrock/Gemini and DynamoDB are
# mocked)
cd services/api && pip install -r requirements-dev.txt && python -m pytest -q

# build the corpus index consumed by the live (Gemini) retrieval path
python scripts/build_corpus_index.py

# deploy the app stack — pass your own Gemini key on the command line, never commit it
sam build -t infra/template.yaml --use-container
sam deploy -t infra/template.yaml --parameter-overrides AiProvider=gemini GeminiApiKey=$GEMINI_API_KEY

# seed the demo catalog
python scripts/seed_dynamo.py

# load the extension: chrome://extensions → Developer mode → Load unpacked → apps/extension/
```

To run the original Bedrock path instead (once account access clears): request Bedrock
model access for Titan Text Embeddings v2 and your chosen Claude/Nova models, run
`python scripts/bootstrap_kb.py --corpus-bucket <your-bucket-name>`, fill the resulting IDs
into `infra/samconfig.toml`, and redeploy with `--parameter-overrides AiProvider=bedrock`.
No code changes required.

Tear everything down after judging:

```bash
bash scripts/teardown.sh
```

## Status

Live end-to-end on real AWS: backend (Lambda + API Gateway + DynamoDB) deployed, web app
live on Amplify Hosting, all four API routes working with real Gemini calls and real
grounded FSSAI/FoSCoS citations, 160 backend tests passing. See `implementation_plan.md`
for the full step tracker and what's left before submission.

## Frontend & 3D Particle Visualization Engine
The BiteCheck web client (`apps/web/`) is built with **Vite**, **Vanilla JS/CSS**, and a custom **Three.js WebGL Particle Engine** that turns dry nutritional and regulatory data into an interactive, physics-driven molecular simulation.
### <img width="1000" height="563" alt="Frontend initial (1)" src="https://github.com/user-attachments/assets/87edc4a1-ad32-4720-9167-8dc7bf6b7f8d" />

### 3D Particle Engine Highlights
* **36,000 GPU-Accelerated Particles:** High-performance particle simulation running at 60 FPS via custom GLSL vertex and fragment shaders with real-time sphere normal mapping, diffuse directional lighting, and rim-light Fresnel shading.
* **GPU Fluid Turbulence:** Custom vertex-shader procedural noise creates fluid, organic wave turbulence and breathing motion across all particle states.
* **Proportional Macronutrient Partitioning:** When an Amazon product is analyzed, particles dynamically subdivide into up to 8 isolated molecular clusters whose volumes directly match the product's actual macronutrient breakdown (Proteins, Carbs, Fats, Fiber, Sugars, Sodium, etc.).
* **Semantic Colorization & Shading:** Smooth shader interpolation transitions particles from ambient pearl-slate to distinct semantic nutritional color palettes (e.g., emerald for protein, amber for carbs, crimson for fats).
* **State-Driven Particle Lifecycle:**
  * `INTRO_SWIRL` → `INTRO_LOGO` (assembles BiteCheck 3D brandmark & typography) → `INTRO_DISPERSE` (dissolves into ambient space).
  * `AMBIENT`: Physics-based cursor interaction with real-time mouse repulsion and 3D camera parallax.
  * `SCANNING`: Concentric orbital compression and high-energy particle beams while the backend Bedrock pipeline executes.
  * `MOLECULES`: Autonomous orbital rotation of macro clusters with interactive focus and inspection.
  * `NOT_FOOD`: Rejection scatter dynamics when non-food items or unparseable URLs are detected.
### <img width="1000" height="563" alt="Frontend second (1)" src="https://github.com/user-attachments/assets/60ae7873-90c8-4ef2-adce-4d36c09ce5c5" />
### Frontend UI & HUD Architecture
* **Cinematic Camera Framing:** Dynamic lerped camera transitions that seamlessly pan, zoom, and frame the 3D particle bay as the inspection drawer opens and closes.
* **Clinical Glassmorphic HUD:** Dark-mode interface designed with deep obsidian tones, neon telemetry accents, and crisp typography (Inter + JetBrains Mono).
* **Instant URL & ASIN Resolver:** One-click sample product pills and live Amazon.in URL parser triggering instantaneous query normalization.
* **Inspection Bay & Safety Drawer:** Displays grounded FSSAI recall notices, violation severity pills, allergen warnings, full macro/micro breakdown, and a one-click FoSCoS grievance draft.
* **Zero Bloat, Maximum Speed:** Pure Vanilla CSS and ES modules bundled with Vite for ultra-low latency and instant cold loads on AWS Amplify.


## License

See `LICENSE`.
