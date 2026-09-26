"""The L3's bars rise with its phases (v0.259.0).

E2E runs 42-43: the L3's 0.75 confidence threshold and its "prototype tested with users" evidence row
were read at every transition, so an L3 could not define before it had the validated prototype it
exists to produce. Four no-code tests over three in-world months, confidence 0.5 -> 0.6 against 0.64,
and no line of code. The threshold is the L3's exit bar; each transition names its own evidence.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2] / "plugins" / "mycelium"
THRESHOLDS = yaml.safe_load((ROOT / "engine" / "confidence-thresholds.yml").read_text())["scales"]
TRANSITIONS = ("discover_to_define", "define_to_develop", "develop_to_deliver", "deliver_to_complete")


def test_the_l3_threshold_is_compared_only_at_its_exit():
    assert THRESHOLDS["L3"]["threshold_applies_at"] == ["deliver_to_complete"]


def _l3_rows(heading: str) -> list[str]:
    text = (ROOT / "engine" / "theory-gates.md").read_text()
    section = text[text.index(heading):]
    section = section[:section.index("\n### ", 1)]
    return [line for line in section.splitlines() if line.startswith("| L3 | ")]


def test_the_l3_jtbd_and_privacy_rows_are_phased_too():
    """v0.262.0, E2E run 50: JTBD `fail` until testers answered and Privacy `pending` until the
    page was built, two design-time gates read as needing evidence from use."""
    (jtbd,) = _l3_rows("### 3. JTBD Gate")
    assert "Discover->Define" in jtbd and "Define->Develop" in jtbd and "hypotheses" in jtbd
    (privacy,) = _l3_rows("### 7. Privacy Gate")
    assert "Define->Develop" in privacy and "Develop->Deliver" in privacy
    assert "Nothing built is needed" in privacy


def test_the_l4_threshold_is_its_exit_bar_too():
    """v0.261.0, E2E run 47: the first L4 any run opened sat at 0.15 against 0.7 in discover,
    after its lock had admitted it on a test-validated verdict."""
    l4 = THRESHOLDS["L4"]
    assert l4["threshold_applies_at"] == ["deliver_to_complete"]
    assert tuple(l4["evidence_by_transition"]) == TRANSITIONS


def test_other_scales_keep_their_threshold_at_every_transition():
    for scale, entry in THRESHOLDS.items():
        if scale not in ("L3", "L4"):
            assert "threshold_applies_at" not in entry, scale


def test_each_l3_transition_names_its_own_evidence():
    by = THRESHOLDS["L3"]["evidence_by_transition"]
    assert tuple(by) == TRANSITIONS
    entry = set(by["discover_to_define"]) | set(by["define_to_develop"])
    assert not entry & {"prototype_feedback", "usability_test_results"}, (
        "a prototype tested with users is what the L3 builds toward, not what it enters on")
    assert "learning_delivery_verdict_on_the_riskiest_assumption" in by["deliver_to_complete"]


def test_the_evidence_gate_row_is_phased_and_the_skills_read_the_key():
    row = next(line for line in (ROOT / "engine" / "theory-gates.md").read_text().splitlines()
               if line.startswith("| L3 | "))
    for step in ("Discover->Define", "Define->Develop", "Develop->Deliver", "Deliver->Complete"):
        assert step in row, step
    for skill in ("diamond-progress", "diamond-assess"):
        assert "threshold_applies_at" in (ROOT / "skills" / skill / "SKILL.md").read_text(), skill


def test_the_evidence_per_transition_fits_the_product_type():
    """v0.269.0, overfit audit: every product type was asked for code tests at the L4's define ->
    develop, and the L3's develop -> deliver asked for a software prototype, so a course pilot, a
    concierge service or an AI tool had nothing that counted."""
    l4 = THRESHOLDS["L4"]["evidence_by_transition"]
    for t in ("define_to_develop", "develop_to_deliver"):
        assert set(l4[t]) >= {"software", "content", "ai_tool", "service_offering"}, t
        assert set(l4[t]) <= set(THRESHOLDS["L4"]["required_evidence"]), "same keys as required"
        for kind in ("content", "ai_tool", "service_offering"):
            assert not any("code" in e for e in l4[t][kind]), (t, kind)
    l3 = THRESHOLDS["L3"]["evidence_by_transition"]["develop_to_deliver"]
    assert not {"prototype_feedback", "technical_feasibility_spike"} & set(l3)
    assert any("outside_the_team" in e for e in l3)
    row = next(line for line in (ROOT / "engine" / "theory-gates.md").read_text().splitlines()
               if line.startswith("| L3 | "))
    assert "dry run of a service" in row, "the gate row names forms beyond a software prototype"
