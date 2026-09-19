#!/usr/bin/env python3
"""Load data/seed/products.json into the bitecheck-catalog DynamoDB table.

This is enrichment data (curated FSSAI licence numbers, verified nutrition panels), not
verdicts - the analyze pipeline still runs live retrieval for every request. It exists so
the ~30 demo products resolve to a clean brand/product/category instantly instead of
depending on the normalizer guessing right every time during the live demo.

Usage:
    python scripts/seed_dynamo.py                  # seed bitecheck-catalog
    python scripts/seed_dynamo.py --dry-run         # validate products.json only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT / "data" / "seed" / "products.json"
TABLE_NAME = "bitecheck-catalog"
REQUIRED_FIELDS = ("asin", "brand", "name", "category")


def load_products() -> list[dict]:
    if not SEED_PATH.exists():
        raise FileNotFoundError(
            f"{SEED_PATH} not found. Create it with an array of product rows - "
            "see data/seed/README.md for the shape."
        )
    products = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    if not isinstance(products, list):
        raise ValueError("data/seed/products.json must be a JSON array")
    return products


def validate(products: list[dict]) -> list[str]:
    problems = []
    seen_asins: set[str] = set()
    for i, p in enumerate(products):
        for field_name in REQUIRED_FIELDS:
            if not p.get(field_name):
                problems.append(f"row {i}: missing required field '{field_name}'")
        asin = p.get("asin")
        if asin:
            if asin in seen_asins:
                problems.append(f"row {i}: duplicate asin {asin}")
            seen_asins.add(asin)
    return problems


def seed(products: list[dict], region: str = "us-east-1") -> int:
    """Batch-write products into the catalog table. Returns count written.

    TODO(saket): boto3.resource('dynamodb').Table(TABLE_NAME).batch_writer()
    """
    raise NotImplementedError


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="validate only, do not write")
    parser.add_argument("--region", default="us-east-1")
    args = parser.parse_args()

    try:
        products = load_products()
    except (FileNotFoundError, ValueError) as e:
        print(f"[seed_dynamo] {e}")
        return 1

    problems = validate(products)
    if problems:
        print(f"[seed_dynamo] {len(problems)} problem(s) in {SEED_PATH}:")
        for p in problems:
            print(f"  - {p}")
        return 1

    print(f"[seed_dynamo] {len(products)} product(s) validated OK.")
    if args.dry_run:
        return 0

    written = seed(products, region=args.region)
    print(f"[seed_dynamo] wrote {written} row(s) to {TABLE_NAME}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
