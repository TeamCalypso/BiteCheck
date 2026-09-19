#!/usr/bin/env python3
"""Normalize raw regulator/lab documents into data/corpus/: markdown + .metadata.json.

Input: data/sources/<issuer>/*.pdf (or .html) - gitignored, downloaded by hand or by a
per-source fetch helper. Output: data/corpus/<issuer>/<slug>.md plus a sidecar
<slug>.md.metadata.json with the fields Bedrock Knowledge Bases will index as filterable
metadata:

    { "issuer": "EU RASFF", "docType": "recall" | "alert" | "regulation" | "judgment",
      "category": "spices_blends" | ... (see contract/analyze.schema.json Category enum),
      "brands": ["Everest", ...], "hazards": ["ethylene_oxide", ...],
      "date": "2024-04-22", "sourceUrl": "https://...", "orderRef": "RASFF 2024.2893" }

Keep metadata lean: S3 Vectors caps attached metadata at 35 keys / 1KB per vector.

This is Mahek's primary tool - most of the actual work is picking good source documents
and filling in accurate metadata, not the code. The code just enforces a consistent shape
so every corpus document looks the same to the retriever.

Usage:
    python scripts/build_corpus.py                 # process everything under data/sources/
    python scripts/build_corpus.py --issuer fssai   # just one issuer subfolder
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES_DIR = ROOT / "data" / "sources"
CORPUS_DIR = ROOT / "data" / "corpus"

REQUIRED_METADATA_FIELDS = ("issuer", "docType", "category", "date")
VALID_DOC_TYPES = {"recall", "alert", "regulation", "judgment", "lab_report", "guideline"}


@dataclass
class CorpusDoc:
    issuer: str
    docType: str
    category: str
    date: str
    brands: list[str] = field(default_factory=list)
    hazards: list[str] = field(default_factory=list)
    orderRef: str | None = None
    sourceUrl: str | None = None


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_]+", "-", text).strip("-")


def validate_metadata(meta: dict, path: Path) -> list[str]:
    """Return a list of problems, empty if the sidecar is acceptable."""
    problems = []
    for field_name in REQUIRED_METADATA_FIELDS:
        if not meta.get(field_name):
            problems.append(f"{path.name}: missing required field '{field_name}'")
    if meta.get("docType") not in VALID_DOC_TYPES:
        problems.append(f"{path.name}: docType {meta.get('docType')!r} not in {VALID_DOC_TYPES}")
    if len(json.dumps(meta)) > 1024:
        problems.append(f"{path.name}: metadata exceeds the 1KB S3 Vectors filterable limit")
    return problems


def convert_one(source_path: Path, issuer_dir: str) -> Path | None:
    """Convert a single raw source file into normalized markdown.

    TODO(mahek/saket): PDF text extraction (pdfplumber or similar) + a pass through a
    cheap Bedrock model to clean up OCR noise and produce the markdown body. The
    .metadata.json sidecar is written by hand alongside each source for now - accuracy
    here matters more than automation for a corpus this size (40-60 docs).
    """
    raise NotImplementedError


def process_issuer(issuer_dir: Path) -> tuple[int, list[str]]:
    """Process every source file under one issuer directory. Returns (count, problems)."""
    count = 0
    problems: list[str] = []
    for meta_path in sorted(issuer_dir.glob("*.metadata.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        problems.extend(validate_metadata(meta, meta_path))
        count += 1
    return count, problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issuer", help="process only data/sources/<issuer>/")
    args = parser.parse_args()

    if not SOURCES_DIR.exists():
        print(f"[build_corpus] {SOURCES_DIR} does not exist yet - nothing to do.")
        return 0

    issuer_dirs = (
        [SOURCES_DIR / args.issuer] if args.issuer else sorted(p for p in SOURCES_DIR.iterdir() if p.is_dir())
    )

    total = 0
    all_problems: list[str] = []
    for issuer_dir in issuer_dirs:
        if not issuer_dir.is_dir():
            print(f"[build_corpus] skip {issuer_dir}, not a directory")
            continue
        count, problems = process_issuer(issuer_dir)
        total += count
        all_problems.extend(problems)
        print(f"[build_corpus] {issuer_dir.name}: {count} document(s) checked")

    if all_problems:
        print("\n[build_corpus] metadata problems:")
        for p in all_problems:
            print(f"  - {p}")

    print(f"\n[build_corpus] {total} document(s) total. Conversion (convert_one) is not yet "
          f"implemented - see TODO. Metadata validation ran regardless.")
    return 1 if all_problems else 0


if __name__ == "__main__":
    sys.exit(main())
