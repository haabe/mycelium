"""The interview snapshot asks, per story, whether anyone was acting on the need, and the L2's
comparison of sibling opportunities reports it (founder ruling 2026-11-12, "Add the field").

Candidate l2-evidence-never-asks-whether-anyone-is-acting-on-the-need: an L2 could clear its
interview floor on voiced pains alone, because a need someone was working on and a pain they lived
with were recorded alike. The schema and the reader are tested in test_validate_canvas.py
(`acting_on`, `acted_on_coverage`); this file pins the writer and the comparison step.
"""

from __future__ import annotations

from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "skills"


def _flat(skill: str) -> str:
    return " ".join((SKILLS / skill / "SKILL.md").read_text(encoding="utf-8").split())


def test_snapshot_records_acting_on_per_story_with_the_three_answers():
    text = _flat("user-interview")
    snap = text[text.index("## Post-Interview Snapshot"):text.index("### Scenario Extraction")]
    assert "**Acting on it now?** One answer per story" in snap
    for answer in ("`under_way`", "`tried_options`", "`lived_with`"):
        assert answer in snap, answer
    assert "`acting_on`" in snap and "provenance.evidence_sources" in snap
    assert "Snyder, *The Power of Pull* (Basic Venture, 2026)" in snap


def test_target_comparison_reports_acted_on_against_voiced():
    text = _flat("ost-builder")
    step = text[text.index("**Choosing the target is the L2's**"):text.index("**The L3 door.**")]
    assert "how much of its evidence shows the need acted on and how much only voiced" in step
    assert "`acting_on`" in step and "into `compared`" in step
    assert "COVERAGE (acted on)" in step
