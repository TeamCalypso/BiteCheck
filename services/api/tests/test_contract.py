"""Every fixture must validate against the schema.

If this is red, the three lanes have drifted apart and nothing else matters. Keep it first
in the run order mentally, even if pytest does not order it that way.
"""

import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = ROOT / "contract"
FIXTURES = sorted((CONTRACT / "fixtures").glob("*.json"))


def _schema():
    return json.loads((CONTRACT / "analyze.schema.json").read_text(encoding="utf-8"))


def test_schema_itself_is_valid():
    jsonschema.Draft202012Validator.check_schema(_schema())


def test_request_schema_is_valid():
    schema = json.loads((CONTRACT / "analyze.request.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)


def test_fixtures_exist():
    assert FIXTURES, "no fixtures found - the frontend has nothing to build against"


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_fixture_validates(path):
    validator = jsonschema.Draft202012Validator(_schema())
    errors = sorted(validator.iter_errors(json.loads(path.read_text(encoding="utf-8"))),
                    key=lambda e: list(e.path))
    assert not errors, "\n".join(f"{list(e.path)}: {e.message}" for e in errors)


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_macro_percentages_sum_to_100(path):
    """The swarm partitions on pct. If it does not sum to 100 the visual is wrong."""
    data = json.loads(path.read_text(encoding="utf-8"))
    nutrition = data.get("nutrition")
    if nutrition is None:
        pytest.skip("no nutrition on this fixture")
    total = sum(m["pct"] for m in nutrition["macros"])
    assert abs(total - 100.0) < 0.05, f"macros sum to {total}, not 100"


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_every_finding_has_a_citation(path):
    """The grounding invariant, asserted at the contract level too."""
    data = json.loads(path.read_text(encoding="utf-8"))
    for finding in data["findings"]:
        assert finding["citations"], f"finding {finding['id']} has no citation"


def test_all_ui_states_are_covered():
    statuses = {
        json.loads(p.read_text(encoding="utf-8"))["verdict"]["status"] for p in FIXTURES
    }
    assert {"CRITICAL", "CAUTION", "CLEAR", "NO_DATA"} <= statuses
