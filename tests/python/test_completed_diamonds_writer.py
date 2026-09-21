"""completed_diamonds: the reader existed, the writer and the schema did not.

FOURTH INSTANCE OF ONE CLASS (v0.230.0). `check_scale_occupancy.py` has read the
`completed_diamonds` key since it shipped, counting it toward "ever opened" at each
scale. No schema defined the key and no skill wrote it, so every occupancy report
counted zero completed cycles regardless of what had finished, and its "intake and
no outlet" finding could never be retired by finishing work. Siblings:
`progression_ruling` (2026-08-05), `last_progressed` (2026-09-20), and the
competitive gate in docs/errata.md.

These tests pin the loop shut at both ends: the reader still reads the key, the
schema defines it, the schema refuses an UNEVIDENCED completion, and the skill that
must write it says so.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCHEMA = REPO / "plugins/mycelium/schemas/diamonds/active.schema.json"
OCCUPANCY = REPO / "plugins/mycelium/scripts/check_scale_occupancy.py"
PROGRESS = REPO / "plugins/mycelium/skills/diamond-progress/SKILL.md"
RULES = REPO / "plugins/mycelium/engine/diamond-rules.md"


def _schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def test_reader_still_reads_the_key() -> None:
    """If the reader stops reading it, these tests are guarding nothing."""
    assert "completed_diamonds" in OCCUPANCY.read_text(encoding="utf-8")


def test_schema_defines_the_key_the_reader_reads() -> None:
    assert "completed_diamonds" in _schema()["properties"]


def test_a_writer_is_named_in_the_skill() -> None:
    """A schema with no writer is the same defect wearing a different hat."""
    text = PROGRESS.read_text(encoding="utf-8")
    assert "completed_diamonds" in text
    assert "dod_verdict" in text


def test_completed_is_no_longer_conflated_with_archived() -> None:
    """The root cause: one bucket held 'met its bar' and 'stopped'."""
    text = RULES.read_text(encoding="utf-8")
    assert "**completed**" in text
    # Scoped to the DEFINITION line, not the whole file: the old wording is quoted
    # on purpose in the note explaining why it changed, and a test that forbids the
    # phrase outright would forbid the repo from recording its own history.
    archived_def = [
        ln for ln in text.splitlines() if ln.lstrip().startswith("- **archived**:")
    ]
    assert archived_def, "archived state definition not found"
    assert "Completed" not in archived_def[0], archived_def[0]


@pytest.mark.parametrize(
    ("diamond", "valid"),
    [
        (
            {
                "completed_at": "2026-09-21",
                "dod_verdict": {
                    "signal_observed": "three strangers ran it unaided",
                    "verified_by": "touch log + two replies",
                },
            },
            True,
        ),
        # Completion asserted with no verdict at all — the shape that made
        # "completed" indistinguishable from "stopped".
        ({"completed_at": "2026-09-21"}, False),
        # A verdict that names no verification is an assertion, not evidence.
        (
            {
                "completed_at": "2026-09-21",
                "dod_verdict": {"signal_observed": "it shipped"},
            },
            False,
        ),
        # A timestamp is not a verdict.
        (
            {
                "dod_verdict": {
                    "signal_observed": "observed",
                    "verified_by": "self-assessed",
                },
            },
            False,
        ),
    ],
    ids=["evidenced", "no-verdict", "verdict-without-verification", "no-timestamp"],
)
def test_schema_requires_evidence_for_a_completion(diamond: dict, valid: bool) -> None:
    jsonschema = pytest.importorskip("jsonschema")

    base = {"id": "l4-x", "scale": "L4", "phase": "complete", "confidence": 0.8}
    # Validate the completed_diamond definition directly, so the test needs no
    # network resolution of the shared _common.schema.json $ref that the
    # top-level document carries (validate_canvas.py supplies that registry).
    schema = _schema()
    defn = dict(schema["$defs"]["completed_diamond"])
    defn["$defs"] = schema["$defs"]
    # Drop the $ref to the plain diamond: its own properties pull in _common.
    defn["allOf"] = [c for c in defn["allOf"] if "$ref" not in c]

    validator = jsonschema.Draft202012Validator(defn)
    errors = list(validator.iter_errors({**base, **diamond}))
    assert bool(not errors) is valid, [e.message for e in errors]
