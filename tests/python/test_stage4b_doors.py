"""The ways into L2 and L3 (v0.301.0, phase migration stage 4b; DL-1367, ruling C).

An L2 opens on an outcome its L1 has set, one per outcome; an L3 on the target its L2 has chosen,
one per target. An L2 with no target is asked to choose one by comparison. An L3 is stopped by its
front runner failing, or by every idea in its set failing, never by one sibling. A diamond in the
old one-object shape is asked, after the doors, to record the new fields.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import next_item as ni  # noqa: E402
import scale_locks as sl  # noqa: E402

TODAY = "2026-10-05"
L1 = {"id": "l1", "scale": "L1", "phase": "develop", "object_ref": "lead with cafes"}


def _sol(sid: str, verdict: str | None = None) -> dict:
    ra = {"statement": f"{sid} works"}
    if verdict:
        ra["verdict"] = verdict
    return {"id": sid, "riskiest_assumption": ra}


OPPS = {"desired_outcomes": [{"id": "out-a", "metric": "a"}, {"id": "out-b", "metric": "b"}],
        "opportunities": [{"id": "opp-1", "status": "open", "rolls_up_to": "out-a",
                           "solutions": [_sol("s1"), _sol("s2"), _sol("s3")]},
                          {"id": "opp-2", "status": "open", "rolls_up_to": "out-a"}]}


def _root(tmp_path: Path, diamonds: list[dict], opps: dict = OPPS) -> Path:
    (tmp_path / ".claude" / "canvas").mkdir(parents=True)
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    (tmp_path / ".claude" / "canvas" / "opportunities.yml").write_text(yaml.safe_dump(opps))
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text(
        yaml.safe_dump({"active_diamonds": diamonds}))
    return tmp_path


def _door(monkeypatch, tmp_path, diamonds, opps=OPPS, st=None):
    monkeypatch.setattr(ni.sl, "can_open", lambda *a, **k: [])  # every lock holds
    return ni._entry_door(_root(tmp_path, diamonds, opps), TODAY, st or {}, diamonds, [])


L2A = {"id": "l2a", "scale": "L2", "phase": "discover", "parent": "l1", "object_ref": "out-a",
       "target": {"opportunity": "opp-1", "chosen_on": "2026-10-01"}}


def test_the_l2_door_opens_on_an_outcome_no_l2_maps(monkeypatch, tmp_path):
    item = _door(monkeypatch, tmp_path, [L1, L2A, {"id": "l3", "scale": "L3", "parent": "l2a",
                                                    "object_ref": "opp-1"}])
    assert item["id"] == "door-l2:l1" and "out-b" in item["text"], item


def test_an_l2_with_no_target_is_asked_to_choose_one(monkeypatch, tmp_path):
    l2 = {k: v for k, v in L2A.items() if k != "target"}
    item = _door(monkeypatch, tmp_path, [L1, l2])
    assert item["id"] == "target-l2:l2a" and "compare" in item["text"]
    assert not ni.agent_owned(item), "the choice is the founder's; the agent drafts it"


def test_the_l3_door_opens_on_the_target_and_only_once(monkeypatch, tmp_path):
    l2b = {"id": "l2b", "scale": "L2", "parent": "l1", "object_ref": "out-b",
           "target": "opp-2"}
    item = _door(monkeypatch, tmp_path / "a", [L1, L2A, l2b])
    assert item["id"] == "door-l3:l2a" and "opp-1" in item["text"]
    worked = [L1, L2A, l2b, {"id": "l3", "scale": "L3", "parent": "l2a", "object_ref": "opp-1"}]
    item = _door(monkeypatch, tmp_path / "b", worked)
    assert item["id"] == "door-l3:l2b", "l2a's target is worked; l2b's is not"


def test_an_l2_in_the_old_shape_is_migrated_before_any_door(monkeypatch, tmp_path):
    """v0.307.0: the old shape is not read, so the target door would ask for a choice the old
    record already holds. The migration records it, and comes first."""
    old = {"id": "l2", "scale": "L2", "parent": "l1", "object_ref": "opp-1"}
    both = {"desired_outcomes": [{"id": "out-a", "metric": "a"}],
            "opportunities": OPPS["opportunities"]}
    worked = [L1, old, {"id": "l3", "scale": "L3", "parent": "l2", "object_ref": "opp-1"}]
    assert _door(monkeypatch, tmp_path / "a", worked, opps=both)["id"] == "target-l2:l2", \
        "the door alone would ask for the target again"
    item, _ = ni._pick_from(_root(tmp_path / "b", worked, both), "", TODAY, {}, "")
    assert item["id"] == "migrate-phase:project" and "l2" in item["text"], item
    assert ni.agent_owned(item), "recording the shape is Mycelium's bookkeeping"


def _l3(tmp_path, sols, front_runner=None) -> tuple[sl.State, dict]:
    opps = {"opportunities": [{"id": "opp-1", "status": "open", "solutions": sols}]}
    d = {"id": "l3", "scale": "L3", "phase": "develop", "object_ref": "opp-1"}
    if front_runner:
        d["front_runner"] = front_runner
    return sl.State(str(_root(tmp_path, [d], opps))), d


def test_one_idea_failing_does_not_stop_the_l3(tmp_path):
    st, d = _l3(tmp_path, [_sol("s1", "invalidated"), _sol("s2"), _sol("s3")])
    assert st.l3_failed(d) is None
    assert st.failed_assumption(d), "control: the old reading stopped it"


def test_none_works_stops_the_l3_and_says_so(tmp_path):
    st, d = _l3(tmp_path, [_sol("s1", "invalidated"), _sol("s2", "failed")])
    assert st.l3_failed(d)
    item = ni._pivot_item(Path(tmp_path), TODAY, {}, d)
    assert item and "none works" in item["text"] and "re-target" in item["text"]


def test_the_front_runner_failing_stops_it_and_names_the_way_on(tmp_path):
    st, d = _l3(tmp_path, [_sol("s1", "invalidated"), _sol("s2")], front_runner="s1")
    assert st.l3_failed(d)
    item = ni._pivot_item(Path(tmp_path), TODAY, {}, d)
    assert "front runner s1" in item["text"] and "another idea" in item["text"]
    st, d = _l3(tmp_path / "b", [_sol("s1"), _sol("s2", "invalidated")], front_runner="s1")
    assert st.l3_failed(d) is None, "a sibling of the front runner failed: not a stop"


# v0.313.0: a choice is written when it is made; its decision when its gates pass. Dogfood
# 2026-10-04: set_target was ruled needs-evidence, `target` was withheld as if it were the
# decision, and this item asked every session for a comparison the founder had already made.
def test_a_ruled_l2_with_no_target_is_told_the_choice_was_never_written(monkeypatch, tmp_path):
    l2 = {k: v for k, v in L2A.items() if k != "target"}
    l2.update(progression_ruling="needs-evidence", progression_ruled_at="2026-10-04")
    item = _door(monkeypatch, tmp_path, [L1, l2])
    assert item["id"] == "target-l2:l2a"
    assert "never written" in item["text"] and "needs-evidence, 2026-10-04" in item["text"]
    assert "compare its opportunities" not in item["text"], "the comparison was already made"


def test_an_unruled_l2_with_no_target_is_told_to_write_it_before_the_gates(monkeypatch, tmp_path):
    l2 = {k: v for k, v in L2A.items() if k != "target"}
    item = _door(monkeypatch, tmp_path, [L1, l2])
    assert "compare its opportunities" in item["text"]
    assert "even before `set_target` passes its gates" in item["text"]
