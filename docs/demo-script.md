# Demo Video Script (≤ 3 minutes)

Hackathon rule: YouTube, public or unlisted, **verified to open in a signed-out browser**
before submission. Do that check last, right before submitting — not just once early on.

## Beat sheet

| Time | Beat | Notes |
|---|---|---|
| 0:00–0:20 | The problem | FSSAI recalls exist but live in PDF circulars nobody reads; shoppers keep buying flagged SKUs. One sentence, one real circular screenshot. |
| 0:20–1:10 | Extension on a real amazon.in listing | Open a genuinely flagged product (from the seeded catalog), show the pill appear, click into the drawer, point at the exact order/circular reference number. This is the "wow" moment — do not rush it. |
| 1:10–1:50 | Web app swarm | Paste the same (or a different) link on the deployed Amplify URL. Idle → scanning → swarm splits by macro composition. Show a second product landing on `CLEAR` for contrast. |
| 1:50–2:10 | Grounding guard | Explicitly say what makes this trustworthy: every finding cites a real retrieved document; show `meta.findingsDropped` or the citation chip. This is the judging differentiator — say it out loud, don't just imply it. |
| 2:10–2:40 | AWS console tour | Bedrock Knowledge Base (S3 Vectors config visible), Lambda function list, DynamoDB cache table with real hit counts, API Gateway. Prove it's really deployed, not a local demo. |
| 2:40–3:00 | Close | Restate the impact in one sentence, show both URLs (Amplify web app + GitHub repo) on screen. |

## Pre-flight checklist (do this the day of recording, not the day before)

- [ ] Three bookmarked demo products confirmed live on amazon.in and still resolving
      correctly: one `CRITICAL`, one `CAUTION`, one `CLEAR`.
- [ ] Extension loaded unpacked and pill/drawer both render cleanly on a fresh Chrome
      profile (no other extensions interfering with the recording).
- [ ] Amplify URL loads from a machine that has never touched this AWS account (CORS,
      public reachability).
- [ ] `GET /v1/health` returns all config flags `true`.
- [ ] Repo is public.
- [ ] Screen recording software doesn't show personal bookmarks/tabs/notifications.

## What NOT to show

- Don't show a cold-start failure or a loading spinner that runs long — cut to a cached
  result if the live cold path is flaky on the day.
- Don't narrate the architecture diagram slide-by-slide; the AWS console tour proves it
  more convincingly than a slide does.
