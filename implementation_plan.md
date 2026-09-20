# Implementation Plan — Live Step Tracker

Full context, architecture, and reasoning live in `README.md` and `docs/`. This file is
just the checklist — read it first when picking work back up mid-sprint.

Owners: **Saket** (backend/infra/deploy), **Mahek** (knowledge base/AI),
**Ritvik** (web app + Chrome extension). Deadline: Sept 20, 2026 (Ship It track).

## Phase 0 — Foundation

- [x] Repo structure created and pushed
- [x] `contract/analyze.schema.json` + `analyze.request.schema.json` frozen
- [x] 4 fixtures written and validated against the schema (`critical-spice`,
      `caution-protein`, `clear-turmeric`, `not-food`)
- [x] `CLAUDE.md`, root `README.md`, `.gitignore` written
- [x] Backend package skeleton: `core/`, `clients/`, `handlers/` stubs, `models.py`
      mirroring the schema, `config.py`
- [x] `resolver.py` and `grounding.py` fully implemented and unit-tested (the two modules
      that needed zero AWS access to build and are structurally load-bearing)
- [x] `infra/template.yaml` (SAM) + `infra/samconfig.toml` skeleton
- [x] `scripts/bootstrap_kb.py`, `build_corpus.py`, `seed_dynamo.py`, `teardown.sh`
      scaffolded with real CLI shape and TODOs
- [x] Docs: PRD, TRD, app-flow, ui-ux-brief, backend-schema, data-sources, demo-script
- [x] Push to `github.com/TeamCalypso/BiteCheck`, confirm repo is **public**
- [x] Saket: AWS account eventually got $140 credits, but **Bedrock invocation remains
      blocked account-wide** by an AWS-side "account currently being verified" hold —
      ruled out IAM, SCPs, region, quotas, and model type as the cause (see `docs/TRD.md`'s
      "Region & account" section). Support case filed. **No longer the critical path
      blocker** — see the AI provider pivot below, which unblocked everything else.
- [x] Ritvik: `apps/web/` built (vanilla JS + three.js, not React/R3F as originally
      planned — a fine simplification, docs corrected) and **live on Amplify Hosting**.
      `apps/extension/` built too — see `apps/extension/README.md` for the original
      handoff brief.
