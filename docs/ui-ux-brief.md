# UI/UX Design Brief

## Shared color semantics

Both surfaces use the same status → color mapping (also in
`apps/extension/src/config.js::STATUS_COLORS` and to be mirrored in the web app's theme):

| Status | Color | Hex |
|---|---|---|
| `CRITICAL` | red | `#DC2626` |
| `WARNING` | orange | `#EA580C` |
| `CAUTION` | amber | `#D97706` |
| `CLEAR` | green | `#059669` |
| `NO_DATA` | slate | `#64748B` |

**Accessibility floor**: never encode status by color alone. Every status badge pairs a
color with an icon (✓ / ⚠) and the status word itself (see `statusLabel()` in
`apps/extension/src/ui.js` for the extension's copy; match it in the web app).
`prefers-reduced-motion` skips the swarm split/scan transitions in favor of an instant
state change.

## Extension

Two tiers, deliberately — a dense inline badge plus an on-demand detail view, the pattern
used by Honey/Keepa/Grammarly-style extensions:

1. **Inline pill** — injected via Shadow DOM (`apps/extension/src/ui.js`) into the buy-box
   anchor (`#desktop_buybox`, falling back to `#rightCol`/`#centerCol`). Colored by status,
   short label ("Critical safety alert" / "Verified clean" / etc.), click target for the
   drawer. Kept small and native-looking rather than trying to look like an Amazon
   component — it should read as *ours*, not spoofed.
2. **Slide-over drawer** — `position: fixed; right: 0; width: 380px; z-index: 2147483647`,
   slides in on click. Contents: headline, plain-language summary, findings list (each with
   its citation, issuer, and date), disclaimer footer. All markup and styles live inside
   the same Shadow DOM as the pill (`STYLES` template literal in `ui.js`) so Amazon's
   global CSS cannot alter it and it cannot alter Amazon's page.

Shadow DOM is a hard requirement, not a nice-to-have — see `contract/README.md`-adjacent
reasoning in `docs/TRD.md`; skipping it was the single most common failure mode described
in the pre-build research (extensions clobbering host-page CSS and vice versa).

**SPA-navigation handling**: Amazon swaps product variants via `history.pushState` without
a full reload. `content.js` patches `history.pushState` and listens for `popstate` so a
stale pill from the previous ASIN is torn down (`removeExisting()`) and a fresh analysis
runs. Untested variant switches were called out explicitly as a manual QA step in the
implementation plan.

## Web app

Dark "inspection bay" aesthetic. Three states driven by a single `status` value:

1. **Idle** — ambient particle cloud (low-density, slow drift, mouse-reactive). URL input
   front and center. Three one-click demo cards below it, one per non-`CLEAR` /
   non-`CRITICAL` fixture family (`contract/fixtures/critical-spice.json`,
   `caution-protein.json`, `clear-turmeric.json`) so judges never have to hunt for a real
   ASIN mid-demo. A live advisories ticker fed by `GET /v1/trending`.
2. **Scanning** — particles converge toward a central point. This state exists specifically
   to cover the 3–5s cold-path latency (see `docs/TRD.md`'s latency budget) — it is a
   deliberate UX cover for real work happening, not decoration for its own sake, so keep
   it honest: it should end when the response actually arrives, not on a fixed timer.
3. **Result** — the swarm splits into one cluster per entry in `nutrition.macros[]`
   (`contract/analyze.schema.json`), cluster size proportional to `pct`, cluster color by
   `class` (`GOOD` / `NEUTRAL` / `WATCH` / `UNKNOWN`). Right-hand panel: verdict gauge
   (`verdict.score`, 0–100), findings list with expandable citation chips, additives,
   alternatives, and the grievance CTA when `grievance.eligible` is true.

`nutrition` can be `null` (see `contract/fixtures/not-food.json`) — the result state must
degrade to "no nutrition data" without the swarm attempting to render an empty split.

## What NOT to build

- Do not try to make the extension pill look like a native Amazon UI element (badge shape,
  exact Amazon typography). It should be visibly a third-party safety layer — that's a
  trust signal, not a weakness.
- Do not gate the web app's idle state behind a login or any account creation — the Ship
  It track submission URL must be reachable and testable by a signed-out judge.
