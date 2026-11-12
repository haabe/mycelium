"""The skills that record or contact other people say what is kept, and who sends (harms check 2026-10-11).

WHAT WAS WRONG. `/mycelium:user-interview` keeps interviewees' verbatim words in the canvas, and the
operating contract has the canvas committed to git. `/mycelium:handoff` asks for the names of people
present and writes outreach briefs. Neither said a word about consent (0 matches each), and neither
cited `harness/delegation-authority.md`, where sending an external message is a human-approved act.
The people affected never chose the tool.

WHAT THIS PINS. Each skill has a consent step that says what the notes are for and where they are
kept, asks before keeping identifying words, keeps other people's names out unless they agreed, and
cites the authority file for who sends. The handoff capture template has a line for what the person
agreed to, above the quotes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[2] / "plugins" / "mycelium"
SKILLS = {name: PLUGIN / "skills" / name / "SKILL.md" for name in ("user-interview", "handoff")}


@pytest.mark.parametrize("name", sorted(SKILLS))
def test_the_skill_has_a_consent_step(name):
    text = SKILLS[name].read_text(encoding="utf-8")
    assert "Consent" in text
    for phrase in ("where they are kept", "git repository", "could identify",
                   "unless that person agreed", "harness/delegation-authority.md"):
        assert phrase in text, f"{name}: the consent step no longer says {phrase!r}"


def test_the_authority_file_says_a_human_approves_outreach():
    text = (PLUGIN / "harness" / "delegation-authority.md").read_text(encoding="utf-8")
    row = next(ln for ln in text.splitlines() if ln.startswith("| Send external message"))
    assert "human approves" in row and "drafts" in row


def test_user_interview_asks_before_the_first_question():
    text = SKILLS["user-interview"].read_text(encoding="utf-8")
    pre = text[text.index("## Pre-Interview"):text.index("## Question Design Rules")]
    assert "before the first question" in pre and "The agent drafts; the person sends" in pre


def test_the_capture_template_records_what_was_agreed_before_the_quotes():
    text = SKILLS["handoff"].read_text(encoding="utf-8")
    template = text[text.index("CAPTURE: [task objective]"):]
    assert template.index("Agreed to (") < template.index("Key quotes (")