- [x] Mahek: sourced and merged FSSAI labelling regulation + 205 FoSCoS recall records
      (PRs #1, #2) — this became the real, live knowledge base once the AI provider
      pivoted to local retrieval (see Phase 1).

> **AI provider pivot (Sept 20):** Bedrock access never cleared in time. Per the hackathon
> organizer's own guidance ("Bedrock is not mandatory... use whatever other AI tools you
> like, the only thing we ask is that you deploy on AWS"), pivoted to **Google Gemini**
> (`gemini-3.5-flash` / `gemini-3.5-flash-lite`, free tier) for the LLM calls, and to a
> **local brand/keyword retrieval** module (`core/local_retrieval.py`) over a bundled
> corpus index instead of Bedrock Knowledge Bases — no embeddings needed at ~250 documents
> each already tagged with real brand names. **Nothing Bedrock-related was deleted** —
> `clients/bedrock.py` and the Bedrock retrieval path in `core/rag.py` are fully intact,
> dispatched via an `AI_PROVIDER` config flag. Flipping back is a one-parameter change if
> Bedrock access ever clears. See `docs/TRD.md`'s "AI provider" section for the full story.
>
> This is now **verified working end-to-end on live AWS**: a real product title through
> Gemini normalization → local retrieval against the real corpus → Gemini verdict
> generation → the grounding guard → a correctly cited, real FSSAI recall finding. Not a
> fixture, not a demo shortcut — genuine RAG over genuine regulator data.

## Phase 1 — Knowledge base + API skeleton

- [x] Mahek: FSSAI labelling regulation + 205 FoSCoS recall records merged into
      `data/corpus/` (PRs #1, #2) — bundled into `services/api/src/bitecheck/data/
      corpus_index.json` via `scripts/build_corpus_index.py` and serving as the real,
      live knowledge base (local retrieval, not Bedrock KB — see the pivot note above)
- [ ] `scripts/bootstrap_kb.py` — written and ready, but not run: no longer on the
      critical path since the AI provider pivot. Would only matter again if Bedrock
      access clears and we switch back.
- [x] Saket: `sam deploy` — **live, Sept 20**, now with real Gemini configuration:
      https://5607b13rz9.execute-api.us-east-1.amazonaws.com/prod . All four routes
      (`/v1/health`, `/v1/trending`, `/v1/analyze`, `/v1/grievance`) confirmed working
      against real AWS with real Gemini calls.
- [x] Ritvik: idle-state swarm rendering, wired to fixtures
- [x] Ritvik: **Amplify Hosting live**, Sept 20:
      https://main.d3koyuekptkg0v.amplifyapp.com , `VITE_API_BASE_URL` wired to the
      real API above. Confirmed loading cleanly, no console errors.

## Phase 2 — Real analysis engine

- [x] `core/cache.py` + `clients/ddb.py` (cache get/put/record_hit/trending) — implemented
      and unit-tested against a moto-simulated DynamoDB, no AWS account needed
- [x] `scripts/seed_dynamo.py::seed()` implemented and smoke-tested (moto) — including a
      float→Decimal fix that would otherwise have crashed on first real run.
      `data/seed/products.json` still needs the ~30 real ASINs filled in — **Mahek's task**
- [x] `core/normalizer.py` (entity extraction + food gate, via `clients/llm.py`'s
      provider dispatch) — unit-tested with mocks, **and verified live against real
      Gemini**: correctly extracted brand/category/confidence from a real product title
- [x] `clients/openfoodfacts.py` + `core/nutrition.py` (label → OFF → catalog → AI estimate,
      per-100g, `other` remainder math, sugar/sat-fat netted out of their parent macro) —
      fully implemented, unit-tested (167 tests now, +7 for the new fallback), and
      confirmed working live (real Open Food Facts data in a real response)
- [x] Added a 4th nutrition fallback, `core/nutrition.py::_from_gemini_estimate()`: when a
      product has no extension-scraped label, no Open Food Facts match, and no seed-catalog
      entry (i.e. any product a judge pastes that isn't one of Mahek's ~30 ASINs), ask the
      active LLM for a typical per-100g estimate so the web app's swarm still splits instead
      of showing nothing. Tagged `confidence="LOW"`/`source="ai_estimate"` plus a new
      `AI_ESTIMATED_NUTRITION` flag so it's never mistaken for a real label — and it never
      touches `findings[]` or the grounding guard, so the zero-hallucination safety
      guarantee is untouched. Cost-checked: only fires on a cache miss where every real
      source already failed, uses the cheap/fast model (same one `normalize()` already
      calls), and is cached for 24h afterward like the rest of the response — verified live
      against real Gemini with a deliberately obscure fictional product (plausible macros,
      summed to exactly 100%).
- [x] `core/rag.py::retrieve()` — dispatches to Bedrock Retrieve or
      `core/local_retrieval.py` (brand/keyword matching, no embeddings) based on
      `AI_PROVIDER`. **Verified live**: correctly surfaced the real FoSCoS recall for a
      real product from the real 206-document corpus.
- [x] `core/verdict.py::assess()` (strict schema, via `clients/llm.py`) — unit-tested,
      **and verified live**: Gemini correctly produced a grounded CRITICAL verdict citing
      the real recall, and the grounding guard passed it with 0 findings dropped
- [x] `handlers/analyze.py` wired end-to-end — integration-tested (mocked) and now
      **confirmed live on real AWS + real Gemini + real corpus data**, full response
      shape, real batch number, real citation
- [x] `handlers/trending.py`, `handlers/grievance.py` implemented, unit-tested, **and
      grievance confirmed live** — produced a correctly formatted, correctly cited FoSCoS
      complaint draft from a real cached analysis
- [x] Mahek: prompt iteration against real demo ASINs is now genuinely possible any time
      (Gemini + local retrieval are live) — no longer blocked on anything AWS-side;
      corpus can keep growing via the existing PR workflow
- [x] `pytest` coverage: **160 passing, 1 skipped**, zero AWS account required to run any
      of it (`cd services/api && python -m pytest -q`)

## Phase 3 — Surfaces

- [x] Ritvik: `apps/extension/` built from `apps/extension/README.md`'s brief — manifest,
      content script (DOM reader), background service worker (owns the fetch, not the
      content script — see the README for why), Shadow DOM pill + drawer per
      `docs/ui-ux-brief.md`
- [x] Ritvik: API base URL wired to the deployed endpoint (`apps/extension/src/config.js`,
      `manifest.json` host_permissions)
- [x] Extension tested unpacked on real amazon.in product pages — **Ritvik confirms testing
      complete**
- [x] Ritvik: swarm split driven by real `nutrition.macros`, result panel, demo cards,
      trending ticker wired to `GET /v1/trending`. Ritvik flagged some web-app links not
      splitting into the swarm — traced to `nutrition` coming back `null` for products
      Open Food Facts doesn't recognize and the seed catalog doesn't have yet (see Phase 2)
      — not a wiring bug, resolves as Mahek's ASIN seeding lands.
- [x] Amplify Hosting connected to `main` — **this URL is the submission URL** (live, see
      Phase 1)

## Phase 4 — Sleep

- [ ] Actually do this

## Phase 5 — Completion + polish

- [x] `handlers/grievance.py` implemented (moved up — see Phase 2)
- [x] `handlers/trending.py` implemented (moved up — see Phase 2)
- [x] ~~`handlers/ingest.py` implemented, `DailySync` schedule flipped to `Enabled: true`~~
      — **decided to cut.** Not needed for the demo; the corpus is already loaded and
      static, so a daily refresh job has nothing to prove for judging.
- [ ] `alternatives[]` populated from the catalog — **explicitly deprioritized for now**;
      revisit only if time remains after Phase 6
- [x] Error/empty/not-food states verified on both surfaces — **Ritvik confirms verified**
- [x] ~~Tighten `infra/template.yaml`'s `AllowedOrigin`~~ — **decided not needed.** The
      extension is only being loaded unpacked for the demo, never published, so
      `chrome-extension://jhncindnmmcjbbejjjgghgkljmbibakk` already works fine against the
      current `AllowedOrigin: *` with zero changes. Narrowing CORS now would only be
      security hardening, not something the demo needs, and isn't worth a redeploy risk
      this close to the deadline. Left as a possible post-hackathon cleanup.

## Phase 6 — Submission

- [x] `README.md` finished with real URLs filled in, plus the "Why Gemini, not Bedrock, is
      live" section explaining the account-verification hold and the provider pivot
- [ ] Demo video recorded per `docs/demo-script.md`, uploaded to YouTube
      public/unlisted, **verified to open in a signed-out browser**
- [ ] Written explanation submitted (problem, build, AWS integration)
- [ ] Eligibility confirmed for all three members (18+, Indian university student, AWS
      Builder Center profile, enrollment verified)
- [ ] Final `scripts/teardown.sh` run after judging closes

## Cut list, in priority order, if time runs short

1. ~~`handlers/ingest.py` scheduling~~ — cut, decided Sept 20
2. `alternatives[]`

(`handlers/grievance.py` and `handlers/trending.py` are already done, so they're off this
list — no longer a time trade-off.)

**Never cut:** the grounding guard, citations on every finding, the live web app URL.
