# BiteCheck — Project Protocol

## What this is

A food-safety layer over Indian e-commerce. A Chrome extension and a web app both call one
AWS backend that cross-references an Amazon.in product against a Bedrock Knowledge Base of
FSSAI / RASFF / FDA / CFS regulator documents, and returns a **grounded** verdict with exact
circular and order references.

Built for the WeMakeDevs x AWS **First Commit** hackathon (Sept 17-20, 2026), **Ship It** track.

## Team & ownership

| Lane | Owner | Directories |
|---|---|---|
| Backend, infra, deployment | Saket | `services/api/`, `infra/`, `scripts/`, `apps/extension/` |
| Knowledge base & AI | Mahek | `data/`, prompts in `services/api/src/bitecheck/core/` |
| Frontend | Ritvik | `apps/web/` |

**Stay in your lane's directories.** Cross-lane changes go through a PR so we do not
collide during the sprint.

## The contract is law

`contract/analyze.schema.json` is the single source of truth for the API response shape.
All three lanes code against it.

- Changing the schema is a **team decision**, announced before it is pushed.
- `services/api/src/bitecheck/models.py` mirrors it in Pydantic.
- `contract/fixtures/*.json` are valid examples; `services/api/tests/test_contract.py`
  asserts they validate. If you change the schema, update fixtures and models in the
  same commit.

## Non-negotiable engineering rules

1. **Never scrape amazon.in from Lambda.** Datacenter IPs get 503/CAPTCHA ~90% of the time.
   Product data comes from the extension's DOM read (browser-side) or from the URL slug +
   seeded catalog + Open Food Facts. This is an architectural constraint, not a preference.

2. **Never emit an ungrounded finding.** Every `findings[].citations[]` entry must trace to a
   chunk actually returned by Bedrock `Retrieve`. `core/grounding.py` enforces this by
   dropping anything unmatched. If everything drops, return `NO_DATA` — never invent a
   violation. We are making public claims about real food brands; a hallucinated recall is
   both a legal problem and an instant disqualification.

3. **No hardcoded demo responses.** Fixtures are for frontend development and tests only.
   The deployed path must run real RAG.

4. **Secrets never enter the repo.** Account IDs, KB IDs and endpoints live in
   `infra/kb-outputs.json` (gitignored) and SAM parameters.

## Conventions

- Backend: Python 3.12, arm64 Lambda, `boto3`, Pydantic v2. Business logic lives in `core/`
  and stays framework-free so it is unit-testable without AWS.
- `handlers/` are thin: parse event, call `core/`, shape response. No logic.
- `clients/` wrap external services so tests can mock them and retry/timeout config is in
  one place.
- Region is `us-east-1`. Vector store is S3 Vectors — **do not** switch to OpenSearch
  Serverless, it bills a ~$350/mo minimum.
- Model IDs are resolved at bootstrap and injected as env vars. Do not hardcode them.

## Commands

```bash
# backend tests
cd services/api && python -m pytest tests -q

# deploy the app stack
sam build -t infra/template.yaml && sam deploy -t infra/template.yaml

# one-time knowledge base bootstrap
python scripts/bootstrap_kb.py

# seed the demo catalog
python scripts/seed_dynamo.py

# tear everything down after judging
bash scripts/teardown.sh
```

## Progress tracking

`implementation_plan.md` in the repo root is the live step tracker. Tick steps off as they
land. It is the file to read first when picking work back up.
