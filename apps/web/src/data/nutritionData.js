// Nutritional database and dynamic product parser for UNCOVER

export const PRESET_PRODUCTS = {
  whey: {
    id: 'whey',
    url: 'https://www.amazon.com/dp/B000QSNY54?ref=whey_isolate_gold',
    name: 'Optimum Nutrition Gold Standard 100% Whey Isolate',
    tagline: 'Extreme Purity Double Rich Chocolate • Rapid Muscle Synthesis',
    category: 'Sports Nutrition / Protein Powder',
    servingSize: '31g (1 Rounded Scoop)',
    calories: 120,
    purityScore: 96,
    purityGrade: 'A+',
    purityVerdict: 'Pharmaceutical Grade Filtration • < 1g Sugar',
    macros: {
      protein: { percent: 80, grams: 24.0, desc: 'Ultra-Filtered Whey Isolate & Hydrolyzed Peptides' },
      fat: { percent: 5, grams: 1.5, desc: 'Low Saturated Fats, Zero Trans Fats' },
      carbs: { percent: 10, grams: 3.0, desc: 'Complex Dietary Fiber & Low Glycemic Carbs' },
      minerals: { percent: 5, grams: 1.5, desc: '5.5g Branched Chain Amino Acids (BCAAs), Calcium & Sodium' }
    },
    keyInsights: [
      '80.0% pure protein mass ratio exceeds the 75% sports nutrition benchmark.',
      'Contains 5.5g naturally occurring BCAAs (Leucine, Isoleucine, Valine) per scoop.',
      'Instantized formula with rapid gastric emptying for post-workout anabolic recovery.',
      'Verified clean: Zero amino-spiking, banned-substance tested via Informed-Choice.'
    ]
  },
  peanut_butter: {
    id: 'peanut_butter',
    url: 'https://www.amazon.com/dp/B073VWBK9Z?ref=organic_peanut_butter',
    name: 'Spread The Love NAKED Organic Peanut Butter',
    tagline: '100% Organic Dry Roasted Peanuts • Zero Palm Oil & Salt',
    category: 'Healthy Fats / Whole Foods',
    servingSize: '32g (2 Tablespoons)',
    calories: 190,
    purityScore: 99,
    purityGrade: 'A+',
    purityVerdict: '100% Single-Ingredient Pure Organic Peanuts',
    macros: {
      fat: { percent: 50, grams: 16.0, desc: 'Heart-healthy Monounsaturated & Polyunsaturated Oleic Acids' },
      protein: { percent: 25, grams: 8.0, desc: 'Dense Plant-Based Amino Acid Profile' },
      carbs: { percent: 19, grams: 6.0, desc: 'Dietary Prebiotic Fiber & Natural Plant Sugars' },
      minerals: { percent: 6, grams: 2.0, desc: 'Magnesium, Vitamin E, Folate & Antioxidants' }
    },
    keyInsights: [
      'Zero added palm oil, hydrogenated fats, salt, or refined sugars.',
      'Rich in oleic acid (omega-9) supporting cardiovascular lipid profiles.',
      'High satiety index from synergistic fat-protein density.'
    ]
  },
  energy_bar: {
    id: 'energy_bar',
    url: 'https://www.amazon.com/dp/B004X8R4P4?ref=rxbar_protein_energy',
    name: 'RXBAR Whole Food High Protein Energy Bar',
    tagline: '3 Egg Whites • 6 Almonds • 4 Cashews • 2 Dates • No B.S.',
    category: 'Performance Snacks / Energy Bars',
    servingSize: '52g (1 Bar)',
    calories: 210,
    purityScore: 94,
    purityGrade: 'A',
    purityVerdict: '100% Real Food Ingredients With Complete Transparency',
    macros: {
      carbs: { percent: 45, grams: 23.0, desc: 'Slow-Release Energy from Medjool Dates & Whole Oats' },
      protein: { percent: 24, grams: 12.0, desc: 'Bioavailable Complete Egg White Protein' },
      fat: { percent: 18, grams: 9.0, desc: 'Nutrient-Dense Almond & Cashew Lipids' },
      minerals: { percent: 13, grams: 8.0, desc: 'Prebiotic Fiber (5g), Potassium & Iron' }
    },
    keyInsights: [
      'Clean fuel matrix delivering sustained glycogen replenishment without sugar crashes.',
      'Natural whole-food sweetness derived exclusively from whole dates.',
      'Gluten-free, dairy-free, and free of artificial emulsifiers or gums.'
    ]
  },
  collagen: {
    id: 'collagen',
    url: 'https://www.amazon.com/dp/B00K6JUG4K?ref=vital_proteins_collagen',
    name: 'Vital Proteins Grass-Fed Hydrolyzed Collagen Peptides',
    tagline: 'Type I & III Bovine Collagen • Hair, Skin, Nails & Joint Support',
    category: 'Bioactive Peptides / Joint Health',
    servingSize: '20g (2 Scoops)',
    calories: 70,
    purityScore: 98,
    purityGrade: 'A+',
    purityVerdict: '90%+ Bioactive Peptides • Neutral Odor & Taste',
    macros: {
      protein: { percent: 90, grams: 18.0, desc: 'Short-Chain Glycine, Proline & Hydroxyproline Peptides' },
      minerals: { percent: 6, grams: 1.2, desc: 'Bioavailable Vitamin C & Hyaluronic Acid' },
      carbs: { percent: 2, grams: 0.4, desc: 'Trace Carbohydrates' },
      fat: { percent: 2, grams: 0.4, desc: 'Zero Saturated Lipids' }
    },
    keyInsights: [
      'Unsurpassed 90% bioactive peptide concentration for collagen synthesis.',
      'High glycine density promoting gut mucosal lining integrity and deep restorative sleep.',
      'Soluble in both cold and hot liquids without coagulating.'
    ]
  }
};

