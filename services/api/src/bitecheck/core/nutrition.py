"""Build the macros array that drives the web app particle swarm.

Three sources in priority order: the extension's scraped label, Open Food Facts, then the
curated catalog. Everything is normalized to per-100g.

The one invariant the frontend depends on: pct values sum to exactly 100. Real labels
never add up (water, ash, micronutrients, rounding), so an "other" bucket absorbs the
remainder. Without it the swarm cannot partition cleanly.

A second, less obvious invariant: `sugar` is nutritionally a *subset* of `carbohydrate`,
and `saturated_fat` is a subset of `fat`. If we sliced the swarm on raw label numbers,
sugar and saturated fat would be double-counted inside their parent macro. So before
slicing, we net the parent down by its child (see `build()`). This is why
`contract/fixtures/caution-protein.json`'s `carbohydrate: 12.0` is the *non-sugar* portion
of total carbs, not the label's raw "Total Carbohydrate" figure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Order the swarm renders clusters in.
MACRO_ORDER = ["protein", "carbohydrate", "sugar", "fat", "saturated_fat", "fiber", "sodium", "other"]

MACRO_CLASS = {
    "protein": "GOOD",
    "fiber": "GOOD",
    "carbohydrate": "NEUTRAL",
    "fat": "NEUTRAL",
    "sugar": "WATCH",
    "saturated_fat": "WATCH",
    "sodium": "WATCH",
    "other": "UNKNOWN",
}

_LABELS = {
    "protein": "Protein",
    "carbohydrate": "Carbs",
    "sugar": "Sugars",
    "fat": "Fat",
    "saturated_fat": "Saturated Fat",
    "fiber": "Fibre",
    "sodium": "Sodium",
}

# Checked in order - most specific first, so "Saturated Fat" matches saturated_fat and
# not fat, and "Total Sugars" matches sugar and not carbohydrate.
_ALIASES: list[tuple[str, tuple[str, ...]]] = [
    ("saturated_fat", ("saturated fat", "saturates", "sat fat", "sat. fat")),
    ("sugar", ("total sugars", "added sugars", "sugars", "sugar")),
    ("fat", ("total fat", "fat")),
    ("fiber", ("dietary fiber", "dietary fibre", "fibre", "fiber")),
    ("sodium", ("sodium",)),
    ("carbohydrate", ("total carbohydrate", "carbohydrates", "carbohydrate", "carbs")),
    ("protein", ("protein",)),
]

_VALUE_RE = re.compile(r"^([\d.]+)\s*([a-zA-Zµ]*)$")


@dataclass(frozen=True)
class Nutrition:
    basis: str
    confidence: str
    source: str
    macros: list[dict[str, Any]]
    flags: list[dict[str, str]]
    additives: list[dict[str, Any]]
    nova_group: int | None


def parse_label_value(raw: str | None) -> float | None:
    """Turn a label string like '24 g', '1.2mg', '<0.5 g', '1,200mg' into grams.

    Returns None for energy units (kcal/kJ - not a mass) or anything unparseable. The
    leading '<'/'~'/'≈' some labels use for trace amounts is stripped and the number taken
    as-is; treating "<0.5 g" as 0.5 g is a defensible upper-bound approximation for a
    safety-scanner context, not a lab measurement.
    """
    if not raw:
        return None
    s = raw.strip().lower().replace(",", "")
    s = s.lstrip("<~≈").strip()
    match = _VALUE_RE.match(s)
    if not match:
        return None

    value = float(match.group(1))
    unit = match.group(2)

    if unit in ("mg",):
        return value / 1000
    if unit in ("mcg", "µg", "ug"):
        return value / 1_000_000
    if unit in ("g", "gm", "gms", ""):
        return value
    if unit in ("kcal", "cal", "kj"):
        return None  # energy, not mass - callers must not treat this as a macro gram value
    return value  # unrecognised unit: best-effort, assume grams


def _extract_macro_key(name: str) -> str | None:
    n = (name or "").strip().lower()
    for key, aliases in _ALIASES:
        if any(alias in n for alias in aliases):
            return key
    return None


def _from_label_rows(label_rows: list[dict[str, Any]] | None) -> dict[str, float] | None:
    """Extension-scraped nutrition table -> {macro_key: grams_per_100g}."""
    if not label_rows:
        return None

    raw: dict[str, float] = {}
    for row in label_rows:
        key = _extract_macro_key(row.get("name", ""))
        if not key:
            continue
        value = parse_label_value(row.get("per100g"))
        if value is None:
            continue
        raw.setdefault(key, value)  # first (topmost) match for a key wins

    # Trust this source only if at least two of the three core macros were found - a
    # single stray row is more likely a mis-parsed selector than a real label.
    core_present = sum(k in raw for k in ("protein", "carbohydrate", "fat"))
    return raw if core_present >= 2 else None


def _from_off_payload(off_payload: dict[str, Any] | None) -> dict[str, float] | None:
    """Open Food Facts product object -> {macro_key: grams_per_100g}.

    Expects the already-unwrapped product dict (as clients.openfoodfacts.search()
    returns), i.e. payload["nutriments"], not the raw /api/v2/search response envelope.
    """
    if not off_payload:
        return None
    nutriments = off_payload.get("nutriments") or {}

    def g(key: str) -> float | None:
        value = nutriments.get(key)
        return float(value) if isinstance(value, (int, float)) else None

    raw: dict[str, float] = {}
    for macro_key, off_key in (
        ("protein", "proteins_100g"),
        ("carbohydrate", "carbohydrates_100g"),
        ("sugar", "sugars_100g"),
        ("fat", "fat_100g"),
        ("saturated_fat", "saturated-fat_100g"),
        ("fiber", "fiber_100g"),
    ):
        value = g(off_key)
        if value is not None:
            raw[macro_key] = value

    sodium = g("sodium_100g")
    if sodium is None:
        salt = g("salt_100g")  # OFF often only has salt; sodium = salt / 2.5
        if salt is not None:
            sodium = salt / 2.5
    if sodium is not None:
        raw["sodium"] = sodium

    return raw or None


def _from_catalog(catalog_nutrition: dict[str, Any] | None) -> dict[str, float] | None:
    """Curated bitecheck-catalog nutrition map -> {macro_key: grams_per_100g}."""
    if not catalog_nutrition:
        return None
    raw = {
        key: float(catalog_nutrition[key])
        for key in _LABELS
        if key in catalog_nutrition and catalog_nutrition[key] is not None
    }
    return raw or None


def _from_off_additives(off_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Additive tags from Open Food Facts, e.g. 'en:e951' -> {"ins": "E951", ...}.

    Risk defaults to "OK" for every additive - we do not yet have a curated INS risk
    table. TODO(mahek/saket): build a small table of commonly-flagged additives (sucralose,
    sodium benzoate, etc.) sourced from the FSSAI Food Additives Regulations already in the
    knowledge base, and look risk up from that instead of defaulting everything to OK.
    """
    if not off_payload:
        return []
    tags = off_payload.get("additives_tags") or []
    additives = []
    for tag in tags:
        code = tag.split(":")[-1].upper()
        additives.append({"ins": code if code.startswith("E") else None, "name": code, "risk": "OK"})
    return additives


