"""Two additions to the gate table the phase gates read (v0.292.0, phase migration stage 0b-3a).

- XAI (the explainability gate) was Gate 13 in theory-gates.md and in no table the code read, so a
  table-driven migration would drop it silently. It now sits in `_MATRIX` at L3-L5, and applies only
  when the product records AI components.
- L5 gains Privacy and Service Quality before it reaches people (founder ruling f, 2026-09-30): a
  sign-up form, analytics or a campaign collects data from people who did not build it.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import scale_locks as sl  # noqa: E402

L3 = {"id": "l3-a", "scale": "L3", "phase": "develop",
      "theory_gates_status": {"explainability": "pending"}}


def _project(tmp_path: Path, ai: bool | None) -> Path:
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text("active_diamonds: []\n")
    if ai is not None:
        (tmp_path / ".claude" / "jit-tooling").mkdir(parents=True)
        (tmp_path / ".claude" / "jit-tooling" / "active-stack.yml").write_text(
            f"ai_components:\n  detected: {'true' if ai else 'false'}\n")
    return tmp_path


def test_the_explainability_gate_is_in_the_table_at_l3_to_l5():
    for scale in ("L3", "L4", "L5"):
        assert "explainability" in sl.transition_gates(scale, "develop->deliver")
        assert "explainability" in sl.transition_gates(scale, "deliver->complete")
    assert "explainability" not in sl.transition_gates("L2", "develop->deliver")


def test_it_is_left_out_for_a_product_with_no_ai():
    assert "explainability" not in sl.transition_gates("L3", "develop->deliver", ai=False)


def test_with_ai_components_a_pending_explainability_gate_blocks(tmp_path):
    st = sl.State(str(_project(tmp_path, ai=True)))
    assert st.gate_missing(L3, "explainability")


def test_control_without_ai_components_it_is_not_required(tmp_path):
    assert sl.State(str(_project(tmp_path, ai=False))).gate_missing(L3, "explainability") is None
    assert sl.State(str(_project(tmp_path / "none", ai=None))).gate_missing(L3, "explainability") is None


def test_l5_needs_privacy_and_service_quality_before_it_delivers():
    gates = sl.transition_gates("L5", "develop->deliver")
    assert "privacy" in gates and "service_quality" in gates
    assert "service_quality" in sl.transition_gates("L5", "deliver->complete")


def test_control_l5_privacy_is_not_added_before_develop():
    assert "privacy" not in sl.transition_gates("L5", "define->develop")
