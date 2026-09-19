/**
 * Bundled contract fixtures for 1-click testing and offline judging fallback.
 * Strictly mirrors contract/fixtures/*.json
 */

export const FIXTURES = {
  'critical-spice': {
    requestId: '11111111-1111-4111-8111-111111111111',
    asin: 'B0FIXTURE1',
    cached: false,
    generatedAt: '2026-09-20T04:11:00Z',
    product: {
      brand: 'Heritage Spices',
      name: 'Garam Masala Blend',
      category: 'spices_blends',
      netQuantity: '100 g',
      fssaiLicense: '10012345678901',
      isFoodProduct: true,
      imageUrl: null,
    },
    verdict: {
      status: 'CRITICAL',
      score: 18,
      headline: 'Batches of this blend were recalled overseas for ethylene oxide',
      summary:
        'Regulators in two jurisdictions withdrew specific batches of this masala blend after detecting ethylene oxide, a pesticide not permitted on spices in the EU. A separate sampling report found pesticide residue above the Indian permitted limit. Check the batch code on your pack against the list below before using it.',
    },
    findings: [
      {
        id: 'f1',
        severity: 'CRITICAL',
        type: 'CONTAMINANT',
        scope: 'BATCH',
        title: 'Ethylene oxide detected above the EU maximum residue limit',
        detail:
          'A border-control sampling of this blend reported ethylene oxide at 0.24 mg/kg against an EU limit of 0.1 mg/kg. The notification covers the batch codes listed here; packs outside these batches were not part of the withdrawal.',
        batches: ['E24/09', 'E24/11'],
        citations: [
          {
            label: 'RASFF 2024.XXXX',
            issuer: 'EU RASFF',
            date: '2024-04-22',
            sourceUrl: 'https://webgate.ec.europa.eu/rasff-window/screen/notification/XXXXXX',
            s3Uri: 's3://bitecheck-corpus/rasff/2024-XXXX.md',
            excerpt: 'ethylene oxide (0.24 mg/kg - ppm) in spice blend from India',
          },
        ],
      },
      {
        id: 'f2',
        severity: 'HIGH',
        type: 'RECALL',
        scope: 'BRAND',
        title: 'Voluntary withdrawal ordered by an overseas food safety authority',
        detail:
          "The importing country's centre for food safety instructed distributors to stop sale and remove affected lots from shelves, citing the same contaminant.",
        batches: [],
        citations: [
          {
            label: 'CFS Food Alert FA-XXXX',
            issuer: 'HK CFS',
            date: '2024-04-21',
            sourceUrl: 'https://www.cfs.gov.hk/english/unsafe_food_alert/',
            s3Uri: 's3://bitecheck-corpus/hkcfs/fa-XXXX.md',
            excerpt: 'The Centre for Food Safety today instructed the trade to stop sale of the affected batches.',
          },
        ],
      },
    ],
    nutrition: {
      basis: 'per_100g',
      confidence: 'MEDIUM',
      source: 'openfoodfacts',
      macros: [
        { key: 'carbohydrate', label: 'Carbs', grams: 41.2, pct: 41.2, class: 'NEUTRAL' },
        { key: 'fat', label: 'Fat', grams: 15.0, pct: 15.0, class: 'NEUTRAL' },
        { key: 'protein', label: 'Protein', grams: 13.5, pct: 13.5, class: 'GOOD' },
        { key: 'fiber', label: 'Fibre', grams: 22.1, pct: 22.1, class: 'GOOD' },
        { key: 'sodium', label: 'Sodium', grams: 1.2, pct: 1.2, class: 'WATCH' },
        { key: 'other', label: 'Unspecified', grams: 7.0, pct: 7.0, class: 'UNKNOWN' },
      ],
      flags: [
        { code: 'INCOMPLETE_LABEL', label: 'Listing image does not show a readable batch code or packing date' },
      ],
      additives: [],
      novaGroup: 3,
    },
    alternatives: [
      {
        brand: 'Demo Organics',
        name: 'Garam Masala (batch-tested)',
        why: 'Publishes per-batch pesticide residue reports and carries no adverse regulator records in our corpus.',
        asin: null,
      },
    ],
    grievance: { eligible: true, reason: null },
    meta: {
      latencyMs: 4120,
      chunksRetrieved: 8,
      findingsDropped: 1,
      modelId: 'fixture',
      nutritionSource: 'openfoodfacts',
    },
    disclaimer:
      'Informational only, compiled from public regulator records. Not a laboratory result for the specific pack you are viewing. Always check the batch code printed on your package.',
  },

  'caution-protein': {
    requestId: '22222222-2222-4222-8222-222222222222',
    asin: 'B0FIXTURE2',
    cached: false,
    generatedAt: '2026-09-20T04:14:00Z',
    product: {
      brand: 'Demo Nutrition',
      name: 'Whey Protein Concentrate, Chocolate, 1 kg',
      category: 'supplements_protein',
      netQuantity: '1 kg',
      fssaiLicense: null,
      isFoodProduct: true,
      imageUrl: null,
    },
    verdict: {
      status: 'CAUTION',
      score: 58,
      headline: 'Protein claim on the listing does not match the declared label',
      summary:
        'The listing advertises 30 g of protein per serving, but the nutrition panel works out to roughly 24 g for the same serving size. The category also carries an active regulatory advisory on unverified protein claims. No recall or contamination record was found for this brand.',
    },
    findings: [
      {
        id: 'f1',
        severity: 'MEDIUM',
        type: 'LABEL_CLAIM',
        scope: 'PRODUCT',
        title: 'Advertised protein content exceeds the declared nutrition panel',
        detail:
          'Marketing copy states 30 g protein per 33 g scoop. The per-100g panel declares 72 g protein, which is about 24 g for that scoop. Claims regulations require advertised nutrient values to match the declared label.',
        batches: [],
        citations: [
          {
            label: 'FSSAI Advertising and Claims Regulations, 2018 - Reg. 6',
            issuer: 'FSSAI',
            date: '2018-11-19',
            sourceUrl: 'https://www.fssai.gov.in/',
            s3Uri: 's3://bitecheck-corpus/fssai/advertising-claims-2018.md',
            excerpt: 'No person shall make a claim which is inconsistent with the information declared on the label.',
          },
        ],
      },
      {
        id: 'f2',
        severity: 'INFO',
        type: 'ADDITIVE',
        scope: 'PRODUCT',
        title: 'Contains a permitted but commonly flagged sweetener',
        detail:
          'The ingredient list includes sucralose (INS 955). It is permitted in this category, but products carrying it must declare it prominently. Listed here for transparency, not as a violation.',
        batches: [],
        citations: [
          {
            label: 'FSSAI Food Product Standards and Food Additives Regulations, 2011',
            issuer: 'FSSAI',
            date: '2011-08-01',
            sourceUrl: 'https://www.fssai.gov.in/',
            s3Uri: 's3://bitecheck-corpus/fssai/food-additives-2011.md',
            excerpt: 'INS 955 Sucralose - permitted with maximum limits as specified.',
          },
        ],
      },
    ],
    nutrition: {
      basis: 'per_100g',
      confidence: 'HIGH',
      source: 'amazon_label',
      macros: [
        { key: 'protein', label: 'Protein', grams: 72.0, pct: 72.0, class: 'GOOD' },
        { key: 'carbohydrate', label: 'Carbs', grams: 12.0, pct: 12.0, class: 'NEUTRAL' },
        { key: 'sugar', label: 'Sugars', grams: 4.5, pct: 4.5, class: 'WATCH' },
        { key: 'fat', label: 'Fat', grams: 6.0, pct: 6.0, class: 'NEUTRAL' },
        { key: 'sodium', label: 'Sodium', grams: 0.4, pct: 0.4, class: 'WATCH' },
        { key: 'other', label: 'Unspecified', grams: 5.1, pct: 5.1, class: 'UNKNOWN' },
      ],
      flags: [
        { code: 'CLAIM_MISMATCH', label: 'Advertised 30 g protein per serving; label implies about 24 g' },
      ],
      additives: [
        { ins: 'INS 955', name: 'Sucralose', risk: 'WATCH' },
        { ins: 'INS 322', name: 'Lecithin', risk: 'OK' },
      ],
      novaGroup: 4,
    },
    alternatives: [],
    grievance: {
      eligible: false,
      reason: 'No CRITICAL or HIGH finding. A labelling complaint can still be filed manually.',
    },
    meta: {
      latencyMs: 3860,
      chunksRetrieved: 6,
      findingsDropped: 0,
      modelId: 'fixture',
      nutritionSource: 'amazon_label',
    },
    disclaimer:
      'Informational only, compiled from public regulator records. Not a laboratory result for the specific pack you are viewing. Always check the batch code printed on your package.',
  },

  'clear-turmeric': {
    requestId: '33333333-3333-4333-8333-333333333333',
    asin: 'B0FIXTURE3',
    cached: true,
    generatedAt: '2026-09-20T04:16:00Z',
    product: {
      brand: 'Pure Organics',
      name: 'Organic Turmeric Powder, 200 g',
      category: 'spices_blends',
      netQuantity: '200 g',
      fssaiLicense: '10098765432109',
      isFoodProduct: true,
      imageUrl: null,
    },
    verdict: {
      status: 'CLEAR',
      score: 94,
      headline: 'No adverse regulator records found for this brand or product',
      summary:
        'We searched Indian and international recall, contamination and claims records covering this brand and category and found nothing adverse. The listing declares a valid FSSAI licence number and a complete nutrition panel. Absence of a record is not a guarantee of purity.',
    },
    findings: [],
    nutrition: {
      basis: 'per_100g',
      confidence: 'HIGH',
      source: 'amazon_label',
      macros: [
        { key: 'carbohydrate', label: 'Carbs', grams: 44.0, pct: 44.0, class: 'NEUTRAL' },
        { key: 'fiber', label: 'Fibre', grams: 21.0, pct: 21.0, class: 'GOOD' },
        { key: 'protein', label: 'Protein', grams: 9.7, pct: 9.7, class: 'GOOD' },
        { key: 'fat', label: 'Fat', grams: 9.9, pct: 9.9, class: 'NEUTRAL' },
        { key: 'other', label: 'Unspecified', grams: 15.4, pct: 15.4, class: 'UNKNOWN' },
      ],
      flags: [],
      additives: [],
      novaGroup: 1,
    },
    alternatives: [],
    grievance: { eligible: false, reason: 'No adverse finding to report.' },
    meta: {
      latencyMs: 88,
      chunksRetrieved: 7,
      findingsDropped: 0,
      modelId: 'fixture',
      nutritionSource: 'amazon_label',
    },
    disclaimer:
      'Informational only, compiled from public regulator records. Not a laboratory result for the specific pack you are viewing. Always check the batch code printed on your package.',
  },

  'not-food': {
    requestId: '44444444-4444-4444-8444-444444444444',
    asin: 'B0FIXTURE4',
    cached: false,
    generatedAt: '2026-09-20T04:18:00Z',
    product: {
      brand: 'Demo Electronics',
      name: 'Wireless Mouse, 2.4 GHz',
      category: 'non_food',
      netQuantity: null,
      fssaiLicense: null,
      isFoodProduct: false,
      imageUrl: null,
    },
    verdict: {
      status: 'NO_DATA',
      score: 100,
      headline: 'Not a food product',
      summary:
        'BiteCheck only analyses food, beverage and nutrition products regulated by FSSAI. This listing was classified as non-food, so no safety analysis was run.',
    },
    findings: [],
    nutrition: null,
    alternatives: [],
    grievance: { eligible: false, reason: 'Not a food product.' },
    meta: {
      latencyMs: 640,
      chunksRetrieved: 0,
      findingsDropped: 0,
      modelId: 'fixture',
      nutritionSource: null,
    },
    disclaimer:
      'Informational only, compiled from public regulator records. Not a laboratory result for the specific pack you are viewing. Always check the batch code printed on your package.',
  },
};

export const DEMO_PRESETS = [
  {
    key: 'critical-spice',
    label: 'Critical Alert: Garam Masala',
    tag: 'Ethylene Oxide Recall',
    status: 'CRITICAL',
    url: 'https://www.amazon.in/Demo-Garam-Masala-100g/dp/B0FIXTURE1',
  },
  {
    key: 'caution-protein',
    label: 'Caution: Whey Protein Isolate',
    tag: 'Label Claim Mismatch',
    status: 'CAUTION',
    url: 'https://www.amazon.in/Demo-Nutrition-Whey-Protein-1kg/dp/B0FIXTURE2',
  },
  {
    key: 'clear-turmeric',
    label: 'Clean: Organic Turmeric',
    tag: 'Verified Pure (No Records)',
    status: 'CLEAR',
    url: 'https://www.amazon.in/Demo-Organics-Turmeric-Powder/dp/B0FIXTURE3',
  },
  {
    key: 'not-food',
    label: 'Non-Food: Wireless Mouse',
    tag: 'Food Gate Filtered',
    status: 'NO_DATA',
    url: 'https://www.amazon.in/Demo-Wireless-Mouse/dp/B0FIXTURE4',
  },
];
