#!/usr/bin/env python3
"""Build a single corpus_index.json from data/corpus/**/*.md + their .metadata.json
sidecars, and write it into the Lambda package (services/api/src/bitecheck/data/).

Why a bundled file instead of S3 or a real vector database: core/local_retrieval.py does
keyword/brand matching, not semantic search, so there's no embedding step to run - the
documents just need to be loadable. At ~250 short documents this file is a few hundred KB,
comfortably small enough to ship inside the Lambda deployment package directly (via the
existing CodeUri), which avoids an extra S3 round-trip on every cold start and avoids
standing up any new AWS resource for what is, at this corpus size, a solved problem without
one. See docs/TRD.md's "AI provider" section for why local retrieval exists at all
(Bedrock Knowledge Bases were the original plan; this is the pivot).

Re-run this and redeploy whenever data/corpus/ changes - the index is a build artifact,
not something the Lambda regenerates itself.

Usage:
    python scripts/build_corpus_index.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "data" / "corpus"
OUTPUT_PATH = ROOT / "services" / "api" / "src" / "bitecheck" / "data" / "corpus_index.json"

REQUIRED_METADATA_FIELDS = ("issuer", "docType", "category", "date")


def build() -> list[dict]:
    entries = []
    problems = []

    for md_path in sorted(CORPUS_DIR.rglob("*.md")):
        meta_path = md_path.with_suffix(md_path.suffix + ".metadata.json")
        if not meta_path.exists():
            problems.append(f"{md_path.relative_to(ROOT)}: no matching .metadata.json")
            continue

        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            problems.append(f"{meta_path.relative_to(ROOT)}: invalid JSON ({e})")
            continue

        missing = [f for f in REQUIRED_METADATA_FIELDS if not metadata.get(f)]
        if missing:
            problems.append(f"{meta_path.relative_to(ROOT)}: missing {missing}")
            continue

        text = md_path.read_text(encoding="utf-8")
        entries.append(
            {
                "id": str(md_path.relative_to(CORPUS_DIR)).replace("\\", "/"),
                "text": text,
                "issuer": metadata.get("issuer"),
                "docType": metadata.get("docType"),
                "category": metadata.get("category"),
                "date": metadata.get("date"),
                "brands": metadata.get("brands") or [],
                "hazards": metadata.get("hazards") or [],
                "orderRef": metadata.get("orderRef"),
                "sourceUrl": metadata.get("sourceUrl"),
            }
        )

    if problems:
        print(f"[build_corpus_index] {len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")

    return entries


def main() -> int:
    entries = build()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"[build_corpus_index] wrote {len(entries)} document(s), {size_kb:.1f} KB -> {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
