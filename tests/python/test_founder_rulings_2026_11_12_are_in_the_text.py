"""Six founder rulings of 2026-11-12 change what the agent is told to do; this pins each one's text.

WHAT WAS WRONG, ONE LINE EACH.
1. The Four Risks gate folded ethics into a Viability bullet ("legal, ethical constraints"), the
   arrangement Cagan says loses it: no question asked it by name and nothing pointed at /harms-check.
2. A Wardley map and a Four Risks verdict were reviewed only by the agent that wrote them; the
   blind pass (devils-advocate Technique 7) existed and nothing ran it. Nothing said a blind pass
   stands in for a second person's judgement and never for their stake.
3. No principle said complying with a gate has to cost less than the cheapest way around it, and
   no review step asked a new gate's author to compare the two.
4. assumption-test did not say which claims published research can answer (claims about people in
   general) and which need a human (claims about this product).
5. define-done asked "Write the opposite of this outcome. Would anyone choose it?"; an L1 or L2
   setting its target in diamond-progress was not asked it.
6. No rule said a dismissal made from metadata, when the artifact is one call away, needs the
   artifact opened first.

Each test fails on the 0.336.0 text.
"""

from __future__ import annotations

import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2] / "plugins" / "mycelium"
SKILLS = PLUGIN / "skills"


def _read(*parts: str) -> str:
    return PLUGIN.joinpath(*parts).read_text(encoding="utf-8")


def _between(text: str, start: str, end: str) -> str:
    i = text.index(start)
    return text[i:text.index(end, i + len(start))]


# ----------------------------------------------------------------- 1. ethics question in Viability

def _four_risks_gate() -> str:
    return _between(_read("engine", "theory-gates.md"), "### 2. Four Risks Gate", "### 3. JTBD Gate")


def test_the_gate_asks_should_we_build_it_inside_viability():
    gate = _four_risks_gate()
    row = next(line for line in gate.splitlines() if line.startswith("| **Business Viability**"))
    assert '"Should we build it?"' in row
    assert "/harms-check" in gate
    assert "Viability stays one of four risks" in gate


def test_it_is_still_four_risks():
    gate = _four_risks_gate()
    rows = [line for line in gate.splitlines()
            if line.startswith("| **") and "|" in line[4:]]
    assert len(rows) == 4, rows
    assert "Ethical" not in "".join(r.split("|")[1] for r in rows)


def test_ice_score_and_ost_builder_ask_it_too():
    for skill in ("ice-score", "ost-builder"):
        text = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
        bullet = next(line for line in text.splitlines() if "**Viability** (cross-cutting)" in line)
        assert '"Should we build it?"' in bullet, skill
        assert "/mycelium:harms-check" in bullet, skill
        assert "four risks" in bullet.lower(), skill


# ----------------------------------------------------------------- 2. default blind pass

def test_wardley_map_runs_the_blind_pass_after_the_map_is_drafted():
    text = (SKILLS / "wardley-map" / "SKILL.md").read_text(encoding="utf-8")
    step = _between(text, "### 8b. Blind challenge of the map", "### 9. Offer")
    assert "runs by default" in step
    assert "/mycelium:devils-advocate` Technique 7" in step
    assert "can only raise concerns" in step
    assert "never for their stake" in step
    log = _between(text, "## Decision Log", "## Connection")
    assert "the blind-pass line from step 8b" in log


def test_diamond_progress_runs_it_before_four_risks_is_recorded_passed():
    text = (SKILLS / "diamond-progress" / "SKILL.md").read_text(encoding="utf-8")
    step = _between(text, "2b-2. **Four Risks: a blind pass runs before the gate is recorded as passed**",
                    "2c. **Build-to-learn")
    assert "/mycelium:devils-advocate` Technique 7" in step
    assert "It never passes anything." in step
    assert "never cited as a reason the gate passed" in step
    # the result lands on an existing field of the gate record, not a new one
    assert "add one line to its `note`" in step
    assert "`progression_blockers` with `gate: four_risks`" in step
    gate = _four_risks_gate()
    assert "step 2b-2" in gate and "`decisions[].note`" in gate


