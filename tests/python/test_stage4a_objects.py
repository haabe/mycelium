"""The L2 and L3 objects, additive (v0.300.0, phase migration stage 4a; DL-1367).

An L2 maps the opportunity space under one outcome and targets one opportunity at a time; an L3 is
that target and its set of solutions, and commits a front runner to build. The old shape (an L2 on
one opportunity, an L3 on one solution) was read through a translation until v0.307.0, which ended
it: migrate_phase.py records the new shape. The L4 reads
the verdicts of the solution it delivers, not the best or the worst of the set.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"))
import scale_locks as sl

PURPOSE = {"why": "Swaps are approved in one place so nobody relays them by hand",
           "who": {"description": "Shift leads at cafes with 2-10 sites"}}
EVIDENCE = {"evidence_type": "anecdotal", "evidence_sources": ["founder story: three relays"]}


def _sol(sid: str, verdict: str | None = None) -> dict:
    ra = {"statement": f"{sid} works", "cheapest_test": "a concierge week with two shift leads"}
    if verdict:
        ra["verdict"] = verdict
    return {"id": sid, "name": sid, "riskiest_assumption": ra}


def _opps(*sols) -> dict:
    return {"desired_outcomes": [{"id": "out-swaps", "metric": "swaps approved without a call",
                                  "north_star_input_ref": "swaps settled in the app"}],
            "opportunities": [{"id": "opp-001", "name": "Approver is off", "status": "open",
                               "rolls_up_to": "out-swaps", "provenance": EVIDENCE,
                               "solutions": list(sols)}]}


def _project(tmp_path: Path, diamonds: list[dict], opps: dict) -> str:
    c = tmp_path / ".claude"
    (c / "canvas").mkdir(parents=True)
    (c / "diamonds").mkdir(parents=True)
    w = {"purpose.yml": PURPOSE, "opportunities.yml": opps,
         "north-star.yml": {"metric": {"name": "swaps settled in the app per week"}},
         "landscape.yml": {"components": [{"id": "comp-1", "name": "group chat swaps"}]}}
    for name, doc in w.items():
        (c / "canvas" / name).write_text(yaml.safe_dump(doc))
    top = [{"id": "l0", "scale": "L0", "phase": "define"},
           {"id": "l1", "scale": "L1", "phase": "develop", "object_ref": "lead with cafes"}]
    (c / "diamonds" / "active.yml").write_text(yaml.safe_dump({"active_diamonds": top + diamonds}))
    return str(tmp_path)


L2_NEW = {"id": "l2", "scale": "L2", "phase": "define", "object_ref": "out-swaps",
          "target": {"opportunity": "opp-001", "chosen_on": "2026-10-01",
                     "compared": ["opp-002"], "why": "the most frequent relay"}}
L2_OLD = {"id": "l2", "scale": "L2", "phase": "define", "object_ref": "opp-001"}


def test_an_l2_names_its_outcome_and_targets_an_opportunity(tmp_path):
    st = sl.State(_project(tmp_path, [L2_NEW], _opps(_sol("sol-a"))))
    assert st.l2_outcome(L2_NEW) == "out-swaps"
    assert st.l2_target(L2_NEW) == "opp-001"
    assert st.l2_target({**L2_NEW, "target": None,
                         "targets": [{"opportunity": "opp-001"}]}) == "opp-001"


def test_an_l2_in_the_old_shape_is_no_longer_read_as_the_new(tmp_path):
    """v0.307.0: the translation ended; an L2 on one opportunity targets nothing until migrated."""
    st = sl.State(_project(tmp_path, [L2_OLD], _opps(_sol("sol-a"))))
    assert st.l2_target(L2_OLD) == ""
    assert st.l2_outcome(L2_OLD) == ""
    assert st.l2_target(L2_NEW) == "opp-001", "control: the new shape"


def test_an_l3_opens_on_its_l2s_target(tmp_path):
    l3 = {"id": "l3", "scale": "L3", "phase": "discover", "parent": "l2"}
    p = _project(tmp_path, [L2_NEW, l3], _opps(_sol("sol-a"), _sol("sol-b")))
    st = sl.State(p)
    assert st.missing(l3) == []
    assert len(st.build_solutions({**l3, "object_ref": "opp-001"})) == 2


def test_the_front_runner_is_only_the_named_one(tmp_path):
    st = sl.State(_project(tmp_path, [L2_NEW], _opps(_sol("sol-a"), _sol("sol-b"))))
    assert st.front_runner({"object_ref": "opp-001", "front_runner": "sol-b"}) == "sol-b"
    assert st.front_runner({"object_ref": "sol-a"}) == "", "old shape: not read since v0.307.0"
    assert st.front_runner({"object_ref": "opp-001"}) == "", "a set with none chosen yet"


def _l4_missing(tmp_path, sols, l3_extra=None, l4_ref="sol-a"):
    l3 = {"id": "l3", "scale": "L3", "phase": "deliver", "parent": "l2", "object_ref": "opp-001",
          "exposures": [{"recorded_at": "2026-10-01", "audience": "two shift leads",
                         "until": "2026-11-01", "channel": "by hand"}], **(l3_extra or {})}
    l4 = {"id": "l4", "scale": "L4", "phase": "discover", "parent": "l3", "object_ref": l4_ref}
    st = sl.State(_project(tmp_path, [L2_NEW, l3, l4], _opps(*sols)))
    return " ".join(st.missing(l4))


def test_the_l4_reads_the_evidence_of_what_it_delivers(tmp_path):
    """Until 0.299.0 a validated sibling opened the L4 for an untested idea."""
    out = _l4_missing(tmp_path / "a", [_sol("sol-a"), _sol("sol-b", "validated")])
    assert "medium confidence" in out, "sol-a is untested; sol-b's verdict is not its"
    assert "medium confidence" not in _l4_missing(
        tmp_path / "b", [_sol("sol-a", "validated"), _sol("sol-b")]), "control: its own verdict"


def test_a_sibling_that_failed_does_not_block_the_one_delivered(tmp_path):
    """Until 0.299.0 a failed idea C blocked the delivery of idea A (Torres p139)."""
    out = _l4_missing(tmp_path / "a", [_sol("sol-a", "validated"), _sol("sol-c", "invalidated")])
    assert "failed its test" not in out
    out = _l4_missing(tmp_path / "b", [_sol("sol-a", "invalidated"), _sol("sol-c", "validated")])
    assert "failed its test" in out, "control: the delivered one failed"


def test_an_l4_that_names_nothing_in_the_set_reads_the_front_runner(tmp_path):
    out = _l4_missing(tmp_path, [_sol("sol-a"), _sol("sol-b", "validated")],
                      l3_extra={"front_runner": "sol-b"}, l4_ref="the swap increment")
    assert "medium confidence" not in out
