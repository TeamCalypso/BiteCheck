// BiteCheck Extension Configuration & UI Tokens
// Shared color semantics specified in docs/ui-ux-brief.md

export const DEFAULT_API_URL = 'http://localhost:8000';

export const STATUS_COLORS = {
  CRITICAL: '#DC2626',
  WARNING: '#EA580C',
  CAUTION: '#D97706',
  CLEAR: '#059669',
  NO_DATA: '#64748B',
};

export const STATUS_LABELS = {
  CRITICAL: 'Critical Safety Alert',
  WARNING: 'Safety Warning',
  CAUTION: 'Caution Advised',
  CLEAR: 'Verified Clean',
  NO_DATA: 'Non-Food / No Records',
};

export const STATUS_ICONS = {
  CRITICAL: '⚠',
  WARNING: '⚠',
  CAUTION: '⚠',
  CLEAR: '✓',
  NO_DATA: 'ℹ',
};

export const SEVERITY_COLORS = {
  CRITICAL: '#DC2626',
  HIGH: '#EA580C',
  MEDIUM: '#D97706',
  INFO: '#38BDF8',
};

export const NOVA_DESCRIPTIONS = {
  1: { label: 'NOVA 1 — Unprocessed / Minimally Processed', desc: 'Natural whole foods without industrial formulations.' },
  2: { label: 'NOVA 2 — Processed Culinary Ingredients', desc: 'Oils, butter, sugar, and salt from natural sources.' },
  3: { label: 'NOVA 3 — Processed Food', desc: 'Manufactured with added salt, sugar, or culinary fats.' },
  4: { label: 'NOVA 4 — Ultra-Processed Food', desc: 'Industrial formulation with additives, preservatives, or emulsifiers.' },
};