def test_devils_advocate_states_judgement_never_stake_once():
    text = (SKILLS / "devils-advocate" / "SKILL.md").read_text(encoding="utf-8")
    assert text.count("### What it stands in for: judgement, never stake") == 1
    section = _between(text, "### What it stands in for: judgement, never stake", "## Technique 6:")
    for word in ("users", "sensing", "adopting", "never to clear one"):
        assert word in section, word
    # the section no longer says nothing invokes it, now that two places do
    assert "Two places run Technique 7 by default" in text


# ----------------------------------------------------------------- 3. price the bypass

def test_the_principle_is_stated_with_its_three_consequences():
    text = _read("harness", "design-principles.md")
    section = _between(text, "## Price the bypass", "## Model variance")
    assert "costs less than the cheapest way around it" in section
    for lead in ("A field nothing writes cannot be complied with at all",
                 "A gate that passes on absence prices the bypass at zero",
                 "The cheapest path has to lead where the work should go"):
        assert lead in section, lead
    assert "check 10 of the Mandatory Pre-Ship Protocol" in section


def test_every_new_gate_is_reviewed_for_its_bypass_price_before_it_ships():
    text = _read("engine", "agent-operating-contract.md")
    gp = _between(text, "## Mandatory Pre-Ship Protocol (G-P-pre)", "## Mandatory Post-Task Protocol")
    line = next(s for s in gp.splitlines() if s.startswith("10. **Bypass price**"))
    assert "a new gate" in line
    assert "exemption and waiver fields included" in line
    assert "Price the bypass" in line


# ----------------------------------------------------------------- 4. literature vs this product

def test_assumption_test_routes_people_in_general_to_literature_and_this_product_to_a_human():
    text = (SKILLS / "assumption-test" / "SKILL.md").read_text(encoding="utf-8")
    section = _between(text, "### Published research: a claim about people, or a claim about this product?",
                       "### Tests (controlled artifacts")
    assert "**A claim about people in general**" in section
    assert "what was measured, on whom, how many" in section
    assert "Being published is not a grade" in section
    assert "**A claim about this product, its market or its users**" in section
    assert "needs a human" in section


# ----------------------------------------------------------------- 5. the opposite test at set_target

def test_diamond_progress_asks_the_opposite_at_an_l1_or_l2_set_target():
    text = (SKILLS / "diamond-progress" / "SKILL.md").read_text(encoding="utf-8")
    step = _between(text, "1c. **At an L1 or L2 `set_target`: the opposite question", "2. **Run all required")
    assert '"Write the opposite of this outcome. Would anyone choose it?"' in step
    assert "a prompt, never a block" in step
    assert "the person judges" in step
    # the same words define-done asks
    dd = (SKILLS / "define-done" / "SKILL.md").read_text(encoding="utf-8")
    assert "Write the opposite of this outcome. Would anyone choose it?" in dd


# ----------------------------------------------------------------- 6. a dismissal from metadata

def test_the_contract_says_open_the_artifact_before_dismissing_on_metadata():
    text = _read("engine", "agent-operating-contract.md")
    assert ("**A dismissal made from metadata, when the artifact is one call away, needs the "
            "artifact opened first.**") in text


def test_the_contract_still_fits_its_parts():
    sys.path.insert(0, str(PLUGIN / "scripts"))
    import contract_parts

    assert contract_parts.main(["--check"]) == 0
    text = contract_parts.CONTRACT.read_text(encoding="utf-8")
    for root in ("/r", "/" + "a" * 219):
        parts = contract_parts.split(text, root)
        assert len(parts) <= contract_parts.MAX_PARTS
        assert max(len(p) for p in parts) <= contract_parts.PART_LIMIT
