"""No shipped instruction may teach the fabricated fourth Hoskins element.

WHY THIS EXISTS (2026-09-22). Hoskins's scenario model has THREE elements — Motivation,
Persona, Simulation. An earlier in-repo model added a fourth, "Means", which is not his;
"how they interact" folds into the Simulation. That was corrected on 2026-07-01 in
`schemas/canvas/scenarios.schema.json` and in `canvas-health` step 8b.

**The correction fixed the CHECKING surfaces and left the TEACHING surfaces alone, for
nearly three months.** Three files still instructed an agent to build the fabricated
model:

    skills/ost-builder/SKILL.md:71        "Use Hoskins' four elements: ... Means ..."
    domains/discovery/CLAUDE.md:99        "Scenarios have four elements: ... Means ..."
    skills/user-interview/SKILL.md:146    "(if four elements present)"

FOUND BY A CONSUMER RUN, NOT BY A CHECK. A dogfood full-ladder agent building
`scenarios.yml` hit the contradiction, reported that "the `ost-builder` skill's own
loaded instructions still describe the stale four-element version", and resolved it
correctly by treating the schema as authoritative. It should not have had to: a schema
is consulted, an instruction is followed, and the two disagreed.

THE LEGITIMATE MENTIONS ARE THE POINT OF THE EXEMPTION LIST BELOW. The schema keeps a
`means` field so historical instances still validate, and the changelog records the
correction. Both must keep saying "Means" — a check that forced them to stop would
delete the institutional memory of why this rule exists.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"

#: Phrasing that asserts the fabricated model. Narrow on purpose: it must not fire on
#: prose that NAMES the error in order to correct it, which is most of the surviving
#: legitimate mentions.
FOUR_ELEMENT = re.compile(r"four\s+elements", re.IGNORECASE)

#: A line is exempt when it is correcting the model rather than teaching it.
CORRECTING = re.compile(
    r"fabricat|corrected|legacy|NOT a Hoskins|historical|earlier in-repo|folds? into",
    re.IGNORECASE,
)


def _shipped_files() -> list[Path]:
    return [
        p for p in PLUGIN.rglob("*")
        if p.is_file()
        and p.suffix in (".md", ".yml", ".yaml", ".json")
        and "__pycache__" not in str(p)
    ]


def test_there_are_files_to_scan():
    """An empty scan would pass by examining nothing."""
    files = _shipped_files()
    assert len(files) > 50, f"only {len(files)} shipped files found; scan looks broken"


def test_no_shipped_instruction_teaches_a_four_element_hoskins_model():
    """THE LOAD-BEARING ASSERTION, and it scans the whole plugin rather than the three
    known files — the 2026-07-01 correction missed three surfaces precisely because it
    fixed the ones someone thought of."""
    offenders = []
    for path in _shipped_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), 1):
            # The scenario/Hoskins context term is part of the condition, not a nested
            # guard: "four elements" is ordinary English and may describe something else
            # entirely, so a match outside that context is not a finding.
            if (FOUR_ELEMENT.search(line)
                    and not CORRECTING.search(line)
                    and re.search(r"hoskins|scenario", line, re.IGNORECASE)):
                offenders.append(f"{path.relative_to(PLUGIN)}:{lineno}: {line.strip()[:120]}")
    assert not offenders, (
        "shipped instructions teach the fabricated fourth Hoskins element:\n  "
        + "\n  ".join(offenders)
        + "\nHoskins has THREE elements: Motivation, Persona, Simulation. 'Means' folds "
          "into the Simulation. See schemas/canvas/scenarios.schema.json."
    )


@pytest.mark.parametrize("path", [
    "skills/ost-builder/SKILL.md",
    "domains/discovery/CLAUDE.md",
    "skills/user-interview/SKILL.md",
])
def test_the_three_repaired_files_name_all_three_elements(path):
    """Pinning the repair itself: removing 'Means' is not enough if the replacement
    does not say what the model actually is."""
    text = (PLUGIN / path).read_text(encoding="utf-8").lower()
    for element in ("motivation", "persona", "simulation"):
        assert element in text, f"{path} no longer names {element}"


def test_the_schema_keeps_means_for_historical_instances():
    """THE COMPLEMENT. The schema must keep the legacy field, or canvases written
    before the correction stop validating — and the reason must stay readable."""
    schema = (PLUGIN / "schemas" / "canvas" / "scenarios.schema.json").read_text(
        encoding="utf-8")
    assert '"means"' in schema
    assert "NOT a Hoskins element" in schema