// Fallback fixtures matching contract/fixtures/*.json for seamless offline demo testing
export const DEMO_FIXTURES = {
  'B0FIXTURE1': {
    requestId: '11111111-1111-4111-8111-111111111111',
    asin: 'B0FIXTURE1',
    cached: true,
    generatedAt: new Date().toISOString(),
    product: {
      brand: 'Heritage Spices',
      name: 'Garam Masala Blend, 100 g',
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
      summary: 'Regulators in two jurisdictions withdrew specific batches of this masala blend after detecting ethylene oxide, a pesticide not permitted on spices in the EU. Check the batch code on your pack against the list below before using it.',
    },
    findings: [
      {
        id: 'f1',
        severity: 'CRITICAL',
        type: 'CONTAMINANT',
        scope: 'BATCH',
        title: 'Ethylene oxide detected above the EU maximum residue limit',
        detail: 'A border-control sampling of this blend reported ethylene oxide at 0.24 mg/kg against an EU limit of 0.1 mg/kg. The notification covers the batch codes listed here; packs outside these batches were not part of the withdrawal.',
        batches: ['E24/09', 'E24/11'],
        citations: [
          {
            label: 'RASFF 2024.2893',
            issuer: 'EU RASFF',
            date: '2024-04-22',
            sourceUrl: 'https://webgate.ec.europa.eu/rasff-window/screen/notification/2024.2893',
            excerpt: 'ethylene oxide (0.24 mg/kg - ppm) in spice blend from India',
          },
        ],
      },
      {
        id: 'f2',
        severity: 'HIGH',
        type: 'RECALL',
        scope: 'BRAND',
        title: 'Voluntary withdrawal ordered by overseas food safety authority',
        detail: "The importing country's centre for food safety instructed distributors to stop sale and remove affected lots from shelves, citing the same contaminant.",
        batches: [],
        citations: [
          {
            label: 'CFS Food Alert FA-2024-04',
            issuer: 'CFS Hong Kong',
            date: '2024-04-05',
            sourceUrl: 'https://www.cfs.gov.hk/',
            excerpt: 'Centre for Food Safety instructs trade to suspend sale of spice products containing ethylene oxide',
          },
        ],
      },
    ],
    nutrition: {
      basis: 'per_100g',
      confidence: 'HIGH',
      source: 'amazon_label',
      novaGroup: 1,
      additives: [],
      macros: [
        { key: 'carbohydrate', label: 'Carbs', grams: 42.0, pct: 42.0, class: 'NEUTRAL' },
        { key: 'fiber', label: 'Fiber', grams: 26.0, pct: 26.0, class: 'GOOD' },
        { key: 'protein', label: 'Protein', grams: 11.0, pct: 11.0, class: 'GOOD' },
        { key: 'fat', label: 'Fat', grams: 14.0, pct: 14.0, class: 'NEUTRAL' },
        { key: 'other', label: 'Unspecified', grams: 7.0, pct: 7.0, class: 'UNKNOWN' },
      ],
    },
    alternatives: [
      {
        brand: 'Organic Tattva',
        name: 'Organic Garam Masala 100g',
        why: 'Zero recall circulars across all regulatory jurisdictions. Valid FSSAI licence with verified third-party laboratory panel testing.',
      },
    ],
    grievance: {
      eligible: true,
      reason: 'Recalled pesticide contaminant above legal maximum limits.',
    },
    disclaimer: 'Informational only, compiled from public regulator records. Not a laboratory result for the specific pack you are viewing. Always check the batch code printed on your package.',
  },

  'B0FIXTURE2': {
    requestId: '22222222-2222-4222-8222-222222222222',
    asin: 'B0FIXTURE2',
    cached: true,
    generatedAt: new Date().toISOString(),
    product: {
      brand: 'Optimum Nutrition',
      name: 'Gold Standard 100% Whey Protein Powder, 1 kg',
      category: 'supplements_protein',
      netQuantity: '1 kg',
      fssaiLicense: '10017011004123',
      isFoodProduct: true,
      imageUrl: null,
    },
    verdict: {
      status: 'CAUTION',
      score: 58,
      headline: 'Marketing claim mismatch: 30g claimed vs 24g actual label',
      summary: 'Promotional display states 30g protein per scoop, but the declared nutrition table indicates 24g per serving. Contains sucralose artificial sweetener. No hazardous pathogen or pesticide contamination found.',
    },
    findings: [
      {
        id: 'f1',
        severity: 'MEDIUM',
        type: 'LABEL_CLAIM',
        scope: 'PRODUCT',
        title: 'Advertised protein content exceeds declared nutrition panel',
        detail: 'Marketing copy states 30 g protein per 33 g scoop. The per-100g panel declares 72 g protein, which is about 24 g for that scoop. Claims regulations require advertised nutrient values to match the declared label.',
        batches: [],
        citations: [
          {
            label: 'FSSAI Advertising and Claims Regulations, 2018 - Reg. 6',
            issuer: 'FSSAI',
            date: '2018-11-19',
            sourceUrl: 'https://www.fssai.gov.in/',
            excerpt: 'No person shall make a claim which is inconsistent with the information declared on the label.',
          },
        ],
      },
    ],
    nutrition: {
      basis: 'per_100g',
      confidence: 'HIGH',
      source: 'amazon_label',
      novaGroup: 4,
      additives: [
        { name: 'Sucralose', ins: 'INS 955', risk: 'WATCH' },
        { name: 'Soy Lecithin', ins: 'INS 322', risk: 'OK' },
      ],
      macros: [
        { key: 'protein', label: 'Protein', grams: 72.0, pct: 72.0, class: 'GOOD' },
        { key: 'carbohydrate', label: 'Carbs', grams: 12.0, pct: 12.0, class: 'NEUTRAL' },
        { key: 'fat', label: 'Fat', grams: 6.0, pct: 6.0, class: 'NEUTRAL' },
        { key: 'other', label: 'Other', grams: 10.0, pct: 10.0, class: 'UNKNOWN' },
      ],
    },
    alternatives: [],
    grievance: {
      eligible: false,
      reason: 'No critical contaminant; labelling clarification required.',
    },
    disclaimer: 'Informational only, compiled from public regulator records. Not a laboratory result for the specific pack you are viewing. Always check the batch code printed on your package.',
  },

  'B0FIXTURE3': {
    requestId: '33333333-3333-4333-8333-333333333333',
    asin: 'B0FIXTURE3',
    cached: true,
    generatedAt: new Date().toISOString(),
    product: {
      brand: 'Pure Organics',
      name: 'Organic Turmeric Root Powder, 200 g',
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
      summary: 'We searched Indian and international recall, contamination and claims records covering this brand and category and found nothing adverse. The listing declares a valid FSSAI licence number and a complete nutrition panel. Absence of a record is not a guarantee of purity.',
    },
    findings: [],
    nutrition: {
      basis: 'per_100g',
      confidence: 'HIGH',
      source: 'amazon_label',
      novaGroup: 1,
      additives: [],
      macros: [
        { key: 'carbohydrate', label: 'Carbs', grams: 44.0, pct: 44.0, class: 'NEUTRAL' },
        { key: 'fiber', label: 'Fibre', grams: 21.0, pct: 21.0, class: 'GOOD' },
        { key: 'protein', label: 'Protein', grams: 9.7, pct: 9.7, class: 'GOOD' },
        { key: 'fat', label: 'Fat', grams: 9.9, pct: 9.9, class: 'NEUTRAL' },
        { key: 'other', label: 'Unspecified', grams: 15.4, pct: 15.4, class: 'UNKNOWN' },
      ],
    },
    alternatives: [],
    grievance: {
      eligible: false,
      reason: 'Clean regulatory record. No violation found.',
    },
    disclaimer: 'Informational only, compiled from public regulator records. Not a laboratory result for the specific pack you are viewing. Always check the batch code printed on your package.',
  },
};
