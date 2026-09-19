# App Flow

## Extension flow

```
User opens an amazon.in product page
        │
        ▼
content.js detects the ASIN in the URL (regex on location.pathname)
        │
        ▼
dom.js reads the page: title, brand, bullets, technical-details table
(FSSAI licence, net quantity), ingredients, nutrition table, image
        │
        ▼
content.js → chrome.runtime.sendMessage → background.js
        │  (service worker; not subject to the page's CSP, unlike content.js)
        ▼
background.js: POST /v1/analyze  { source: "extension", url, extracted }
        │
        ▼
        ... backend pipeline (see below) ...
        │
        ▼
background.js → sendResponse → content.js
        │
        ▼
ui.js renders the pill inside a Shadow DOM host, prepended into
#desktop_buybox (or #rightCol / #centerCol as fallbacks)
        │
        ▼
User clicks the pill → ui.js renders/toggles the slide-over drawer
        │
        ▼
Amazon variant switch (pushState, no reload)
        │
        ▼
content.js's patched history.pushState triggers runAnalysis() again
for the new ASIN; the pill is removed and re-rendered
```

## Web app flow

```
User pastes an amazon.in URL into the web app's input
        │
        ▼
Client-side: same ASIN regex as the extension (kept in sync manually -
see the TODO in core/resolver.py's docstring about sharing the pattern)
        │
        ▼
POST /v1/analyze  { source: "web", url }         (no `extracted`)
        │
        ▼
        ... backend pipeline (see below) ...
        │
        ▼
verdict.status === "NO_DATA" && product.isFoodProduct === false
        │                                   │
        │ yes                               │ no
        ▼                                   ▼
"Not a food product" state         swarm animation: idle cloud → scanning
(no swarm split)                    convergence → split into nutrition.macros
                                     clusters, sized by pct, colored by class
        │                                   │
        └───────────────┬───────────────────┘
                         ▼
        Result panel: verdict gauge, findings with citation
        chips, additives, alternatives, grievance button
```

## Backend pipeline (shared by both flows)

This is `handlers/analyze.py`, sequencing calls into `core/`:

```
1. resolve(url)                     → ASIN + slug title, or 400 if unresolvable
2. cache.get(asin)                  → hit + not expired? → cache.record_hit(); RETURN
3. ddb.get_catalog_entry(asin)      → curated attributes if seeded
4. normalizer.normalize(title, ...) → {brand, product, category, isFoodProduct}
                                     → isFoodProduct == false? → RETURN NO_DATA/notFood
5. nutrition.build(...)             → label → Open Food Facts → catalog → macros[]
6. rag.retrieve(query, category)    → ranked chunks + citation metadata
7. verdict.assess(product, chunks)  → draft {verdict, findings} (untrusted)
8. grounding.enforce(findings, chunks)
                                     → drop anything not traceable to a retrieved chunk
                                     → all findings dropped? → verdict forced to NO_DATA
9. cache.put(asin, response, ttl)   → RETURN
```

Steps 4–8 only run on a cache miss. Step 2's cache hit path is the one that makes the
"trending products load instantly" claim true — see `docs/backend-schema.md` for the
`TrendingIndex` GSI that `GET /v1/trending` reads from the same table.

## The batch-scope gap

FSSAI/RASFF/CFS recall notices are usually batch-specific; an Amazon listing has no batch
number a user can check before buying. `findings[].scope` records this explicitly
(`BATCH` vs `BRAND` vs `PRODUCT` vs `CATEGORY`), and the UI copy for a `BATCH`-scoped
finding tells the user to check the physical batch code on their own package rather than
implying every unit of that listing is affected. This is called out in `PRD.md` as a
stated limitation, not hidden in the UI.

## Grievance flow (stretch, Phase 5)

```
User clicks "Draft FoSCoS complaint" on a finding with severity CRITICAL or HIGH
        │
        ▼
POST /v1/grievance  { requestId }
        │
        ▼
handlers/grievance.py reads the cached analysis for that requestId,
calls Bedrock to draft complaint text citing the ASIN + the specific
violation reference(s)
        │
        ▼
Draft text returned to the UI. The user reviews and copies it manually -
BiteCheck never submits anything to FoSCoS on the user's behalf.
```
