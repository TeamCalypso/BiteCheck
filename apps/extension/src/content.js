/**
 * Content script: reads the product page DOM, asks the background worker to run the
 * analysis, and renders the result. Everything visual lives inside a Shadow DOM
 * (see ui.js) so Amazon's global CSS cannot leak in or be leaked on.
 *
 * Amazon is a partial SPA - switching a variant (size/flavor) does not reload the page,
 * so we also listen for history state changes and re-run on ASIN change.
 */

import { extractProductData } from "./dom.js";
import { renderPill, renderDrawer, removeExisting } from "./ui.js";

let lastAsin = null;

function currentAsin() {
  const match = location.pathname.match(/\/(?:dp|gp\/product)\/([A-Z0-9]{10})/i);
  return match ? match[1].toUpperCase() : null;
}

async function runAnalysis() {
  const asin = currentAsin();
  if (!asin || asin === lastAsin) return;
  lastAsin = asin;

  removeExisting();

  const payload = {
    source: "extension",
    url: location.href,
    extracted: extractProductData(),
  };

  // TODO(saket): chrome.runtime.sendMessage to background.js, which owns the fetch
  // (content scripts hitting a cross-origin API directly can be blocked by page CSP;
  // the service worker is not subject to the page's CSP).
  chrome.runtime.sendMessage({ type: "ANALYZE", payload }, (response) => {
    if (chrome.runtime.lastError || !response) {
      console.debug("[BiteCheck] analysis unavailable:", chrome.runtime.lastError);
      return;
    }
    if (response.error) {
      console.debug("[BiteCheck] analysis error:", response.error);
      return;
    }
    renderPill(response.data, () => renderDrawer(response.data));
  });
}

runAnalysis();

// Amazon updates the URL via history.pushState on variant switches without a full reload.
window.addEventListener("popstate", runAnalysis);
const originalPushState = history.pushState;
history.pushState = function (...args) {
  originalPushState.apply(this, args);
  runAnalysis();
};
