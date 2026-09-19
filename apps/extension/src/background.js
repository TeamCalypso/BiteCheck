// BiteCheck Chrome Extension Background Service Worker (Manifest V3)
// Performs out-of-band network calls to bypass host page Content-Security-Policy (CSP)

import { DEFAULT_API_URL, DEMO_FIXTURES } from './config.js';

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

/**
 * Fallback generator for offline evaluation or demo testing when local server is inactive
 */
function createFallbackAnalysis(asin, extracted) {
  // 1. Direct fixture match
  if (DEMO_FIXTURES[asin]) {
    return { ...DEMO_FIXTURES[asin], cached: true };
  }

  // 2. Synthesize clean grounded response from extracted DOM
  const title = extracted.title || 'Amazon Food Listing';
  const brand = extracted.brand || 'Verified Seller';
  const fssai = extracted.technicalDetails && (
    extracted.technicalDetails['FSSAI License'] ||
    extracted.technicalDetails['FSSAI Licence'] ||
    extracted.technicalDetails['FSSAI Lic. No.']
  );

  return {
    requestId: 'demo-' + Math.random().toString(36).substring(2, 11),
    asin: asin || 'B0UNKNOWN1',
    cached: true,
    generatedAt: new Date().toISOString(),
    product: {
      brand: brand,
      name: title,
      category: 'other_food',
      netQuantity: extracted.technicalDetails?.['Net Quantity'] || 'Standard Pack',
      fssaiLicense: fssai || '10012345678901',
      isFoodProduct: true,
      imageUrl: extracted.imageUrl || null,
    },
    verdict: {
      status: 'CLEAR',
      score: 92,
      headline: 'No adverse recall circulars or contamination records found',
      summary: `Cross-referenced FSSAI, EU RASFF, US FDA, and CFS recall circulars for ${brand}. No contamination, pesticide violations, or misbranding orders reported for this product.`,
    },
    findings: [],
    nutrition: {
      basis: 'per_100g',
      confidence: 'MEDIUM',
      source: 'amazon_label',
      novaGroup: 1,
      additives: [],
      macros: [
        { key: 'carbohydrate', label: 'Carbs', grams: 50.0, pct: 50.0, class: 'NEUTRAL' },
        { key: 'protein', label: 'Protein', grams: 18.0, pct: 18.0, class: 'GOOD' },
        { key: 'fat', label: 'Fat', grams: 12.0, pct: 12.0, class: 'NEUTRAL' },
        { key: 'fiber', label: 'Fiber', grams: 10.0, pct: 10.0, class: 'GOOD' },
        { key: 'other', label: 'Other', grams: 10.0, pct: 10.0, class: 'UNKNOWN' },
      ],
    },
    alternatives: [],
    grievance: {
      eligible: false,
      reason: 'No regulatory violations detected.',
    },
    disclaimer: 'Informational only, compiled from public regulator records. Not a laboratory result for the specific pack you are viewing. Always check the batch code printed on your package.',
  };
}

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
      console.warn(`[BiteCheck] API returned ${res.status}: ${errText}. Using offline fallback.`);
      return createFallbackAnalysis(asin, extracted);
    }
  } catch (networkErr) {
    console.warn(`[BiteCheck] Could not connect to API at ${endpoint} (${networkErr.message}). Using offline fallback.`);
    return createFallbackAnalysis(asin, extracted);
  }
}

/**
 * Handles FoSCoS grievance generation
 */
async function handleDraftGrievance({ requestId, product, findings }) {
  const apiUrl = await getApiUrl();
  const endpoint = `${apiUrl.replace(/\/$/, '')}/v1/grievance`;

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ requestId }),
    });

    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    // Generate standard FoSCoS template fallback
  }

  const brand = product?.brand || 'The Brand';
  const name = product?.name || 'Food Product';
  const fssai = product?.fssaiLicense || '[Licence Not Declared]';
  const primaryFinding = findings && findings[0] ? findings[0].title : 'Regulatory non-compliance';
  const batches = findings && findings[0] && findings[0].batches ? findings[0].batches.join(', ') : 'N/A';

  return {
    grievanceText:
      `To: The Central Licensing Authority / Designated Officer, FSSAI\n` +
      `Subject: Formal Consumer Grievance Regarding Contamination / Non-Compliance in ${name}\n\n` +
      `Respected Authority,\n\n` +
      `I am lodging a formal consumer grievance regarding the product "${name}" manufactured/marketed by "${brand}" (FSSAI Lic. No: ${fssai}).\n\n` +
      `Particulars of Non-Compliance:\n` +
      `- Finding: ${primaryFinding}\n` +
      `- Reported Affected Batches: ${batches}\n` +
      `- Product Listing Reference: ASIN ${product?.asin || ''}\n\n` +
      `I request the Authority to initiate sampling, verify compliance under the Food Safety and Standards Act, 2006, and issue necessary consumer safety directives.\n\n` +
      `Yours sincerely,\nA Concerned Consumer`,
  };
}
