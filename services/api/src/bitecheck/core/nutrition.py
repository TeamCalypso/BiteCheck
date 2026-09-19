"""Build the macros array that drives the web app particle swarm.

Three sources in priority order: the extension's scraped label, Open Food Facts, then the
curated catalog. Everything is normalized to per-100g.

The one invariant the frontend depends on: pct values sum to exactly 100. Real labels
never add up (water, ash, micronutrients, rounding), so an "other" bucket absorbs the
remainder. Without it the swarm cannot partition cleanly.
"""

from __future__ import annotations

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
    """Turn a label string like '24 g', '1.2mg', '<0.5 g' into grams.

    TODO(saket): handle mg/mcg/kJ, ranges, and the '<' prefix.
    """
    raise NotImplementedError


def build(
    label_rows: list[dict[str, Any]] | None,
    off_payload: dict[str, Any] | None,
    catalog_nutrition: dict[str, Any] | None,
) -> Nutrition | None:
    """Resolve nutrition from the best available source. None when nothing is available.

    TODO(saket)
    """
    raise NotImplementedError


def close_to_hundred(macros: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Append or adjust the 'other' bucket so pct sums to 100.

    TODO(saket)
    """
    raise NotImplementedError
