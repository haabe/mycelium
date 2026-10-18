"""A project's scope (solo or team, hobby or product) is asked before the brief, and a gate never rules on an empty one.

REGRESSION (v0.328.0), from the founder's own hobby project on plugin 0.317.5 (2026-10-09 to 10-18).
The brief flow asked its four questions and offered test, prototype or "Go deeper"; the scope
question lived only inside Go deeper's classification phase. He picked the test, so nothing asked,
`project_type` stayed "", and nine days later the L0 evidence gate ruled against the 0.9 base, noting
"project_type unset, so no adaptation", instead of solo_hobby's 0.63. He set it himself:
"this question should come in pretty early to prevent a hobby project to be demanded scores almost
impossible for a weekend project". The README promises a weekend project "a few lines each, not a
week of work".

Pinned where each decision is made: the interview's brief flow (asked before question 1), the start
composition's announcement of it, and the two skills that apply the threshold (ask before ruling).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "plugins" / "mycelium" / "skills"
SCOPE_LINE = "is this a solo hobby, a solo product, or a team product?"


def _read(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def test_interview_asks_scope_before_question_one():
    text = _read("interview")
    flow = text[text.index("### Universal Brief Flow") :]
    assert SCOPE_LINE in flow, "the brief flow must ask the scope line"
    assert flow.index(SCOPE_LINE) < flow.index("What are you trying to change, and for whom?"), (
        "the scope line must come before question 1, so the bars are sized from the first gate"
    )


def test_interview_writes_the_answer_the_same_turn():
    text = _read("interview")
    flow = text[text.index("### Universal Brief Flow") : text.index("What are you trying to change, and for whom?")]
    for value in ("solo_hobby", "solo_product", "team_startup", "team_enterprise"):
        assert value in flow, f"the scope step must map an answer to {value}"
    assert "the same turn" in flow


def test_go_deeper_does_not_ask_scope_twice():
    text = _read("interview")
    section = text[text.index("**Project scope**:") :]
    assert "already set" in section[:1200], "Go deeper must confirm a scope asked before question 1, not re-ask it"


def test_start_announces_the_scope_line():
    text = _read("start")
    assert "one line about the project" in text
    assert "Now: 4 questions about your idea" not in text, "the transition line must mention the scope line"


def test_gates_ask_before_ruling_on_an_empty_project_type():
    for skill in ("diamond-progress", "diamond-assess"):
        text = _read(skill)
        assert SCOPE_LINE in text, f"{skill} must ask the scope line when project_type is empty"
        assert "never apply the base" in text.lower(), f"{skill} must not apply the base threshold silently"
