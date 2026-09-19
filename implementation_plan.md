# Implementation Plan — Live Step Tracker

Full context, architecture, and reasoning live in `README.md` and `docs/`. This file is
just the checklist — read it first when picking work back up mid-sprint.

Owners: **Saket** (backend/infra/deploy/extension), **Mahek** (knowledge base/AI),
**Ritvik** (web frontend). Deadline: Sept 20, 2026 (Ship It track).

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
- [x] `apps/extension/` MV3 shell: manifest, content script, background worker, DOM
      reader, Shadow DOM UI (pill + drawer)
- [x] Docs: PRD, TRD, app-flow, ui-ux-brief, backend-schema, data-sources, demo-script
- [ ] Push to `github.com/TeamCalypso/BiteCheck`, confirm repo is **public**
- [ ] Saket: AWS account confirmed, `us-east-1`, Bedrock model access requested for Titan
      Text Embeddings v2 + chosen Claude/Nova models (do this immediately — approval can
      lag)
- [ ] Ritvik: pull this scaffold, start the Vite + React + TS + R3F project in `apps/web/`
      against `contract/fixtures/*.json`
- [ ] Mahek: start pulling the first ~20 source documents into `data/sources/` per
      `docs/data-sources.md`

## Phase 1 — Knowledge base + API skeleton

- [ ] Mahek: `data/sources/` → `scripts/build_corpus.py` → `data/corpus/`, first 20 docs
- [ ] Saket: implement `scripts/bootstrap_kb.py` for real — corpus bucket, S3 vector
      bucket/index, Bedrock KB (`S3_VECTORS`), data source, first ingestion job; write
      `infra/kb-outputs.json`
- [ ] Saket: implement `clients/bedrock.py::resolve_model_ids()`, fill
      `infra/samconfig.toml` parameters
- [ ] Saket: implement `handlers/health.py` fully (done as stub — verify once deployed),
      `sam deploy` a first pass with `analyze` still returning a fixture. **Get a live URL
      up early.**
- [ ] Ritvik: idle-state swarm rendering, wired to fixtures

## Phase 2 — Real analysis engine

- [ ] `core/cache.py` + `clients/ddb.py` (cache get/put/record_hit/trending)
- [ ] `scripts/seed_dynamo.py::seed()` implemented; `data/seed/products.json` populated
      with ~30 real ASINs across the 4 demo states
- [ ] `core/normalizer.py` (Bedrock Converse entity extraction + food gate)
- [ ] `clients/openfoodfacts.py` + `core/nutrition.py` (label → OFF → catalog, per-100g,
      `other` remainder math)
- [ ] `core/rag.py::retrieve()` (bedrock-agent-runtime Retrieve)
- [ ] `core/verdict.py::assess()` (Converse, strict schema) — grounding.py already done
- [ ] `handlers/analyze.py` wired end-to-end
- [ ] Mahek: prompt iteration against real demo ASINs; corpus to 40+ docs; re-sync KB
- [ ] `pytest` coverage on nutrition math and schema conformance of real (not fixture)
      responses

## Phase 3 — Surfaces

- [ ] `apps/extension/src/config.js::API_BASE_URL` updated to the deployed API
- [ ] Extension tested unpacked on 5 real amazon.in product pages, including a variant
      switch and a non-food item
- [ ] Ritvik: swarm split driven by real `nutrition.macros`, result panel, demo cards,
      trending ticker wired to `GET /v1/trending`
- [ ] Amplify Hosting connected to `main` — **this URL is the submission URL**

## Phase 4 — Sleep

- [ ] Actually do this

## Phase 5 — Completion + polish

- [ ] `handlers/grievance.py` implemented
- [ ] `handlers/trending.py` implemented (GSI query)
- [ ] `handlers/ingest.py` implemented, `DailySync` schedule flipped to `Enabled: true`
- [ ] `alternatives[]` populated from the catalog
- [ ] Error/empty/not-food states verified on both surfaces
- [ ] CORS verified from the Amplify origin and from `https://www.amazon.in`

## Phase 6 — Submission

- [ ] `README.md` finished with real URLs filled in
- [ ] Demo video recorded per `docs/demo-script.md`, uploaded to YouTube
      public/unlisted, **verified to open in a signed-out browser**
- [ ] Written explanation submitted (problem, build, AWS integration)
- [ ] Eligibility confirmed for all three members (18+, Indian university student, AWS
      Builder Center profile, enrollment verified)
- [ ] Final `scripts/teardown.sh` run after judging closes

## Cut list, in priority order, if time runs short

1. `handlers/ingest.py` scheduling
2. `alternatives[]`
3. `handlers/grievance.py`
4. `handlers/trending.py` / the live advisories ticker

**Never cut:** the grounding guard, citations on every finding, the live web app URL.
