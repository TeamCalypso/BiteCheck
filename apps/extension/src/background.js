/**
 * Service worker: owns the network call to the BiteCheck API. Kept separate from
 * content.js because a service worker is not subject to the host page's Content-Security-
 * Policy, so it can reach an arbitrary API origin even on pages that lock that down.
 */

import { ANALYZE_ENDPOINT } from "./config.js";

const inflight = new Map(); // asin -> Promise, dedupes rapid re-renders during a variant switch

async function analyze(payload) {
  const key = payload.url;
  if (inflight.has(key)) return inflight.get(key);

  const request = fetch(ANALYZE_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
    .then(async (res) => {
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      return res.json();
    })
    .finally(() => inflight.delete(key));

  inflight.set(key, request);
  return request;
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type !== "ANALYZE") return false;

  analyze(message.payload)
    .then((data) => sendResponse({ data }))
    .catch((error) => sendResponse({ error: error.message }));

  return true; // keep the message channel open for the async sendResponse
});
