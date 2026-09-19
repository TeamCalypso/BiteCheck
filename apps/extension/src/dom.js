/**
 * Reads the extracted.* payload straight from the Amazon.in DOM, matching
 * contract/analyze.request.schema.json's `extracted` shape. This runs in the user's own
 * browser session with their own cookies/session - never server-side. See
 * services/api/src/bitecheck/core/resolver.py for why that split exists.
 *
 * Selectors are Amazon's current desktop layout (Sept 2026) and WILL drift. Keep every
 * selector behind a helper so a layout change is a one-line fix, not a rewrite.
 */

function text(selector) {
  const el = document.querySelector(selector);
  return el ? el.textContent.trim() : null;
}

export function getTitle() {
  return text("#productTitle");
}

export function getBrand() {
  const raw = text("#bylineInfo");
  if (!raw) return null;
  return raw
    .replace(/^Visit the /i, "")
    .replace(/ Store$/i, "")
    .replace(/^Brand:\s*/i, "")
    .trim();
}

export function getBullets() {
  return Array.from(document.querySelectorAll("#feature-bullets li span"))
    .map((el) => el.textContent.trim())
    .filter(Boolean);
}

export function getTechnicalDetails() {
  // Two possible tables on Amazon.in: #productDetails_techSpec_section_1 and
  // #detailBullets_feature_div. Merge both so FSSAI License / Net Quantity are found
  // wherever the listing put them.
  const details = {};

  document
    .querySelectorAll("#productDetails_techSpec_section_1 tr, #productDetails_detailBullets_sections1 tr")
    .forEach((row) => {
      const key = row.querySelector("th")?.textContent.trim();
      const value = row.querySelector("td")?.textContent.trim();
      if (key && value) details[key] = value;
    });

  document.querySelectorAll("#detailBullets_feature_div li").forEach((li) => {
    const parts = li.textContent.split(":");
    if (parts.length >= 2) {
      const key = parts[0].trim();
      const value = parts.slice(1).join(":").trim();
      if (key && value) details[key] = value;
    }
  });

  return details;
}

export function getIngredientsText() {
  // No single stable selector for ingredients across categories; check the common spots.
  return (
    text("#nic-ingredients-content") ||
    text("[data-feature-name='ingredients']") ||
    null
  );
}

export function getNutritionTable() {
  const rows = document.querySelectorAll(
    "#nutritional-information table tr, .nutrition-table tr"
  );
  if (!rows.length) return [];

  return Array.from(rows)
    .map((row) => {
      const cells = Array.from(row.querySelectorAll("td, th")).map((c) => c.textContent.trim());
      if (cells.length < 2 || !cells[0]) return null;
      return { name: cells[0], per100g: cells[1] || null, perServing: cells[2] || null };
    })
    .filter(Boolean);
}

export function getImageUrl() {
  return document.querySelector("#landingImage")?.src || null;
}

/** Assembles the full `extracted` payload for POST /v1/analyze. */
export function extractProductData() {
  return {
    title: getTitle(),
    brand: getBrand(),
    bullets: getBullets(),
    technicalDetails: getTechnicalDetails(),
    ingredientsText: getIngredientsText(),
    nutritionTable: getNutritionTable(),
    imageUrl: getImageUrl(),
  };
}

/** The buy-box anchor the pill/drawer get injected next to. Falls back gracefully. */
export function getBuyBoxAnchor() {
  return (
    document.querySelector("#desktop_buybox") ||
    document.querySelector("#rightCol") ||
    document.querySelector("#centerCol")
  );
}
