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
from decimal import Decimal
from pathlib import Path
from typing import Any

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


def _floats_to_decimal(value: Any) -> Any:
    """boto3's DynamoDB resource API rejects native Python floats outright (it requires
    Decimal for numeric types) - products.json's nutrition values (13.5, 41.2, ...) are
    plain JSON floats, so this converts them recursively before every write."""
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: _floats_to_decimal(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_floats_to_decimal(v) for v in value]
    return value


def seed(products: list[dict], region: str = "ap-south-1", table_name: str = TABLE_NAME) -> int:
    """Batch-write products into the catalog table. Returns count written.

    Only the fields the catalog schema actually uses are written (see
    docs/backend-schema.md's bitecheck-catalog section) - any extra keys in a seed row
    (like a human-only 'notes' field with commentary) are dropped rather than blindly
    written, so a typo'd key in products.json can't silently create schema drift.
    """
    table = boto3.resource("dynamodb", region_name=region).Table(table_name)
    written = 0
    with table.batch_writer() as batch:
        for product in products:
            item = {
                "asin": product["asin"],
                "brand": product["brand"],
                "name": product["name"],
                "category": product["category"],
            }
            for optional_key in ("netQuantity", "fssaiLicense", "nutrition", "notes"):
                if product.get(optional_key) is not None:
                    item[optional_key] = _floats_to_decimal(product[optional_key])
            batch.put_item(Item=item)
            written += 1
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="validate only, do not write")
    parser.add_argument("--region", default="ap-south-1")
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
