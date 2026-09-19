# Seed catalog

`products.json` is a flat array of curated product rows loaded into `bitecheck-catalog` by
`scripts/seed_dynamo.py`. This is enrichment only — it makes the ~30 demo ASINs resolve to
a clean identity instantly. It never substitutes for live retrieval; verdicts always come
from `core/rag.py` + `core/verdict.py` against the knowledge base.

## Row shape

```jsonc
{
  "asin": "B0XXXXXXXX",
  "brand": "Everest",
  "name": "Garam Masala Powder",
  "category": "spices_blends",       // must match the Category enum in contract/analyze.schema.json
  "netQuantity": "100 g",
  "fssaiLicense": "10012345678901",
  "nutrition": {                      // optional, per-100g, used when the label/OFF path finds nothing
    "protein": 13.5, "carbohydrate": 41.2, "fat": 15.0, "fiber": 22.1, "sodium": 1.2
  },
  "notes": "Demo catalog entry for the Sept 20 submission."
}
```

## Building this list

Target ~30 rows covering the 4 demo states (critical / caution / clear / not-food) plus a
spread across the three category buckets from the corpus: spices/condiments, protein
supplements, and dairy/perishables. Real, purchasable Amazon.in ASINs — verify each one
resolves before the demo.
