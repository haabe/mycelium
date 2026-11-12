"""Technique 7's evidence base carries the 2026-09-20 scorecard, and keeps its caveat.

WHAT WAS WRONG. devils-advocate's Technique 7 (the blind adversarial pass) rested its record on "two
runs, one author, one project". A later day ran about ten blind-reader runs, checked every objection
against the code or data, and scored six confirmed catches (all on work that had passed self-review
and the local gates), one refuted, and three frame errors no reader could see, all caught by the
founder. The skill did not say so, nor that the reader and the human catch different kinds of error.

WHAT THIS PINS. The third record is on the page with its numbers and its split, says it was scored by
the session that ran it and not independently, and the not-generalised caveat stays.
"""

from __future__ import annotations

from pathlib import Path

SKILL = (Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "skills"
         / "devils-advocate" / "SKILL.md")


def _technique_7() -> str:
    text = SKILL.read_text(encoding="utf-8")
    start = text.index("## Technique 7:")
    return text[start:text.index("## Technique 6:", start)]


def test_the_caveat_stays():
    section = _technique_7()
    assert "**WHAT IS NOT CLAIMED**: that this generalises." in section
    assert "one author and one project" in section


def test_the_third_record_is_there_with_its_scoring_named():
    section = _technique_7()
    assert "A THIRD RECORD, 2026-09-20" in section
    for phrase in ("Six confirmed catches", "One refuted objection", "Three errors no reader could see",
                   "not by an independent scorer", "errors in the reasoning", "errors in the frame"):
        assert phrase in section, f"Technique 7 no longer says {phrase!r}"
