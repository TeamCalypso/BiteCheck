# BiteCheck web app

Owner: **Ritvik**.

Stack: Vite + vanilla JS + `three` (particle swarm) — as actually built. The original plan
called for React + TypeScript + `@react-three/fiber`; Ritvik built it directly on top of
`three` instead, which works fine and is a reasonable simplification.

## Contract

Build against `../../contract/analyze.schema.json` and the fixtures in
`../../contract/fixtures/*.json` — do not wait on the live API. `POST /v1/analyze` from
`services/api` will return exactly that shape once it's live; swap the fixture fetch for a
real `fetch(API_BASE_URL + "/v1/analyze", ...)` call at that point.

Key thing the swarm needs: `nutrition.macros[]` — `pct` values always sum to 100 (an
`other` bucket absorbs the remainder), so cluster sizing can be a direct proportional split
with no extra normalization on your end. `nutrition` itself can be `null` (see the
`not-food` fixture) — handle that before wiring up the split animation.

See `../../docs/ui-ux-brief.md` for the three states (idle / scanning / result), color
tokens, and the demo card flow, and `../../docs/app-flow.md` for how a paste-a-link
request maps onto the pipeline.

## Setup & Scripts

To install dependencies:
```bash
npm install
```

To run the local development server:
```bash
npm run dev
```

To build for production (Amplify / static hosting):
```bash
npm run build
```

To preview the production build:
```bash
npm run preview
```

