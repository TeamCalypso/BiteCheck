"""Pydantic models must accept every fixture. Catches models.py drifting from the schema."""

import json
from pathlib import Path

import pytest

from bitecheck.models import AnalyzeResponse

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = sorted((ROOT / "contract" / "fixtures").glob("*.json"))


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_fixture_parses_as_analyze_response(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    AnalyzeResponse.model_validate(data)
