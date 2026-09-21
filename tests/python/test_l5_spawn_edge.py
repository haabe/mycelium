"""The L4 -> L5 spawn edge, and the PMF block that gates it.

WHY (v0.232.0). Every rung of the ladder had a spawn rule except the top one. `diamond-rules.md`
listed L0->L1, L1->L2, L2->L3, L3->L4, L4->sub-L4 and L5->L2 — an EXIT from L5 and no ENTRY to it —
so an L5 diamond could only ever be created by hand, and the market scale sat unreachable by the
process that is supposed to reach it. `/launch-tier` was already making the categorisation that
should fire it (Lauchengco: "what does or doesn't get done flows from how releases are categorized")
and nothing acted on the result.

These tests pin the three halves that make the edge real rather than described: the rule exists, the
skill that fires it says so, and the schema types the entry condition so a band cannot be asserted
without a reading behind it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
RULES = REPO / "plugins/mycelium/engine/diamond-rules.md"
LAUNCH = REPO / "plugins/mycelium/skills/launch-tier/SKILL.md"
ASSESS = REPO / "plugins/mycelium/skills/diamond-assess/SKILL.md"
SCHEMA = REPO / "plugins/mycelium/schemas/diamonds/active.schema.json"


def _schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def test_the_ladder_has_an_entry_to_its_top_rung() -> None:
    text = RULES.read_text(encoding="utf-8")
    assert "L4 spawns L5" in text, "the missing edge is back"


def test_the_skill_that_categorises_is_the_one_that_spawns() -> None:
    """The trigger is the categorisation, not a date — so it must live where it is made."""
    text = LAUNCH.read_text(encoding="utf-8")
    assert "SPAWNS AN L5" in text
    assert "scale: L5" in text, "the skill must say what to write, not merely that to write"


def test_pmf_is_read_by_something() -> None:
    """A write-only entry condition is the defect class this release exists to stop repeating."""
    assert "pmf" in ASSESS.read_text(encoding="utf-8")


def test_diamond_carries_the_spawn_provenance_fields() -> None:
    props = _schema()["$defs"]["diamond"]["properties"]
    assert "pmf" in props
    assert "spawned_by" in props
    assert "spawn_trigger" in props


def test_not_yet_measurable_is_a_first_class_band() -> None:
    """Below a real sample a percentage is not a percentage. The honest answer must be sayable,
    or the schema itself pressures the author into inventing a number."""
    bands = _schema()["$defs"]["pmf"]["properties"]["band"]["enum"]
    assert "not-yet-measurable" in bands
    assert set(bands) == {
        "green",
        "tweak-product-or-language",
        "wrong-audience-or-underbuilt",
        "not-yet-measurable",
    }


def test_percentage_is_nullable_because_null_and_zero_are_different_claims() -> None:
    pct = _schema()["$defs"]["pmf"]["properties"]["very_disappointed_pct"]
    assert "null" in pct["type"], "writing 0 for 'we did not ask' is the error this prevents"


@pytest.mark.parametrize(
    ("pmf", "valid"),
    [
        ({"band": "not-yet-measurable", "n": 4, "very_disappointed_pct": None}, True),
        ({"band": "green", "n": 120, "very_disappointed_pct": 44}, True),
        # An invented band is how a gate gets cleared by vocabulary.
        ({"band": "strong-pmf", "very_disappointed_pct": 40}, False),
        # A percentage outside the possible range is a typo or a fabrication.
        ({"band": "green", "very_disappointed_pct": 140}, False),
        # The band is the one thing that must be stated.
        ({"n": 120, "very_disappointed_pct": 44}, False),
    ],
    ids=["honest-small-n", "real-reading", "invented-band", "impossible-pct", "no-band"],
)
def test_pmf_block_validation(pmf: dict, valid: bool) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = _schema()
    defn = dict(schema["$defs"]["pmf"])
    defn["$defs"] = schema["$defs"]
    errors = list(jsonschema.Draft202012Validator(defn).iter_errors(pmf))
    assert bool(not errors) is valid, [e.message for e in errors]


# --------------------------------------------- the substrate the trigger reads

GTM_SCHEMA = REPO / "plugins/mycelium/schemas/canvas/go-to-market.schema.json"
OCCUPANCY = REPO / "plugins/mycelium/scripts/check_scale_occupancy.py"


def _gtm() -> dict:
    return json.loads(GTM_SCHEMA.read_text(encoding="utf-8"))


def test_the_retired_scalar_now_fails_rather_than_being_quietly_accepted() -> None:
    """BREAKING, v0.233.0. Silently tolerating `launch_tier: 1` would leave the spawn reading a
    number nobody maintains — which is how the edge looked wired and fired never."""
    jsonschema = pytest.importorskip("jsonschema")
    field = _gtm()["properties"]["launch_tier"]
    v = jsonschema.Draft202012Validator(field)
    assert list(v.iter_errors(1)), "the old value must now be rejected"
    assert not list(v.iter_errors(None))


def test_band_label_is_free_text_because_the_vocabulary_is_the_teams() -> None:
    """Lauchengco: 'be it levels, grades, names, numbers, or tiers.' An enum here would
    re-impose the fixed table this release removes."""
    item = _gtm()["properties"]["releases"]["items"]
    assert item["properties"]["band_label"]["type"] == "string"
    assert "enum" not in item["properties"]["band_label"]


def test_one_machine_readable_bit_carries_the_trigger() -> None:
    item = _gtm()["properties"]["releases"]["items"]
    assert item["properties"]["is_major_launch"]["type"] == "boolean"
    assert "is_major_launch" in item["required"]


def test_the_detector_reads_the_spawn_backlink() -> None:
    """An unfired spawn has to be visible, or this whole edge is description again."""
    assert "spawned_l5" in OCCUPANCY.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("release", "valid"),
    [
        ({"id": "v1.0.0", "band_label": "Level 5 — category-defining", "is_major_launch": True}, True),
        ({"id": "v1.0.1", "band_label": "patch", "is_major_launch": False}, True),
        # No band recorded is the old failure: a release with no place on the scale.
        ({"id": "v1.0.2", "is_major_launch": True}, False),
        # The trigger bit is not optional.
        ({"id": "v1.0.3", "band_label": "big one"}, False),
    ],
    ids=["major", "minor", "no-band", "no-trigger-bit"],
)
def test_release_entry_validation(release: dict, valid: bool) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    item = _gtm()["properties"]["releases"]["items"]
    errors = list(jsonschema.Draft202012Validator(item).iter_errors(release))
    assert bool(not errors) is valid, [e.message for e in errors]
