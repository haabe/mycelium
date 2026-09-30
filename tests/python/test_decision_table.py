"""The evidence gates are keyed to the decisions they guard (v0.298.0, stage 3b-1, DL-1366).

Each level runs a learning loop: set a target, start an experiment, commit to build, release,
close. A gate belongs to the decision it guards, and each phase move makes a fixed set of those
decisions until the phase is retired. This is a translation: every phase move still needs exactly
the gates it needed in 0.297.0, pinned below cell by cell.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"))
import check_gate_set_drift as drift
import scale_locks as sl

#: The per-transition table as 0.297.0 shipped it, frozen. Change it only with a release that
#: changes a gate on purpose, and say so in that release.
TABLE_0297 = {"evidence": {"discover->define": ("L0", "L1", "L2", "L3", "L4", "L5"),
                  "define->develop": ("L0", "L1", "L2", "L3", "L4", "L5"),
                  "develop->deliver": ("L0", "L1", "L2", "L3", "L4", "L5"),
                  "deliver->complete": ("L0", "L1", "L2", "L3", "L4", "L5")},
     "four_risks": {"define->develop": ("L1", "L2", "L3", "L4"),
                    "develop->deliver": ("L1", "L2", "L3", "L4")},
     "jtbd": {"discover->define": ("L1", "L2", "L3"), "define->develop": ("L1", "L2", "L3")},
     "cynefin": {"define->develop": ("L0", "L1", "L2", "L3", "L4", "L5")},
     "bias": {"discover->define": ("L0", "L1", "L2", "L3", "L4", "L5"),
              "define->develop": ("L0", "L1", "L2", "L3", "L4", "L5"),
              "develop->deliver": ("L0", "L1", "L2", "L3", "L4", "L5"),
              "deliver->complete": ("L0", "L1", "L2", "L3", "L4", "L5")},
     "security": {"develop->deliver": ("L3", "L4", "L5"), "deliver->complete": ("L3", "L4", "L5")},
     "privacy": {"define->develop": ("L2", "L3", "L4"),
                 "develop->deliver": ("L2", "L3", "L4", "L5")},
     "bvssh": {"deliver->complete": ("L0", "L1", "L2", "L3", "L4", "L5")},
     "service_quality": {"develop->deliver": ("L2", "L3", "L4", "L5"),
                         "deliver->complete": ("L2", "L3", "L4", "L5")},
     "delivery_metrics": {"deliver->complete": ("L3", "L4")},
     "corrections": {"discover->define": ("L0", "L1", "L2", "L3", "L4", "L5"),
                     "define->develop": ("L0", "L1", "L2", "L3", "L4", "L5"),
                     "develop->deliver": ("L0", "L1", "L2", "L3", "L4", "L5"),
                     "deliver->complete": ("L0", "L1", "L2", "L3", "L4", "L5")},
     "regulatory": {"define->develop": ("L3", "L4", "L5"), "develop->deliver": ("L3", "L4", "L5")},
     "explainability": {"develop->deliver": ("L3", "L4", "L5"),
                        "deliver->complete": ("L3", "L4", "L5")}}

SCALES = ("L0", "L1", "L2", "L3", "L4", "L5")


def test_the_table_derived_from_decisions_is_the_0297_table():
    assert sl.gate_matrix() == TABLE_0297
    assert list(sl.gate_matrix()) == list(TABLE_0297), "report order kept"


@pytest.mark.parametrize("ai", [True, False])
def test_every_move_needs_the_gates_of_the_decisions_it_makes(ai):
    for scale in SCALES:
        for t, decisions in sl.TRANSITION_DECISIONS.items():
            union = {g for d in decisions for g in sl.decision_gates(scale, d, ai=ai)}
            assert set(sl.transition_gates(scale, t, ai=ai)) == union, (scale, t)


def test_each_gate_sits_with_the_decision_it_guards():
    assert "cynefin" in sl.decision_gates("L3", "start_experiment")
    assert "cynefin" not in sl.decision_gates("L3", "commit_to_build")
    assert {"four_risks", "regulatory"} <= set(sl.decision_gates("L3", "commit_to_build"))
    assert "bvssh" in sl.decision_gates("L0", "close")
    for d in sl.DECISIONS:
        assert {"bias", "corrections"} <= set(sl.decision_gates("L0", d)), d


def test_define_to_develop_starts_an_experiment_and_commits_to_build():
    assert sl.transition_decisions("define->develop") == ("start_experiment", "commit_to_build")
    assert sl.transition_decisions("nowhere->else") == ()


def test_every_decision_gate_is_a_defined_gate():
    for rows in sl.DECISIONS.values():
        assert set(rows) <= drift.GATE_KEYS


def test_a_move_without_its_record_is_told_which_decisions_to_name(tmp_path):
    d = {"id": "l0-a", "scale": "L0", "phase": "define",
         "theory_gates_status": dict.fromkeys(sl.transition_gates("L0", "define->develop"), "pass")}
    out = sl.State(str(tmp_path)).move_missing({**d, "phase": "develop"}, "define")
    assert any("decisions: [start_experiment, commit_to_build]" in x for x in out)
