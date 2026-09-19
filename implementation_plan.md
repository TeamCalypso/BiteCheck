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
- [ ] Saket: AWS account verified but showing **$0 credits** on two accounts so far (see
      note below) — Bedrock model access still blocked on this. **Currently the critical
      path blocker for everything in Phase 1.**
- [ ] Ritvik: pull this scaffold, start the Vite + React + TS + R3F project in `apps/web/`
      against `contract/fixtures/*.json`; also owns `apps/extension/` (MV3 Chrome
      extension) — see `apps/extension/README.md` for the handoff brief (contract, the
      Shadow DOM requirement, SPA-nav handling). An earlier draft of the extension was
      written by Saket and removed on Sept 20 — ownership moved to match `CLAUDE.md`,
      which always specified `apps/extension/` as frontend, not backend
- [ ] Mahek + Saket: start pulling the first ~20 source documents into `data/sources/` per
      `docs/data-sources.md`

> **AWS account status (Sept 20):** original account verified but shows $0 available
> credits (likely excluded from new-account promos since it was created long ago, even
> though only just verified). Hackathon's $100 team credit form submitted, coupon email
> not yet received. Pivoting to a second, genuinely new AWS account on a separate email,
> plus checking AWS Educate. Real project cost is small (<$10 total per `docs/TRD.md`) so
> once *any* account has a verified payment method, we are unblocked even without credits
> — Bedrock is the only pay-from-token-one service in our stack; everything else is
> free-tier.

## Phase 1 — Knowledge base + API skeleton

- [ ] Mahek + Saket: `data/sources/` → `scripts/build_corpus.py` → `data/corpus/`, first 20 docs
- [ ] Saket: implement `scripts/bootstrap_kb.py` for real — corpus bucket, S3 vector
      bucket/index, Bedrock KB (`S3_VECTORS`), data source, first ingestion job; write
      `infra/kb-outputs.json`. **Blocked on AWS account access.**
- [ ] Saket: implement `clients/bedrock.py::resolve_model_ids()`, fill
      `infra/samconfig.toml` parameters. **Blocked on AWS account access.**
- [ ] Saket: `sam deploy` a first pass. **Get a live URL up as soon as AWS is unblocked.**
- [ ] Ritvik: idle-state swarm rendering, wired to fixtures

## Phase 2 — Real analysis engine

- [x] `core/cache.py` + `clients/ddb.py` (cache get/put/record_hit/trending) — implemented
      and unit-tested against a moto-simulated DynamoDB, no AWS account needed
- [x] `scripts/seed_dynamo.py::seed()` implemented and smoke-tested (moto) — including a
      float→Decimal fix that would otherwise have crashed on first real run.
      `data/seed/products.json` still needs the ~30 real ASINs filled in (Saket + Mahek)
- [x] `core/normalizer.py` (Bedrock Converse entity extraction + food gate) — written,
      unit-tested with a mocked Bedrock call. Real correctness (does it actually normalize
      well) can only be confirmed once Bedrock access exists
- [x] `clients/openfoodfacts.py` + `core/nutrition.py` (label → OFF → catalog, per-100g,
      `other` remainder math, sugar/sat-fat netted out of their parent macro) — fully
      implemented and unit-tested, including the float-formatting bug caught by tests
- [x] `core/rag.py::retrieve()` (bedrock-agent-runtime Retrieve) — written, correctness
      pending real Bedrock access to verify against
- [x] `core/verdict.py::assess()` (Converse, strict schema) — written and unit-tested with
      a mocked Bedrock call; `score_from_findings()` recomputes the score post-grounding
- [x] `handlers/analyze.py` wired end-to-end — full pipeline integration-tested with
      Bedrock/Open Food Facts faked and DynamoDB via moto; response validated against
      `contract/analyze.schema.json` in the test itself. Caught and fixed a real schema
      violation (`meta.latencyMs` was `null` on the not-food path) before it could ship
- [x] `handlers/trending.py`, `handlers/grievance.py` implemented and unit-tested (moved up
      from Phase 5 since they were quick once analyze.py's plumbing existed)
- [ ] Mahek: prompt iteration against real demo ASINs; corpus to 40+ docs; re-sync KB —
      **blocked on AWS account access**
- [x] `pytest` coverage: **132 passing, 1 skipped**, zero AWS account required to run any
      of it (`cd services/api && python -m pytest -q`)

## Phase 3 — Surfaces

- [ ] Ritvik: `apps/extension/` built from `apps/extension/README.md`'s brief — manifest,
      content script (DOM reader), background service worker (owns the fetch, not the
      content script — see the README for why), Shadow DOM pill + drawer per
      `docs/ui-ux-brief.md`
- [ ] Ritvik: API base URL wired to the deployed endpoint once Saket has one
- [ ] Extension tested unpacked on 5 real amazon.in product pages, including a variant
      switch and a non-food item
- [ ] Ritvik: swarm split driven by real `nutrition.macros`, result panel, demo cards,
      trending ticker wired to `GET /v1/trending`
- [ ] Amplify Hosting connected to `main` — **this URL is the submission URL**

## Phase 4 — Sleep

- [ ] Actually do this

## Phase 5 — Completion + polish

- [x] `handlers/grievance.py` implemented (moved up — see Phase 2)
- [x] `handlers/trending.py` implemented (moved up — see Phase 2)
- [ ] `handlers/ingest.py` implemented, `DailySync` schedule flipped to `Enabled: true`
      (still first on the cut list if time is short — see below)
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

(`handlers/grievance.py` and `handlers/trending.py` are already done, so they're off this
list — no longer a time trade-off.)

**Never cut:** the grounding guard, citations on every finding, the live web app URL.
