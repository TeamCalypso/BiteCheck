# BiteCheck Chrome extension

Owner: **Ritvik**.

MV3 (Manifest V3) extension that activates on `amazon.in` product pages, shows an inline
safety pill under the buy box, and a slide-over drawer with the full findings/citations on
click.

## Contract

Build against `../../contract/analyze.request.schema.json` for what to send, and
`../../contract/analyze.schema.json` + `../../contract/fixtures/*.json` for what comes
back. `POST {API_BASE_URL}/v1/analyze` — the URL will be filled in once the backend is
deployed (Saket).

Request shape when `source: "extension"`:
```jsonc
{
  "source": "extension",
  "url": "<the current page's location.href>",
  "extracted": {
    "title": "...",           // #productTitle
    "brand": "...",           // #bylineInfo, strip "Visit the ... Store" / "Brand: "
    "bullets": ["..."],       // #feature-bullets li
    "technicalDetails": { "FSSAI License": "...", "Net Quantity": "..." },
    "ingredientsText": "...",
    "nutritionTable": [{ "name": "Protein", "per100g": "24 g" }],
    "imageUrl": "..."
  }
}
```

Selectors will drift as Amazon changes its layout — keep each one behind a small helper
function so a break is a one-line fix.

## Non-negotiable: Shadow DOM

Everything you render (the pill, the drawer) **must** live inside a Shadow DOM root
(`element.attachShadow({ mode: "open" })`). Amazon's global CSS will otherwise warp your
typography and buttons, and your styles can leak onto Amazon's own page. See
`../../docs/ui-ux-brief.md`'s Extension section for the full design brief (two-tier
pill + drawer pattern, color tokens, copy for each status).

## SPA navigation

Amazon swaps product variants via `history.pushState` without a full page reload — patch
`history.pushState` (and listen for `popstate`) so a stale result from the previous ASIN
gets torn down and a fresh analysis runs when the ASIN in the URL changes.

## Where the API call happens

Run the `fetch()` to the backend from the **background service worker**, not the content
script — a service worker isn't subject to the host page's Content-Security-Policy, so it
can reach an arbitrary API origin even on pages that lock that down; a content script
sometimes can't.

## Setup

Not yet scaffolded. `manifest.json` (permissions: `storage`, `webNavigation`;
`host_permissions`: `https://www.amazon.in/*`) plus a content script and a background
service worker is the minimum shape. Load unpacked via `chrome://extensions` → Developer
mode → Load unpacked → this directory, to test against a real amazon.in page as you go.

See `../../docs/app-flow.md` for the full extension flow sequence.
