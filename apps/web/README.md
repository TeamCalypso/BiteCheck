# BiteCheck web app

Owner: **Ritvik**.

Stack: Vite + React + TypeScript + `@react-three/fiber` / `@react-three/drei` (three.js
particle swarm), per the approved plan.

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

## Setup

Not yet scaffolded — this file is a placeholder until Ritvik pushes the Vite project here
(`npm create vite@latest . -- --template react-ts` from this directory, or your preferred
equivalent). Once pushed, add the actual run/build commands to this README so `sam` /
Amplify deploy steps in `../../infra/` and CI can reference them.
