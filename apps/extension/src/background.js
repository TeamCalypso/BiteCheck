// BiteCheck Chrome Extension Background Service Worker (Manifest V3)
// Performs out-of-band network calls to bypass host page Content-Security-Policy (CSP)

import { DEFAULT_API_URL } from './config.js';

/**
 * Retrieves configured backend API URL from chrome.storage
 */
async function getApiUrl() {
  try {
    const res = await chrome.storage.sync.get(['bitecheckApiUrl']);
    return res.bitecheckApiUrl || DEFAULT_API_URL;
  } catch (err) {
    return DEFAULT_API_URL;
  }
}

// NOTE: there used to be a createFallbackAnalysis() here that silently substituted
// fabricated data (a hardcoded "CLEAR" verdict claiming FSSAI/RASFF/FDA/CFS circulars had
// been cross-referenced, when they never were) whenever the real API failed. Removed - see
// handleAnalyzeProduct() below. Every claim BiteCheck shows must trace to something we
// actually checked; a confident-looking fake result is worse than an honest "couldn't
// reach the server, try again" error, especially for a real product a real user is
// looking at.

// Listen for messages from content script or popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'ANALYZE_PRODUCT') {
    handleAnalyzeProduct(message)
      .then((data) => sendResponse({ success: true, data }))
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true; // Keep message channel open for async response
  }

  if (message.type === 'DRAFT_GRIEVANCE') {
    handleDraftGrievance(message)
      .then((data) => sendResponse({ success: true, data }))
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true;
  }

  if (message.type === 'GET_API_URL') {
    getApiUrl().then((url) => sendResponse({ url }));
    return true;
  }

  if (message.type === 'SET_API_URL') {
    chrome.storage.sync.set({ bitecheckApiUrl: message.url }).then(() => {
      sendResponse({ success: true });
    });
    return true;
  }
});

/**
 * Executes POST /v1/analyze to backend, falling back gracefully on connection refusal
 */
async function handleAnalyzeProduct({ url, asin, extracted, forceRefresh }) {
  const apiUrl = await getApiUrl();
  const endpoint = `${apiUrl.replace(/\/$/, '')}/v1/analyze`;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);

    const res = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        source: 'extension',
        url: url,
        extracted: extracted,
        forceRefresh: Boolean(forceRefresh),
      }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (res.ok) {
      const json = await res.json();
      return json;
    } else {
      const errText = await res.text();
      console.warn(`[BiteCheck] API returned ${res.status}: ${errText}`);
      throw new Error('Could not reach the safety database. Please try again.');
    }
  } catch (networkErr) {
    console.warn(`[BiteCheck] Could not connect to API at ${endpoint} (${networkErr.message})`);
    // Let this propagate - the onMessage listener's .catch() turns it into
    // { success: false, error }, which content.js shows as an honest "couldn't check this
    // right now" state rather than a fabricated verdict about a real product.
    throw networkErr;
  }
}

/**
 * Handles FoSCoS grievance generation
 */
async function handleDraftGrievance({ requestId, product, findings }) {
  const apiUrl = await getApiUrl();
  const endpoint = `${apiUrl.replace(/\/$/, '')}/v1/grievance`;

  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ requestId }),
  });

  if (!res.ok) {
    // No template fallback here on purpose: a hardcoded "Finding: Regulatory
    // non-compliance" letter, generated when we never actually confirmed a violation,
    // is a real, formal-looking accusation a user could copy straight into FoSCoS against
    // a real company. That's worse than the analyze-path fallback, not just equivalent to
    // it - let this fail honestly and ask the user to retry.
    throw new Error('Could not draft the complaint right now. Please try again.');
  }

  return await res.json();
}
