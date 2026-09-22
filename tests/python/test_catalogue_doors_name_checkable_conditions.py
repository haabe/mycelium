"""A catalogue door's condition must be something the shipped tree can actually set.

WHY THIS EXISTS (v0.242.4). The L3 door read *"When a leaf is `selected`, offer to open an
L3 diamond on it"* — and **nothing in the plugin could set `selected`**:

  - `opportunities[].solutions[]` carries `minted_by`, `provenance`, `purpose_stance`,
    `shipped_at`. No status field.
  - The only status enum in that schema belongs to the OPPORTUNITY:
    open / closed / resolved / addressed / discarded.
  - A grep of every `.md`, `.yml` and `.json` under `plugins/mycelium/` found the word in
    three places, all describing the gate and none setting it.

**A door gated on a state with no writer is a door that never opens.** A consumer canvas
reported 53 solution records and no L3 diamond ever opened — reported by the framework's own
`check_scale_occupancy.py` as "the catalogue has an intake and no outlet at this scale",
which is the exact condition v0.217.0 added this door to fix.

Found by a full-ladder dogfood run, not by a check: `/ice-score` scored six solutions,
ranked one first, recommended it, and correctly declined to open anything — closing with
"`diamonds/active.yml` is not modified by this entry."

THIS TEST PINS THE PROPERTY, NOT THE WORDING: whatever a door's condition names, it must not
be a status value that no schema declares. That is checkable and it is what failed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[2] / "plugins" / "mycelium"
ICE = PLUGIN / "skills" / "ice-score" / "SKILL.md"
OST = PLUGIN / "skills" / "ost-builder" / "SKILL.md"
RULES = PLUGIN / "engine" / "diamond-rules.md"


def _declared_status_values() -> set[str]:
    """Every string in every enum across the canvas schemas."""
    out: set[str] = set()
    for f in (PLUGIN / "schemas" / "canvas").glob("*.json"):
        def walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k == "enum" and isinstance(v, list):
                        out.update(x for x in v if isinstance(x, str))
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(json.loads(f.read_text(encoding="utf-8")))
    return out


def test_schema_enums_were_found():
    """An empty set would make the assertions below pass by examining nothing."""
    values = _declared_status_values()
    assert len(values) > 20, f"only {len(values)} enum values found; the scan looks broken"
    assert "discarded" in values


@pytest.mark.parametrize("path", [ICE, OST, RULES], ids=lambda p: p.name)
def test_no_door_is_gated_on_an_undeclared_state(path):
    """THE LOAD-BEARING ASSERTION. A door sentence that gates on `a-state` in backticks
    must name a value some schema declares."""
    declared = _declared_status_values()
    text = path.read_text(encoding="utf-8")
    offenders = []
    for line in text.splitlines():
        if "offer" not in line.lower() and "offers" not in line.lower():
            continue
        if "diamond" not in line.lower():
            continue
        for m in re.finditer(r"When a leaf is `([a-z_]+)`|on a `?([a-z_]+)`? leaf", line):
            state = m.group(1) or m.group(2)
            if state and state not in declared and state not in {"scored", "selected-by-a-human"}:
                offenders.append(f"{path.name}: door gated on `{state}`, which no schema declares")
    assert not offenders, "\n".join(offenders) + (
        "\nA door gated on a state nothing writes never opens. Name a property the record "
        "actually carries, as /ost-builder does with 'scored and evidence-backed'."
    )


def test_the_l3_door_no_longer_names_the_phantom_state():
    """THE REGRESSION, pinned by name — and the phrase is allowed to APPEAR.

    The repaired text quotes the old wording to say what changed and why, which is the
    institutional memory of this defect. Forbidding the string outright would delete it, so
    the assertion is that no line uses it as a LIVE condition: every occurrence must sit on
    a line that also marks it as historical. Same rule the Hoskins drift guard applies for
    the same reason."""
    text = ICE.read_text(encoding="utf-8")
    live = [
        ln for ln in text.splitlines()
        if "When a leaf is `selected`" in ln
        and not re.search(r"Until v|changed|repaired|could not be met|no writer", ln)
    ]
    assert not live, f"the phantom condition is still stated as live: {live}"
    assert "highest-ranked" in text, "the replacement condition is missing"


def test_both_doors_state_the_decline_form():
    """The L2 door's shape includes recording a NO in one line. The L3 door now matches:
    an offer with no way to decline on the record is an offer that gets silently skipped."""
    assert "stays a record" in OST.read_text(encoding="utf-8")
    assert "stays a record" in ICE.read_text(encoding="utf-8")
