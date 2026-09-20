# BiteCheck — Technical Requirements Document

See the approved plan at the repo's `implementation_plan.md` for the phased build order.
This document is the durable technical reference; the implementation plan is the
disposable step tracker.

## Region & account

**`us-east-1`.** This flip-flopped twice during the build — worth recording the full story
since whoever picks this up next (including us, if the account situation changes) shouldn't
repeat the investigation:

1. **Started as `us-east-1`**, out of caution: at build time, Amazon S3 Vectors'
   availability in Mumbai was unconfirmed (initial research surfaced contradictory
   results), while `us-east-1` support was certain.
2. **Switched to `ap-south-1` (Mumbai)** after re-verifying against live AWS docs: S3
   Vectors is confirmed on AWS's current region list, and Claude models are reachable from
   `ap-south-1` via Global/APAC cross-region inference profiles. On paper, strictly better —
   lower latency for the actual (Indian) userbase, stronger "built for India" story.
3. **Switched back to `us-east-1`** after direct testing turned up a real, account-specific
   blocker documentation couldn't have shown us: `bedrock-runtime converse` and
   `invoke-model` both fail in `ap-south-1` for this AWS account with a generic
   `ValidationException: Operation not allowed` — reproduced via the CLI **and** the
   console's own model playground, and reproduced on a first-party Amazon model (Nova
   Micro, Titan Embeddings) as well as Claude, ruling out an Anthropic-specific cause.
   Confirmed **not** an IAM permissions issue (`iam simulate-principal-policy` explicitly
   returns `allowed` for `bedrock:InvokeModel`/`bedrock:Converse`) and **not** an
   Organizations SCP (the account isn't an Organizations member at all). The same exact
   call against `us-east-1` succeeds immediately. Best working theory: this account's
   "Free plan" credit program only provisions Bedrock in `us-east-1` — but that's inferred,
   not confirmed by AWS documentation, so **it's worth re-testing `ap-south-1` before
   assuming it's permanently unusable**, in case this was a temporary account-provisioning
   state rather than a hard limit.

Practical upshot: `scripts/bootstrap_kb.py`'s `VERDICT_MODEL_CANDIDATES` still tries a
`global.*` inference profile first (harmless to keep — it works from any source region),
then falls back to `us.*` profiles and bare model IDs, which is what actually resolves
successfully in `us-east-1` today.

Bedrock model access itself needed no separate request this round — AWS retired the manual
"Model access" approval page; serverless foundation models now activate automatically on
first invocation per-account. (First-time Anthropic use may still prompt for a short
use-case form somewhere in that flow; we didn't hit it, possibly because Claude 3 Haiku is
old enough not to require it.)

## Vector store: Amazon S3 Vectors, not OpenSearch Serverless

OpenSearch Serverless bills a hard minimum of ~2 OCU (~$350/month) regardless of usage.
Against a $200–$300 hackathon credit budget that is a real risk. S3 Vectors has no such
floor — cost scales with actual storage and query volume, which for a 40–60 document
corpus is cents. Trade-off accepted: S3 Vectors supports semantic search only (no hybrid
search) and caps attached metadata at 35 keys / 1KB per vector, both of which are fine
for this corpus size and query pattern.

## IaC: AWS SAM

`infra/template.yaml` owns everything redeployed repeatedly: the HTTP API, the five
Lambdas, and the two DynamoDB tables. The Bedrock Knowledge Base and its S3 Vectors index
are deliberately **not** in this template — they're bootstrapped once via
`scripts/bootstrap_kb.py` because KB creation and ingestion are slow, one-time operations
and we don't want them torn down and recreated on every `sam deploy` during active
development. Their IDs flow into the SAM stack as parameters
(`infra/samconfig.toml` → `parameter_overrides`).

## The scraping constraint (repeated because it drives multiple design decisions)

A Lambda function requesting `amazon.in` from a datacenter IP gets a 503 or a silent
CAPTCHA on the large majority of requests — this is a documented, structural anti-bot
posture, not a rate-limiting issue that retries or backoff would fix. Consequently:

- There is **no** `fetch_amazon_product()` anywhere in this codebase, and there must never
  be one added. If you're tempted to add server-side scraping, don't — it will work in
  local testing (residential IP) and fail in production (Lambda IP), which is the worst
  possible failure mode to discover during the live demo.
- The extension is the only high-fidelity data source, because it runs in the user's own
  browser with their own IP and session.
- The web app resolves products from `core/resolver.py` (URL slug parsing) plus
  `bitecheck-catalog` (curated) plus Open Food Facts (free, no key, decent India coverage).

## Pipeline stages and their owning modules

| Stage | Module | Notes |
|---|---|---|
| Resolve URL → ASIN/slug | `core/resolver.py` | pure functions, fully unit tested |
| Cache lookup/write | `core/cache.py`, `clients/ddb.py` | DynamoDB, 24h TTL, atomic hit counter |
| Catalog enrichment | `clients/ddb.py` | curated, never a substitute for live retrieval |
| Entity normalize + food gate | `core/normalizer.py` | Bedrock Converse, cheap model |
| Nutrition resolution | `core/nutrition.py`, `clients/openfoodfacts.py` | label → OFF → catalog, per-100g |
| Retrieval | `core/rag.py`, `clients/bedrock.py` | `bedrock-agent-runtime:Retrieve`, not RetrieveAndGenerate — see below |
| Verdict generation | `core/verdict.py` | Converse with strict JSON/tool schema |
| Grounding | `core/grounding.py` | drops any finding not traceable to a retrieved chunk |

### Why `Retrieve`, not `RetrieveAndGenerate`

`RetrieveAndGenerate` returns prose with its own citation structure that we don't control
and would have to re-parse to extract structured findings. `Retrieve` returns the raw
ranked chunks plus their S3 metadata directly. We then do generation ourselves with a
strict schema in `core/verdict.py`, and — critically — `core/grounding.py` can verify every
resulting claim against the exact chunk set that was retrieved, because we still have it.
This is the mechanism that makes the "zero hallucination" claim checkable rather than
aspirational.

## Model ID resolution

Never hardcoded. `scripts/bootstrap_kb.py::resolve_model_id()` queries the account's
available inference profiles/models at bootstrap time and writes the resolved IDs into
`infra/kb-outputs.json`, which feeds `samconfig.toml` parameters. Recent Claude models on
Bedrock require inference-profile addressing (`us.anthropic.*`) rather than a bare model
ID, and exactly which profiles are enabled varies by account and by when Bedrock model
access was granted — this must not be assumed at code-authoring time.

## Latency budget

Cold path target: 3–5s (normalize call + retrieve + verdict call, sequential — see
`handlers/analyze.py`). This sits comfortably under the HTTP API's 29-second integration
timeout with margin. The web app's scanning animation is timed to cover this window
rather than treating it as dead time to optimize away first.

Warm path (cache hit): <150ms, DynamoDB `GetItem` + a `hitCount` increment.

## Testing strategy

- `core/` modules are framework-free specifically so they can be unit tested with `pytest`
  and no AWS credentials (see `services/api/tests/`).
- `contract/fixtures/*.json` are validated against `contract/analyze.schema.json` on every
  test run (`test_contract.py`) and against the Pydantic models (`test_models.py`) — this
  is what keeps three people working in parallel from drifting apart.
- The grounding guard has dedicated tests (`test_grounding.py`) including the "empty
  retrieval drops everything" case, because that's the one that must never regress.
- Before the demo: manually run the analyze endpoint against an empty/wrong KB prefix and
  confirm every response degrades to `NO_DATA` rather than inventing a finding — this is
  the check that proves the safety property in production, not just in unit tests.

## Cost & teardown

Expected total under $10 for the build window (S3 Vectors: cents; Bedrock tokens: a few
dollars; Lambda/DynamoDB/API Gateway: within free tier; Amplify: free tier). `scripts/
teardown.sh` removes the Bedrock KB (with its `Delete` data policy so the vector index
goes with it), the corpus and vector S3 buckets, and runs `sam delete`. Run it after
judging — see the plan's cost & teardown section for the reasoning.