def _derive_flags(raw: dict[str, float]) -> list[dict[str, str]]:
    """Heuristic label flags from UK FSA-style per-100g traffic-light thresholds.

    These are general nutrition heuristics, not FSSAI-sourced findings - they never touch
    `findings[]` or the grounding guard. They're informational flags on the nutrition
    panel only. A real `LABEL_CLAIM` finding still requires a retrieved, grounded citation.
    """
    flags = []
    sugar = raw.get("sugar")
    if sugar is not None and sugar >= 10:
        flags.append({
            "code": "ADDED_SUGAR_HIGH",
            "label": f"{sugar:.1f}g sugar per 100g — above the high-sugar threshold",
        })
    sodium = raw.get("sodium")
    if sodium is not None and sodium >= 0.6:
        flags.append({
            "code": "SODIUM_HIGH",
            "label": f"{sodium * 1000:.0f}mg sodium per 100g — above the high-sodium threshold",
        })
    sat_fat = raw.get("saturated_fat")
    if sat_fat is not None and sat_fat >= 5:
        flags.append({
            "code": "SATFAT_HIGH",
            "label": f"{sat_fat:.1f}g saturated fat per 100g — above the high-saturated-fat threshold",
        })
    return flags


def close_to_hundred(macros: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Append an 'other' bucket (or scale down) so every entry's pct sums to exactly 100.

    Each input dict needs at least {key, label, grams, class}; grams is assumed to already
    be a per-100g value, so it doubles as the pct value directly. Handles two failure
    modes real data hits: undershooting 100 (the common case - water/ash/micronutrients
    aren't tracked) via an 'other' bucket, and overshooting 100 (bad source data) via
    proportional scaling. Rounding drift is absorbed into the largest bucket so the sum is
    always exact, never off by float noise.
    """
    result = [dict(m) for m in macros]
    total = sum(m["grams"] for m in result)

    if total > 100.0:
        scale = 100.0 / total if total else 0.0
        for m in result:
            m["grams"] = round(m["grams"] * scale, 1)
        total = sum(m["grams"] for m in result)

    remainder = round(100.0 - total, 1)
    if remainder > 0.05:
        result.append(
            {"key": "other", "label": "Unspecified", "grams": remainder, "class": MACRO_CLASS["other"]}
        )

    for m in result:
        m["pct"] = round(m["grams"], 1)

    drift = round(100.0 - sum(m["pct"] for m in result), 2)
    if result and abs(drift) >= 0.01:
        biggest = max(result, key=lambda m: m["pct"])
        biggest["pct"] = round(biggest["pct"] + drift, 1)
        biggest["grams"] = biggest["pct"]

    return result


def build(
    label_rows: list[dict[str, Any]] | None,
    off_payload: dict[str, Any] | None,
    catalog_nutrition: dict[str, Any] | None,
) -> Nutrition | None:
    """Resolve nutrition from the best available source. None when nothing is available.

    Source priority: extension-scraped label (HIGH confidence) -> Open Food Facts (MEDIUM)
    -> curated catalog (MEDIUM). Never raises - a source that yields nothing just falls
    through to the next one, and the caller gets None rather than an exception when every
    source is empty (see handlers/analyze.py: a missing nutrition panel must not fail the
    whole request).
    """
    raw = _from_label_rows(label_rows)
    source, confidence = "amazon_label", "HIGH"

    if raw is None:
        raw = _from_off_payload(off_payload)
        source, confidence = "openfoodfacts", "MEDIUM"

    if raw is None:
        raw = _from_catalog(catalog_nutrition)
        source, confidence = "catalog", "MEDIUM"

    if not raw:
        return None

    # Net the parent macro down by its child so the swarm's slices are disjoint - see the
    # module docstring for why this matters.
    if "sugar" in raw and "carbohydrate" in raw:
        raw["carbohydrate"] = max(0.0, raw["carbohydrate"] - raw["sugar"])
    if "saturated_fat" in raw and "fat" in raw:
        raw["fat"] = max(0.0, raw["fat"] - raw["saturated_fat"])

    macros = [
        {"key": key, "label": _LABELS[key], "grams": round(raw[key], 2), "class": MACRO_CLASS[key]}
        for key in MACRO_ORDER
        if key in raw and key != "other" and raw[key] > 0
    ]
    macros = close_to_hundred(macros)

    nova_group = None
    if off_payload:
        ng = off_payload.get("nova_group")
        if isinstance(ng, int) and 1 <= ng <= 4:
            nova_group = ng

    return Nutrition(
        basis="per_100g",
        confidence=confidence,
        source=source,
        macros=macros,
        flags=_derive_flags(raw),
        additives=_from_off_additives(off_payload),
        nova_group=nova_group,
    )
