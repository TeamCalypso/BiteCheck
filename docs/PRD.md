# BiteCheck — Product Requirements Document

## Problem

FSSAI issues product bans, lab-test failures, and recall notices for adulterated spices,
unapproved protein powders, pesticide-heavy produce, and mislabeled baby food on an
ongoing basis. These advisories exist as PDF circulars scattered across regulator
websites. Consumers have no way to check them before buying, and quick-commerce/e-commerce
listings do not surface batch-level recall information — so people keep buying flagged
SKUs. Separately, D2C wellness brands (protein powders, "no added sugar" snacks) make
label claims that public lab tests frequently contradict.

## Who this is for

Shoppers on Amazon.in buying packaged food, spices, or nutrition/supplement products, who
have no practical way to check a product against scattered public safety records before
purchasing.

## Solution

A safety layer that sits between the shopper and the listing:

1. **Chrome extension** — reads the product page DOM the user already has open, sends it
   to our backend, and shows a grounded verdict inline plus a detailed drawer, all sourced
   from a Bedrock RAG knowledge base of FSSAI/RASFF/FDA/CFS documents.
2. **Web app** — the same analysis, reachable by pasting any Amazon.in product link,
   rendered as a three.js particle swarm that visually splits by nutritional composition.
   This is the project's public, testable URL.

## Goals (this submission)

- A working end-to-end pipeline: real Bedrock retrieval, real grounding, real DynamoDB
  cache — not a hardcoded demo.
- Zero hallucinated safety claims. Every finding traces to an actual retrieved document.
- A live, publicly reachable web app URL and a working unpacked extension, both driven by
  one deployed API.
- A visually distinctive web experience (the swarm) that makes the judging demo memorable.

## Non-goals (this submission)

- Batch-level tracking tied to a specific physical package the user is holding (FSSAI
  circulars are batch-specific; Amazon listings are not — see `app-flow.md` for how we
  handle this gap with `scope: BATCH` findings and a "check your batch code" prompt rather
  than pretending to know the user's exact pack).
- Submitting the FoSCoS grievance on the user's behalf — we draft it, the user files it.
- Coverage of platforms other than Amazon.in (Blinkit/Zepto/Instamart cited in the original
  brief are a stated future direction, not in scope for the hackathon build — no public,
  scrapable listing surface exists that doesn't hit the same anti-bot wall as Amazon).
- Real-time cold-chain/dark-store data (Concept described in the brainstorm phase but no
  public per-store feed exists to build against in this timeframe).

## Success criteria (Ship It track judging)

- Impact: a judge can paste a real, currently-listed Amazon.in spice/supplement link and
  get back a non-generic, citation-backed verdict within the 3-minute demo.
- AWS integration: Bedrock Knowledge Bases (S3 Vectors), Lambda, API Gateway, DynamoDB,
  Amplify Hosting are all visibly load-bearing, not decorative.
- Working execution over feature count: the analyze pipeline, grounding guard, and cache
  must all work reliably before any stretch feature (grievance drafting, alternatives) is
  attempted.

## Key user flows

See `app-flow.md` for the full sequence diagrams. In short:

- **Extension flow**: open a product page → pill appears under the buy box within ~5s
  (cold) or instantly (cached) → click → drawer with findings and citations.
- **Web flow**: paste a link → food-gate check → scanning animation → swarm splits by
  macro composition → findings panel with the same citations.

## Risks called out explicitly

- **No server-side Amazon scraping is possible** (datacenter IPs are blocked ~90% of the
  time). This is why the web flow resolves products from the URL slug plus a seeded
  catalog plus Open Food Facts, not a live fetch. See `TRD.md` and
  `services/api/src/bitecheck/core/resolver.py`.
- **Corpus coverage is inherently partial.** FSSAI circulars alone under-cover the space;
  the corpus pulls from RASFF, US FDA import alerts, and Hong Kong CFS as well (see
  `data-sources.md`). A `NO_DATA` result is an honest "we found nothing," never a false
  "verified clean" — `verdict.score` for `NO_DATA` should not be read as a purity
  guarantee, and the UI copy says so.
