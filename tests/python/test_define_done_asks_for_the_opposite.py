"""define-done asks whether the outcome is a choice: write the opposite, would anyone pick it (2026-10-16).

WHAT WAS WRONG. No check asked whether a written outcome is a real choice. Roger Martin's test, as
presented on the Product Growth podcast: if the opposite of a choice is stupid on its face, no choice has been made.
A done-bar such as "home cooks get better meals with less effort" passed every Mycelium check and
ruled out no work. A search of the plugin for "opposite", "real choice" and "Roger Martin" found
only devils-advocate's "What if the OPPOSITE is true?", which asks a different question.

WHAT THIS PINS. Step 1 of the sequence asks for the opposite after the outcome is written and before
the signal step, says it is advisory and the person judges, and keeps both wordings in `log[]`.
"""

from __future__ import annotations

from pathlib import Path

SKILL = (Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "skills" / "define-done"
         / "SKILL.md")


def _step_one() -> str:
    text = SKILL.read_text(encoding="utf-8")
    start = text.index("**1. \"When this is done, what's different")
    return text[start:text.index("**2. \"What's the ONE thing", start)]


def test_step_one_asks_for_the_opposite():
    assert "Write the opposite of this outcome. Would anyone choose it?" in _step_one()


def test_the_question_is_advisory_and_keeps_both_wordings():
    step = _step_one()
    assert "advisory, never a block" in step
    assert "the person judges" in step
    assert "`log[]`" in step
