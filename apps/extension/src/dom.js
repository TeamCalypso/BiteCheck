// BiteCheck DOM Extraction Helpers for Amazon.in
// Each selector is encapsulated in a dedicated helper function for resilience against Amazon layout shifts.

/**
 * Extracts 10-character Amazon ASIN from any amazon.in product URL
 * @param {string} [url=window.location.href]
 * @returns {string|null}
 */
export function extractAsin(url = window.location.href) {
  if (!url) return null;
  const match = url.match(/(?:\/dp\/|\/gp\/product\/|\/product\/|\/asin\/)([A-Z0-9]{10})/i);
  return match ? match[1].toUpperCase() : null;
}

/**
 * Extracts Product Title
 */
export function extractTitle() {
  const el =
    document.querySelector('#productTitle') ||
    document.querySelector('#title') ||
    document.querySelector('h1.product-title') ||
    document.querySelector('h1 span');
  return el ? el.textContent.trim() : null;
}

/**
 * Extracts Brand Name with common Amazon prefixes stripped
 */
export function extractBrand() {
  const el =
    document.querySelector('#bylineInfo') ||
    document.querySelector('#bylineInfo_feature_div a') ||
    document.querySelector('a#brand') ||
    document.querySelector('.po-brand .a-span9');

  if (!el) return null;
  let text = el.textContent.trim();

  // Strip Amazon byline wrappers
  text = text
    .replace(/^Visit the\s+/i, '')
    .replace(/\s+Store$/i, '')
    .replace(/^Brand:\s*/i, '')
    .replace(/^by\s+/i, '')
    .trim();

  return text || null;
}

/**
 * Extracts Feature Bullet Points
 */
export function extractBullets() {
  const bullets = [];
  const nodes = document.querySelectorAll(
    '#feature-bullets ul li span.a-list-item, #featurebullets_feature_div li span.a-list-item'
  );

  nodes.forEach((node) => {
    const text = node.textContent.trim();
    if (text && !text.toLowerCase().includes('report an issue with this product')) {
      bullets.push(text);
    }
  });

  return bullets;
}

/**
 * Extracts Technical Details and Specification Key-Value Pairs
 * e.g. "FSSAI License", "Net Quantity", "Manufacturer", "Ingredients"
 */
export function extractTechnicalDetails() {
  const details = {};

  // 1. Classic Table Sections
  const tableRows = document.querySelectorAll(
    '#productDetails_techSpec_section_1 tr, #productDetails_db_sections tr, #prodDetails tr'
  );
  tableRows.forEach((row) => {
    const th = row.querySelector('th, td.label');
    const td = row.querySelector('td:not(.label), td.value');
    if (th && td) {
      const key = th.textContent.trim().replace(/[\n\r\t]+/g, ' ');
      const val = td.textContent.trim().replace(/[\n\r\t]+/g, ' ');
      if (key && val) details[key] = val;
    }
  });

  // 2. Modern Detail Bullets
  const bulletItems = document.querySelectorAll('#detailBullets_feature_div ul li');
  bulletItems.forEach((li) => {
    const keyEl = li.querySelector('span.a-text-bold');
    if (keyEl) {
      const key = keyEl.textContent.replace(/[:\u200E\u200F]+/g, '').trim();
      const val = li.textContent.replace(keyEl.textContent, '').trim();
      if (key && val) details[key] = val;
    }
  });

  // 3. Overview Row Grid (div.po-row)
  const overviewRows = document.querySelectorAll('.po-row');
  overviewRows.forEach((row) => {
    const keyEl = row.querySelector('.a-span3');
    const valEl = row.querySelector('.a-span9');
    if (keyEl && valEl) {
      const key = keyEl.textContent.trim();
      const val = valEl.textContent.trim();
      if (key && val) details[key] = val;
    }
  });

  return details;
}

/**
 * Extracts Ingredients Text from Important Information sections or Technical Details
 */
export function extractIngredients() {
  // Check Important Information section
  const section =
    document.querySelector('#important-information') ||
    document.querySelector('div[data-feature-name="importantInformation"]') ||
    document.querySelector('#ingredients_feature_div');

  if (section) {
    const p = section.querySelector('p, div.a-section');
    if (p && p.textContent.trim()) {
      return p.textContent.trim();
    }
  }

  // Check technical details table
  const details = extractTechnicalDetails();
  for (const [k, v] of Object.entries(details)) {
    if (k.toLowerCase().includes('ingredient')) {
      return v;
    }
  }

  // Check bullets for explicit ingredient mentions
  const bullets = extractBullets();
  const ingBullet = bullets.find((b) => b.toLowerCase().startsWith('ingredients:'));
  if (ingBullet) {
    return ingBullet.replace(/^ingredients:\s*/i, '').trim();
  }

  return null;
}

/**
 * Extracts raw nutrition table rows if rendered on the page
 */
export function extractNutritionTable() {
  const rows = [];
  const tables = document.querySelectorAll(
    '#important-information table, #productDescription table, .a-bordered'
  );

  tables.forEach((tbl) => {
    const trs = tbl.querySelectorAll('tr');
    trs.forEach((tr) => {
      const tds = tr.querySelectorAll('td, th');
      if (tds.length >= 2) {
        const name = tds[0].textContent.trim();
        const per100g = tds[1] ? tds[1].textContent.trim() : null;
        const perServing = tds[2] ? tds[2].textContent.trim() : null;
        if (name && !name.toLowerCase().includes('nutrient') && !name.toLowerCase().includes('nutrition')) {
          rows.push({ name, per100g, perServing });
        }
      }
    });
  });

  return rows.length > 0 ? rows : null;
}

/**
 * Extracts main product image URL
 */
export function extractImageUrl() {
  const img =
    document.querySelector('#landingImage') ||
    document.querySelector('#imgTagWrapperId img') ||
    document.querySelector('#main-image');
  return img ? img.getAttribute('src') || img.currentSrc : null;
}

/**
 * Compiles full extracted DOM payload as required by contract/analyze.request.schema.json
 */
export function extractProductPayload() {
  return {
    title: extractTitle(),
    brand: extractBrand(),
    bullets: extractBullets(),
    technicalDetails: extractTechnicalDetails(),
    ingredientsText: extractIngredients(),
    nutritionTable: extractNutritionTable(),
    imageUrl: extractImageUrl(),
  };
}

/**
 * Finds optimal Buy Box anchor element for injecting the inline BiteCheck safety pill
 */
export function findBuyBoxAnchor() {
  return (
    document.querySelector('#desktop_buybox') ||
    document.querySelector('#buyBoxAccordion') ||
    document.querySelector('#buybox') ||
    document.querySelector('#rightCol') ||
    document.querySelector('#centerCol')
  );
}
