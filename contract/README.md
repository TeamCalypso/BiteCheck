# Contract

This directory is the boundary between the three lanes. Backend, web app and extension all
code against these files.

| File | What it is |
|---|---|
| `analyze.request.schema.json` | Request body for `POST /v1/analyze` |
| `analyze.schema.json` | Response body for `POST /v1/analyze` — **the** source of truth |
| `fixtures/*.json` | Valid example responses, one per UI state |

## Rules

1. **Changing the schema is a team decision.** Announce it before pushing. Everything
   downstream breaks silently otherwise.
2. A schema change, a fixture update and a `models.py` update land in the **same commit**.
3. `services/api/tests/test_contract.py` validates every fixture on every run. If it is red,
   nothing else matters.

## Fixtures use placeholder brands on purpose

The fixtures say "Demo Masala Co." and "Demo Nutrition", not real company names, and their
citation references end in `XXXX`.

That is deliberate. A fixture is committed, public, permanent text. Shipping a file that
asserts a named real company failed a pesticide test — when that text was written by us
rather than retrieved from a regulator document — would be an unverified public claim about
a real business, and it would sit in the repo whether or not the backend was running.

Real brand names and real order references appear **only** at runtime, only when
`core/grounding.py` has matched them to an actual retrieved chunk from the knowledge base.
That is the whole point of the grounding guard.

So: fixtures for shape, live RAG for substance. Never put a real accusation in a fixture.

## The four UI states

| Fixture | `verdict.status` | What the UI must show |
|---|---|---|
| `critical-spice.json` | `CRITICAL` | Red. Batch codes prominent, citations expandable, grievance button enabled |
| `caution-protein.json` | `CAUTION` | Amber. Claim mismatch called out against the nutrition panel |
| `clear-turmeric.json` | `CLEAR` | Green, `findings` empty. Note this one has `cached: true` and an 88 ms latency — exercise the cache badge with it |
| `not-food.json` | `NO_DATA` | Neutral. `nutrition` is `null`, so the swarm must handle a null gracefully |

There is a fifth state the fixtures do not cover because it has no distinct shape: a food
product where retrieval genuinely found nothing adverse *and* we are not confident, which
also returns `NO_DATA` but with `isFoodProduct: true`. Handle `NO_DATA` by checking
`product.isFoodProduct` to decide the wording.

## Notes for the frontend

- `nutrition.macros[].pct` sums to 100, always. The `other` entry absorbs the remainder, so
  the swarm can partition without special-casing.
- `nutrition` can be `null`. `verdict` and `findings` never are (`findings` may be `[]`).
- `findings[].citations` has `minItems: 1` — a finding without a source cannot exist, so you
  can render the citation chip unconditionally.
- `meta.findingsDropped` is the number of ungrounded claims the guard removed. Worth
  surfacing somewhere small; it is a good story during judging.
