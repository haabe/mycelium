"""The Bias gate must say, where it is decided, that a planned mitigation counts as documented.

REGRESSION (2026-09-23, dogfood full-ladder run 18). Two bias audits met all four pass criteria
in `theory-gates.md` §5 (checklist reviewed, biases named with mitigations documented,
disconfirming evidence sought and cited, the agent's own biases examined) and recorded the gate
`not-passed` on the L0, L2 and L3 diamonds alike: "a citation is not a resolution, and no probe
has run". Evidence, Corrections and JTBD had passed, so that one reading held every diamond in
Discover. The criteria never asked for a resolution. Running the experiment is required by the
Cynefin gate at Define->Develop and by Four Risks; asking for it at the first transition gates
the start of a cycle on work its own later transitions exist to do.

Founder ruling, same day: planned mitigation is enough at Discover->Define. Pinned in both
places the decision is made, the gate definition and the skill that records the gate, because
v0.242.5 found a rule that lived only in the engine doc being missed by the skill that acted.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATES = ROOT / "plugins" / "mycelium" / "engine" / "theory-gates.md"
SKILL = ROOT / "plugins" / "mycelium" / "skills" / "bias-check" / "SKILL.md"


def _bias_section() -> str:
    text = GATES.read_text(encoding="utf-8")
    start = text.index("### 5. Bias Gate")
    return text[start:text.index("### 6. Security Gate", start)]


def test_gate_definition_says_a_planned_mitigation_counts():
    section = _bias_section()
    assert "may be PLANNED" in section
    assert "does not require that the mitigation has already" in section


def test_gate_definition_says_cited_disconfirming_evidence_is_sought():
    assert "has been *sought*" in _bias_section()


def test_gate_definition_names_where_the_experiment_is_required():
    section = _bias_section()
    assert "Cynefin gate at Define->Develop" in section
    assert "Four Risks" in section


def test_the_skill_that_records_the_gate_says_the_same():
    text = SKILL.read_text(encoding="utf-8")
    assert "## Recording the Bias gate" in text
    assert "A planned mitigation counts as" in text
    assert "not this gate's test" in text
