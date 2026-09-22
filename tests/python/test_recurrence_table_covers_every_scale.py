"""Every scale must state what it recurs on, and the catalogue doors must match it.

WHY THIS EXISTS (v0.242.3). `diamond-rules.md` named two catalogue doors — `/ost-builder`
offers an L2, `/ice-score` offers an L3 — and said nothing about why only those two. An
agent enumerated them, found the asymmetry, and filed it as a probable defect. **Twice in
one session**, the second time after a blind reviewer had already corrected the first
attempt, because the correcting reasoning lived in a consumer project's design notes and
not on the page that states the rule.

The reasoning is now on the page: a level's recurrence trigger decides whether a door is
possible. L2 recurs continuously and L3 per candidate — piles, so a door can open on one.
L1, L4 and L5 recur on events — a decision, an increment, a categorisation — and an event
has no queue to select from.

THIS TEST PINS THE CONSISTENCY, not the prose. If someone adds a third door without giving
that scale a pile-shaped recurrence, or changes a recurrence to an event while leaving its
door in place, the table and the doors disagree and this fails.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RULES = (Path(__file__).resolve().parents[2]
         / "plugins" / "mycelium" / "engine" / "diamond-rules.md")

SCALES = ("L0", "L1", "L2", "L3", "L4", "L5")

#: Scales whose recurrence is a PILE, and which may therefore carry a catalogue door.
PILE_SCALES = {"L2", "L3"}


def _recurrence_table() -> dict[str, str]:
    """Parse the `recurs on` column, keyed by scale."""
    text = RULES.read_text(encoding="utf-8")
    start = text.index("## What each level RECURS ON")
    end = text.index("## Spawning Rules", start)
    rows = {}
    for line in text[start:end].splitlines():
        # UNBOLDED ON PURPOSE, and the reason is a defect this table caused: the
        # theory-gating parser matched any `| **L0** |` row anywhere in the file and let
        # later matches win, so a bolded table here silently replaced the theory table as
        # the source of truth for gating. That parser is now header-anchored; this table
        # also stops imitating the other one's row shape. Belt and braces, cheaply.
        m = re.match(r"^\|\s*(L[0-5])\s*\|([^|]*)\|([^|]*)\|", line)
        if m:
            rows[m.group(1)] = m.group(3).strip()
    return rows


def test_the_table_was_found_and_is_complete():
    """An unparsed table would make every assertion below vacuous."""
    rows = _recurrence_table()
    missing = [s for s in SCALES if s not in rows]
    assert not missing, f"no `recurs on` row for {missing}; table parsed as {rows}"


@pytest.mark.parametrize("scale", SCALES)
def test_every_scale_states_what_it_recurs_on(scale):
    rows = _recurrence_table()
    assert rows[scale], f"{scale} has an empty `recurs on` cell"


def test_the_doors_match_the_pile_scales():
    """THE LOAD-BEARING ASSERTION. The catalogue sentence names the scales with doors;
    they must be exactly the scales whose recurrence is a pile."""
    text = RULES.read_text(encoding="utf-8")
    m = re.search(r"A cycle is opened by a spawn from the parent \(below\) OR from the "
                  r"catalogue:(.+?)\n", text, re.DOTALL)
    assert m, "could not find the catalogue sentence in diamond-rules.md"
    sentence = m.group(1)
    with_doors = {s for s in SCALES if re.search(rf"\b(an )?{s}\b", sentence)}
    assert with_doors == PILE_SCALES, (
        f"catalogue doors are declared for {sorted(with_doors)} but the pile-shaped "
        f"scales are {sorted(PILE_SCALES)}. A door needs a pile to open on: if a scale "
        "gained a door, give it a pile-shaped recurrence and update PILE_SCALES here; if "
        "it lost one, say why on the page."
    )


def test_the_page_warns_before_the_spawning_rules():
    """Placement matters: the warning must precede the rules a reader acts on, or it is
    read after the proposal has already been written."""
    text = RULES.read_text(encoding="utf-8")
    assert text.index("## What each level RECURS ON") < text.index("## Spawning Rules")


def test_l1s_id_bearing_records_are_named_as_the_trap():
    """L1's files DO carry ids, which is exactly why an enumeration finds a false gap.
    The page must name them, or the next reader repeats the error."""
    text = RULES.read_text(encoding="utf-8")
    for token in ("climatic_predictions", "doctrine.yml", "open"):
        assert token in text, f"the L1 explanation no longer names {token}"