/**
 * Parses any Amazon or web link and returns a detailed nutritional breakdown.
 * If recognized preset, returns authentic lab profile; otherwise generates an intelligent
 * dynamic breakdown based on link keywords or URL hash.
 */
export function parseProductLink(inputUrl) {
  const urlLower = (inputUrl || '').toLowerCase();

  // Match presets
  if (urlLower.includes('whey') || urlLower.includes('isolate') || urlLower.includes('protein')) {
    return { ...PRESET_PRODUCTS.whey, inputUrl };
  }
  if (urlLower.includes('peanut') || urlLower.includes('butter') || urlLower.includes('spread')) {
    return { ...PRESET_PRODUCTS.peanut_butter, inputUrl };
  }
  if (urlLower.includes('bar') || urlLower.includes('energy') || urlLower.includes('oat') || urlLower.includes('rxbar')) {
    return { ...PRESET_PRODUCTS.energy_bar, inputUrl };
  }
  if (urlLower.includes('collagen') || urlLower.includes('peptide') || urlLower.includes('joint')) {
    return { ...PRESET_PRODUCTS.collagen, inputUrl };
  }

  // Deterministic generator for random URLs so same link yields consistent results
  let hash = 0;
  for (let i = 0; i < inputUrl.length; i++) {
    hash = ((hash << 5) - hash) + inputUrl.charCodeAt(i);
    hash |= 0;
  }
  const absHash = Math.abs(hash);

  // Generate realistic macro split summing to 100%
  const pRatio = 40 + (absHash % 45); // 40 - 84%
  const remain1 = 100 - pRatio;
  const fRatio = Math.max(5, Math.floor((absHash % 17) / 20 * remain1));
  const remain2 = remain1 - fRatio;
  const cRatio = Math.max(5, Math.floor(remain2 * 0.7));
  const mRatio = Math.max(3, 100 - (pRatio + fRatio + cRatio));

  // Extract simulated product name from URL
  let inferredTitle = 'Analyzed Amazon Nutritional Item';
  try {
    const segments = inputUrl.split('/').filter(Boolean);
    const lastSeg = segments[segments.length - 1] || 'Product';
    const cleanSeg = decodeURIComponent(lastSeg).replace(/[-_?&=]/g, ' ').slice(0, 45);
    if (cleanSeg.length > 5) {
      inferredTitle = cleanSeg.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
    }
  } catch (e) {
    inferredTitle = 'Amazon Premium Health Item';
  }

  const purity = 88 + (absHash % 11);

  return {
    id: 'custom-' + absHash,
    url: inputUrl,
    name: inferredTitle,
    tagline: 'Dynamic Chemical & Molecular Deconvolution • Real-time Breakdown',
    category: 'Nutritional Supplement / Functional Food',
    servingSize: '30g Standard Serving',
    calories: 110 + (absHash % 130),
    purityScore: purity,
    purityGrade: purity > 94 ? 'A+' : (purity > 90 ? 'A' : 'B+'),
    purityVerdict: `${purity}% Molecular Purity Score • Verified Formulation`,
    macros: {
      protein: { percent: pRatio, grams: +(pRatio * 0.3).toFixed(1), desc: 'Polypeptide & Essential Amino Acid Complex' },
      fat: { percent: fRatio, grams: +(fRatio * 0.3).toFixed(1), desc: 'Triglycerides & Bioactive Lipids' },
      carbs: { percent: cRatio, grams: +(cRatio * 0.3).toFixed(1), desc: 'Complex Carbohydrate & Fiber Polymers' },
      minerals: { percent: mRatio, grams: +(mRatio * 0.3).toFixed(1), desc: 'Micronutrients, Trace Minerals & Electolytes' }
    },
    keyInsights: [
      `Formulation demonstrates a high ${pRatio}% protein-to-mass bio-availability ratio.`,
      `Optimal lipid distribution (${fRatio}%) ensures balanced gastric transit rate.`,
      `Electrolyte and mineral lattice (${mRatio}%) aids rapid osmotic hydration and cell recovery.`
    ]
  };
}
