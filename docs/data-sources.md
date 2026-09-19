# Knowledge Base Data Sources

Owner: **Mahek**. Target 40–60 documents. Every source in the corpus must appear as a row
here with real provenance — judges ask, and a citation that traces to nothing is worse
than no citation at all.

FSSAI alone under-covers this space (most of the highest-profile ETO/pesticide findings on
Indian spice brands were reported by *other* countries' regulators first). Pull from all of
these, not just FSSAI:

| Source | Why it's in the corpus | Status |
|---|---|---|
| FSSAI press releases, recall & alert notices | Primary Indian authority; the order reference numbers our findings ultimately point to | not started |
| EU RASFF Window (filter: origin India, hazard ETO/pesticides/aflatoxin) | Public, structured, and where most of the reported spice ETO alerts actually originate | not started |
| Hong Kong CFS food alerts | Broke the MDH/Everest ETO story that made this problem visible in India | not started |
| US FDA Import Alerts (99-08, 99-19) + recalls + India refusal reports | Public, brand-level and batch-level detail | not started |
| Singapore SFA recalls | Corroborating alerts on Indian-origin goods | not started |
| FSSAI Contaminants & Pesticide Residues Regulations (MRL tables) | Lets a finding say "2.4x the permitted limit" with an actual source, not a vibe | not started |
| FSSAI Advertising & Claims Regulations, 2018 | Backbone of the protein-powder / "no added sugar" claim-mismatch category | not started |
| FSSAI Labelling & Display Regulations, 2020 | Mandatory disclosure gap findings | not started |
| FSSAI Food Product Standards and Food Additives Regulations, 2011 | INS-code additive risk annotation | not started |
| CSE (Centre for Science and Environment) lab investigation reports | Independent Indian lab evidence, not government-sourced | not started |
| NCDRC / consumer court judgments | Adjudicated adulteration cases — `ADJUDICATION` finding type | not started |
| ICMR-NIN Dietary Guidelines, 2024 | Grounds nutrition commentary in an Indian reference standard, not a generic one | not started |

## Not in the knowledge base — runtime enrichment only

**Open Food Facts (India)** — `clients/openfoodfacts.py`. This is a live API call inside
the analyze pipeline (ingredients, additives, NOVA group, nutrition fallback), not a
document ingested into the vector store. Do not add OFF dumps to the corpus; it would
duplicate what the runtime client already provides and bloat the index with generic
product data that isn't a safety document.

## Per-document workflow

1. Download the raw circular/report into `data/sources/<issuer>/` (gitignored — these are
   often large PDFs and belong to their original publishers, not this repo).
2. Write the `.metadata.json` sidecar by hand — see the required fields in
   `docs/backend-schema.md`'s "Knowledge base document metadata shape" section. Accuracy
   here matters more than automation at this corpus size (40–60 documents); do not trust
   an LLM's first guess at `hazards` or `brands` without checking it against the source.
3. Run `python scripts/build_corpus.py --issuer <name>` to normalize into
   `data/corpus/<issuer>/` and validate the metadata (required fields present, size under
   the S3 Vectors 1KB filterable-metadata limit).
4. Update this table's `Status` column.
5. Once a batch of new documents lands, re-run the KB ingestion sync (either via
   `scripts/bootstrap_kb.py`'s ingestion trigger, or eventually `handlers/ingest.py` on its
   daily schedule once that's implemented in Phase 5).

## Provenance log

Add one row per document once sourced — this becomes the "judges ask, we have an answer"
artifact:

| Document | Issuer | Date | Source URL | Added by |
|---|---|---|---|---|
| Food Safety and Standards (Labelling and Display) Regulations, 2020 - Version VII | FSSAI | 2025-04-03 | https://fssai.gov.in/upload/uploadfiles/files/Comp_Labelling%20Display_Version%20VII_03042025.pdf | Mahek |
