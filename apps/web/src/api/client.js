/**
 * BiteCheck API Client
 * Connects the web frontend to the AWS HTTP API.
 */

import { ENDPOINTS } from '../config.js';

const ASIN_REGEX = /(?:dp|gp\/product|gp\/aw\/d|product)\/([A-Z0-9]{10})|[?&](?:asin|ASIN)=([A-Z0-9]{10})\b/i;

/**
 * Extracts a 10-character ASIN from an Amazon URL.
 */
export function extractAsin(url) {
  if (!url) return null;
  const match = url.match(ASIN_REGEX);
  return match ? (match[1] || match[2]).toUpperCase() : null;
}

/**
 * Validates whether the URL appears to be an Amazon link containing an ASIN.
 */
export function isValidAmazonUrl(url) {
  if (!url || typeof url !== 'string') return false;
  return Boolean(extractAsin(url));
}

/**
 * POST /v1/analyze
 * Executes food safety and grounding analysis for an Amazon product URL.
 */
export async function analyzeProduct(url, options = {}) {
  // A cache-miss analysis makes two sequential Gemini calls plus retrieval/grounding, and
  // has been measured live at 9-20s; the Lambda itself has a 25s budget. An 8s client-side
  // abort here doesn't mean the request failed - it means the backend was still working,
  // and it finishes and caches the result anyway (which is why a retry "just works": it's
  // a cache hit). 28s gives a small margin past the Lambda's own ceiling so a genuine
  // backend timeout surfaces as a real error instead of being masked by this firing first.
  const { forceRefresh = false, timeoutMs = 28000 } = options;

  // Live API Call with AbortController
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(ENDPOINTS.ANALYZE, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source: 'web',
        url,
        forceRefresh,
      }),
      signal: controller.signal,
    });

    clearTimeout(timer);

    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(errBody.message || `API returned HTTP ${res.status}`);
    }

    const data = await res.json();
    return { data, source: 'live' };
  } catch (err) {
    clearTimeout(timer);

    // Do NOT silently substitute fabricated data for a real answer here - this path runs
    // for any real product a user pastes, and returning a confident-looking fake verdict
    // (with a fake citation) undermines the whole "every claim is grounded" premise of the
    // project. Let the caller (interface.js's triggerAnalysis) handle this as a real error -
    // it already shows an honest "analysis failed, try again" state.
    console.warn('[BiteCheck API] Live endpoint unreachable:', err.message);
    throw new Error('Could not reach the safety database. Please try again in a moment.');
  }
}

/**
 * GET /v1/trending
 * Fetches recent high-traffic analyzed products.
 */
export async function fetchTrending() {
  try {
    const res = await fetch(ENDPOINTS.TRENDING, {
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    // Empty, not fabricated real-brand data with made-up scores - an empty ticker is
    // honest; a list of specific "CRITICAL"/"CAUTION" claims about real companies
    // (Everest, Optimum Nutrition) that were never actually checked is not.
    console.warn('[BiteCheck API] Trending endpoint unreachable:', err.message);
    return [];
  }
}

/**
 * POST /v1/grievance
 * Drafts a FoSCoS consumer grievance for an eligible product analysis.
 */
export async function draftGrievance(requestId) {
  try {
    const res = await fetch(ENDPOINTS.GRIEVANCE, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ requestId }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    // A fixed sample draft here would cite the wrong product entirely (a hardcoded
    // ASIN/brand, not whatever the user was actually looking at) - just as misleading as
    // the other fallbacks, and confusing on top of that. Let the caller show a real error.
    console.warn('[BiteCheck API] Grievance endpoint unreachable:', err.message);
    throw new Error('Could not draft the complaint right now. Please try again.');
  }
}
