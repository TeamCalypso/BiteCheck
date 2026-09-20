#!/usr/bin/env python3
"""Convert an FSSAI FoSCoS food-recall Excel export into KB-ready Markdown records."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT / "data" / "sources" / "fssai" / "foscos_food_recall_export_2026-09-20.xlsx"
OUTPUT_DIR = ROOT / "data" / "corpus" / "fssai" / "recalls"

SOURCE_URL = "https://foscos.fssai.gov.in/food-recall"
SNAPSHOT_DATE = "2026-09-20"


def clean(value) -> str:
    """Return a safe display string while preserving source wording."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_]+", "-", text).strip("-")


def normalize_date(value) -> str:
    """Convert Excel dates to YYYY-MM-DD where possible."""
    if pd.isna(value):
        return ""

    parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)

    if pd.isna(parsed):
        return clean(value)

    return parsed.strftime("%Y-%m-%d")


def infer_category(product: str) -> str:
    """Conservatively map product descriptions to the contract categories."""
    text = product.lower()

    if any(word in text for word in [
        "chilli", "chillies", "masala", "spice", "pepper",
        "cumin", "coriander", "turmeric", "cardamom"
    ]):
        return "spices_blends"

    if any(word in text for word in [
        "wheat flour", "atta", "flour", "rice", "grain",
        "cereal", "pulse", "dal", "starch"
    ]):
        return "staples_grains"

    if any(word in text for word in [
        "biscuit", "cookie", "snack", "namkeen", "mixture",
        "chips", "cake", "bakery", "bread", "bun"
    ]):
        return "packaged_snacks"

    if any(word in text for word in [
        "ghee", "butter", "oil", "fat", "margarine"
    ]):
        return "oils_fats"

    if any(word in text for word in [
        "milk", "curd", "yogurt", "paneer", "cheese",
        "dairy"
    ]):
        return "dairy_perishable"

    if any(word in text for word in [
        "juice", "drink", "beverage", "water", "soft drink"
    ]):
        return "beverages"

    if any(word in text for word in [
        "protein", "supplement", "nutrition"
    ]):
        return "supplements_protein"

    return "other_food"


def build_markdown(row: pd.Series) -> str:
    recall_id = clean(row["Recall Id"])

    fields = [
        ("FBO Name", clean(row["FBO Name"])),
        ("Brand Name", clean(row["Brand Name"])),
        ("Batch / Lot No.", clean(row["Batch / Lot No."])),
        ("Product", clean(row["Product"])),
        ("Recall Start Date", normalize_date(row["Recall Start Date"])),
        ("Recall Status", clean(row["Recall Status"])),
        ("Recall Termination Date", normalize_date(row["Recall Termination Date"])),
        ("License / Registration No.", clean(row["License / Registration No."])),
        (
            "License Type",
            clean(row["License Type [Central/State/Registration]"]),
        ),
        ("Nature of Recall", clean(row["Nature of Recall"])),
    ]

    lines = [
        f"# FSSAI FoSCoS Food Recall — Recall ID {recall_id}",
        "",
        "## Recall Information",
        "",
    ]

    for label, value in fields:
        lines.append(f"- **{label}:** {value if value else 'Not provided in source record'}")

    lines.extend([
        "",
        "## Reason for Recall",
        "",
        clean(row["Reason for Recall"]) or "Not provided in source record",
        "",
        "## Source",
        "",
        f"- **Issuer:** FSSAI",
        f"- **System:** FoSCoS Food Recall",
        f"- **Recall ID:** {recall_id}",
        f"- **Export snapshot:** {SNAPSHOT_DATE}",
        f"- **Source URL:** {SOURCE_URL}",
        "",
        "> This record reproduces information from the FSSAI FoSCoS food-recall export. "
        "A recall record applies to the product/batch identified in the source record "
        "and should not be interpreted as a finding that every product from the brand is unsafe.",
        "",
    ])

    return "\n".join(lines)


def build_metadata(row: pd.Series) -> dict:
    recall_id = clean(row["Recall Id"])
    product = clean(row["Product"])
    brand = clean(row["Brand Name"])

    return {
        "issuer": "FSSAI",
        "docType": "recall",
        "category": infer_category(product),
        "brands": [brand] if brand else [],
        "hazards": [],
        "date": normalize_date(row["Recall Start Date"]),
        "orderRef": f"FoSCoS Recall ID {recall_id}",
        "sourceUrl": SOURCE_URL,
    }


def main() -> int:
    if not INPUT_FILE.exists():
        print(f"Input file not found: {INPUT_FILE}")
        return 1

    df = pd.read_excel(INPUT_FILE)

    required_columns = {
        "Recall Id",
        "FBO Name",
        "Brand Name",
        "Batch / Lot No.",
        "Product",
        "Reason for Recall",
        "Recall Start Date",
        "Recall Status",
        "Recall Termination Date",
        "License / Registration No.",
        "License Type [Central/State/Registration]",
        "Nature of Recall",
    }

    missing = required_columns - set(df.columns)

    if missing:
        print("Missing expected columns:")
        for column in sorted(missing):
            print(f"  - {column}")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    generated = 0
    skipped = 0
    seen_ids = set()

    for _, row in df.iterrows():
        recall_id = clean(row["Recall Id"])

        if not recall_id:
            skipped += 1
            continue

        if recall_id in seen_ids:
            print(f"WARNING: duplicate Recall ID {recall_id}; skipping duplicate")
            skipped += 1
            continue

        seen_ids.add(recall_id)

        slug = slugify(f"foscos-recall-{recall_id}")

        markdown_path = OUTPUT_DIR / f"{slug}.md"
        metadata_path = OUTPUT_DIR / f"{slug}.md.metadata.json"

        markdown_path.write_text(
            build_markdown(row),
            encoding="utf-8",
        )

        metadata_path.write_text(
            json.dumps(
                build_metadata(row),
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )

        generated += 1

    print(f"FoSCoS rows read: {len(df)}")
    print(f"Recall records generated: {generated}")
    print(f"Rows skipped: {skipped}")
    print(f"Output directory: {OUTPUT_DIR}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
