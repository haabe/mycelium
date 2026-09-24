"""Every diamond scale must have a skill that opens it, and a way out.

WHY (v0.243.0). The founder's principle, stated when L1 and L4 were found unreachable:
*"If there's no way to progress into and out of all or any of the diamonds, the model is wrong."*

Until v0.243.0 `engine/diamond-rules.md` said L0 spawns L1 and L3 spawns L4, and no skill did
either. L1's only instruction was one passive line in `/diamond-progress` ("identify if child
diamonds should be spawned"); L4's "entry permit" (the Four Risks verdict) had no consumer. In
dogfood full-ladder runs 6 to 20 neither scale was ever created, including three runs in which L0
reached define, and v0.242.3 had closed the question as "correct by design" on the reasoning that an
event-recurring scale cannot have a catalogue door. That reasoning was right about doors and wrong
about entrances: no pile means no door, not no way in.

THE CHECK: for each scale, at least one shipped skill must instruct the agent to OPEN or OFFER a
diamond at that scale, in words a reader acts on, and (v0.245.0) that door must check the scale's
entry lock first: a way in is not a way in before the parent has established what it builds on. L0 is founded by `/interview`. Exits are generic:
`/diamond-progress` must carry both completion (Deliver->Complete) and the killed path.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "plugins" / "mycelium" / "skills"
RULES = ROOT / "plugins" / "mycelium" / "engine" / "diamond-rules.md"

#: scale -> a pattern that, found in a SKILL.md, is an instruction to open a cycle at that scale.
ENTRY = {
    "L0": re.compile(r"scale:\s*L0\b"),
    "L1": re.compile(r"open an L1 Strategy diamond"),
    "L2": re.compile(r"open an L2 diamond"),
    "L3": re.compile(r"open an L3 diamond"),
    "L4": re.compile(r"open an L4 Delivery diamond"),
    "L5": re.compile(r"spawns an L5 Market diamond"),
}


def _skills_matching(pattern: re.Pattern) -> list[str]:
    return sorted(p.parent.name for p in SKILLS.glob("*/SKILL.md")
                  if pattern.search(p.read_text(encoding="utf-8")))


@pytest.mark.parametrize("scale", sorted(ENTRY))
def test_every_scale_has_a_skill_that_opens_it(scale):
    openers = _skills_matching(ENTRY[scale])
    assert openers, (
        f"no shipped skill opens or offers an {scale} diamond. A scale with no way in means the "
        "model is wrong; a sentence in an engine doc saying it will be spawned is not a way in."
    )


def test_l1_and_l4_offers_are_where_their_events_happen():
    """The entrances for the event-recurring scales sit in the skill running when the event occurs."""
    assert "wardley-map" in _skills_matching(ENTRY["L1"])
    assert "preflight" in _skills_matching(ENTRY["L4"])


#: The door for each scale above L0, and the lock call it must make before offering (v0.245.0).
DOORS = {"L1": "wardley-map", "L2": "ost-builder", "L3": "ice-score", "L4": "preflight",
         "L5": "launch-tier"}


@pytest.mark.parametrize("scale", sorted(DOORS))
def test_every_door_checks_its_entry_lock(scale):
    """Founder model (2026-09-24): each scale opens on what its parent has established. v0.243.0
    made every door open "whether or not the parent has progressed", which answered ENTRY with a
    ruling about SPEED; the door must now ask the lock before it offers."""
    text = (SKILLS / DOORS[scale] / "SKILL.md").read_text(encoding="utf-8")
    assert f"--can-open {scale}" in text, f"{DOORS[scale]} offers an {scale} without checking its lock"


def test_no_door_opens_regardless_of_the_parent():
    offenders = [str(p.relative_to(ROOT)) for p in [*SKILLS.glob("*/SKILL.md"), RULES]
                 if re.search(r"whether or not (the|other) (L0 )?(parent|diamonds)",
                              p.read_text(encoding="utf-8"))]
    assert not offenders, f"a door still opens whether or not the parent is ready: {offenders}"


def test_the_rules_separate_entry_from_speed():
    text = RULES.read_text(encoding="utf-8")
    assert "### Entry locks" in text
    assert "Once open, a diamond moves at its own speed." in text


def test_no_page_says_a_parent_bounds_a_child():
    """The undefined 'bounds how far it can go' was read as 'children cannot progress while the parent
    is blocked', and a dogfood run then never assessed its L2 and L3 diamonds. It is replaced by the
    ruling that diamonds progress at their own speed."""
    offenders = [str(p.relative_to(ROOT)) for p in [*SKILLS.glob("*/SKILL.md"), RULES]
                 if re.search(r"bounds how far|bounds the cycle", p.read_text(encoding="utf-8"))]
    assert not offenders, f"still states a parent bound: {offenders}"


def test_every_scale_has_a_way_out():
    text = (SKILLS / "diamond-progress" / "SKILL.md").read_text(encoding="utf-8")
    assert "Deliver->Complete" in text, "no completion exit in /diamond-progress"
    assert "killed_diamonds" in text, "no killed exit in /diamond-progress"
