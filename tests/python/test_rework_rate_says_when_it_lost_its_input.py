"""dora-check's rework rate reports null when its keyword method has lost its input (2026-10-20).

WHAT WAS WRONG. Part 2b computes `apex.ai_rework_rate` from commit subjects matching a fix pattern.
On the dogfood record it gave 6.2% on 2026-09-10 and 0.9% on 2026-10-20 after the subjects stopped
using "fix: ..." prefixes, while a hand reading found about three in four release subjects naming
something that was wrong. Nothing said the pattern had stopped matching; the number fell and read as
quality improving. The file-overlap alternative failed the other way (86.7% to 96.6%).

WHAT THIS PINS. Part 2b, under the rework field and before its output line, tells the agent to check
the input under a floor, to report null with "the method may have lost its input", and names the
opposite failure of the file-overlap criterion. The `demand_type` field it points to exists in the
cycle-history schema.
"""

from __future__ import annotations

import json
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2] / "plugins" / "mycelium"
SKILL = PLUGIN / "skills" / "dora-check" / "SKILL.md"


def _rework_block() -> str:
    text = SKILL.read_text(encoding="utf-8")
    start = text.index("**`apex.ai_rework_rate`**")
    return text[start:text.index("**`apex.ai_acceptance_rate`**", start)]


def test_the_rework_field_says_when_its_method_lost_its_input():
    block = _rework_block()
    assert "the method may have lost its input" in block
    assert "report `value: null`" in block
    assert block.index("lost its input") < block.index("- Output:")


def test_the_floor_and_the_opposite_failure_are_both_named():
    block = _rework_block()
    assert "under 2% of the window's commits" in block
    assert "measuring shared files, not rework" in block


def test_the_wording_free_record_it_points_to_exists():
    assert "cycle-history.yml#cycles[].demand_type" in _rework_block()
    schema = json.loads((PLUGIN / "schemas" / "canvas" / "cycle-history.schema.json")
                        .read_text(encoding="utf-8"))
    assert "demand_type" in json.dumps(schema)
