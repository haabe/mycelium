"""Lifecycle, from the 2026-10-01 control audit (DL-1370, batch 3: K3, P15, P16). Each gap was
reproduced on 0.307.6 before it was fixed. The delivering L3 here records its decisions and its
running exposure directly (founder rule, 2026-10-01); writes are judged as the hook judges them,
with no fixture conversion of the proposed text.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import diamond_rulings as dr  # noqa: E402
import scale_locks as sl  # noqa: E402
import test_scale_locks as tsl  # noqa: E402

AF = Path(".claude") / "diamonds" / "active.yml"
RELEASED = [{"decision": d, "on": "2026-09-20"}
            for d in ("set_target", "start_experiment", "commit_to_build", "release")]
RUNNING = {**tsl.RECORD, "started": "2026-09-21"}  # reaching people, nothing `ended`
ENDED = {**RUNNING, "ended": {"how": "withdrawn", "on": "2026-09-24"}}


@pytest.fixture(autouse=True)
def _today(monkeypatch):
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-09-25")


def _l3(record=RUNNING, **extra) -> dict:
    return {"id": "l3-a", "scale": "L3", "object_ref": "sol-001", "evidence_type": "anecdotal",
            "theory_gates_status": dict(tsl.EXPOSE_PASSED), "decisions": list(RELEASED),
            "exposures": [dict(record)], **extra}


def _project(tmp_path: Path, diamonds: list[dict]) -> str:
    return tsl._project(tmp_path, purpose=tsl.PURPOSE, opps=tsl._full_opps(), diamonds=diamonds)


def _disk(p: str) -> dict:
    return yaml.safe_load((Path(p) / AF).read_text())


def _write(p: str, doc: dict) -> list[str]:
    """The hook's verdict on writing `doc`, unconverted: it is what the agent writes."""
    return sl.new_diamond_violations(p, {"tool_name": "Write", "tool_input": {
        "file_path": str(AF), "content": yaml.safe_dump(doc)}})


def _without(doc: dict, did: str) -> dict:
    out = copy.deepcopy(doc)
    out["active_diamonds"] = [d for d in out["active_diamonds"] if d.get("id") != did]
    return out


def _get(doc: dict, did: str) -> dict:
    return copy.deepcopy(next(d for d in doc["active_diamonds"] if d.get("id") == did))


def _ends(out: list[str]) -> bool:
    return any("how its learning delivery ended" in v for v in out)


# K3 -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("state", [None, "archived", "killed"])
def test_moving_a_delivering_l3_to_the_archive_says_how_its_delivery_ended(tmp_path, state):
    """K3: 4c (0.302.0) named "moving the L3 to the archived list" and judged it against the new
    file, where the L3 already read as closed."""
    p = _project(tmp_path, [_l3()])
    doc = _disk(p)
    l3 = {**_get(doc, "l3-a"), **({"state": state} if state else {})}
    assert _ends(_write(p, {**_without(doc, "l3-a"), "archived_diamonds": [l3]}))


def test_control_an_archived_l3_whose_delivery_ended_passes(tmp_path):
    p = _project(tmp_path, [_l3(ENDED)])
    doc = _disk(p)
    assert not _ends(_write(p, {**_without(doc, "l3-a"),
                                "archived_diamonds": [_get(doc, "l3-a")]}))


def test_a_parked_l3_killed_later_says_how_its_delivery_ended(tmp_path):
    """K3: parking is a pause and is not judged; killing the parked L3 was read as closing an
    already closed one."""
    p = _project(tmp_path, [_l3()])
    doc = _disk(p)
    parked = copy.deepcopy(doc)
    parked["active_diamonds"] = [{**d, "state": "parked"} if d["id"] == "l3-a" else d
                                 for d in parked["active_diamonds"]]
    assert not _ends(_write(p, parked)), "control: parking is a pause"
    (Path(p) / AF).write_text(yaml.safe_dump(parked))
    killed = copy.deepcopy(parked)
    killed["active_diamonds"] = [{**d, "state": "killed"} if d["id"] == "l3-a" else d
                                 for d in killed["active_diamonds"]]
    assert _ends(_write(p, killed))


def test_deleting_a_delivering_l3_from_the_file_says_how_its_delivery_ended(tmp_path):
    """K3: an L3 removed from the file was in no list the rule read. Deleting it, then adding it
    back as completed in a later write, passed both writes."""
    p = _project(tmp_path, [_l3()])
    assert _ends(_write(p, _without(_disk(p), "l3-a")))


def test_control_deleting_an_l3_that_reaches_nobody_is_not_this_rule(tmp_path):
    p = _project(tmp_path, [_l3(ENDED)])
    assert not _ends(_write(p, _without(_disk(p), "l3-a")))


# P15 ------------------------------------------------------------------------------------------

def test_an_l3_inheriting_its_l2s_target_closes_when_the_l2_retargets(tmp_path):
    """P15: an L3 with no `object_ref` reads its L2's target; judged against the new file, it had
    already followed the L2 to the new one, and stayed open with a running exposure."""
    opps = tsl._full_opps()
    opps["opportunities"].append({**opps["opportunities"][0], "id": "opp-002"})
    l3 = {**_l3(), "parent": "l2"}  # the suite's ladder: l2 targets opp-001
    l3.pop("object_ref")
    p = tsl._project(tmp_path, purpose=tsl.PURPOSE, opps=opps, diamonds=[l3])
    doc = _disk(p)
    assert sl.State(p).l3_target(_get(doc, "l3-a")) == "opp-001", "it inherits the L2's target"
    moved = copy.deepcopy(doc)
    moved["active_diamonds"] = [{**d, "target": "opp-002"} if d["id"] == "l2" else d
                                for d in moved["active_diamonds"]]
    assert any("no longer targets" in v for v in _write(p, moved))


# P16 ------------------------------------------------------------------------------------------

def test_a_repair_of_a_broken_file_is_judged_with_the_running_exposure(tmp_path):
    """P16: with no commit, the last good state came from the rulings record, which kept no
    exposures, so a repair that widened a running delivery was unjudged."""
    p = _project(tmp_path, [_l3()])
    dr.record(Path(p), "s1")  # the record a good write leaves
    good = _disk(p)
    (Path(p) / AF).write_text("active_diamonds: [broken\n")  # a shell write broke it
    wider = copy.deepcopy(good)
    wider["active_diamonds"] = [{**d, "exposures": [{**d["exposures"][0],
                                                     "audience": "everyone with the link"}]}
                                if d["id"] == "l3-a" else d for d in wider["active_diamonds"]]
    assert any("changes" in v for v in _write(p, wider))
    assert not any("changes" in v for v in _write(p, good)), "control: the repair alone"


def test_a_repair_after_a_shell_break_is_judged_with_the_snapshot(tmp_path):
    """P16, the upgrade window: a record written before 0.307.7 keeps no exposures; the shell
    guard's snapshot from just before the breaking command does."""
    p = _project(tmp_path, [_l3()])
    good = _disk(p)
    state = Path(p) / ".claude" / "state"
    (state / "diamond-rulings.json").write_text(json.dumps(  # the old record's shape
        {d["id"]: {"sig": dr.signature(d), "scale": d["scale"]} for d in good["active_diamonds"]}))
    (state / "bash-guard").mkdir(parents=True)
    (state / "bash-guard" / "active.yml.before").write_text(yaml.safe_dump(good))
    (Path(p) / AF).write_text("active_diamonds: [broken\n")
    wider = copy.deepcopy(good)
    wider["active_diamonds"] = [{**d, "exposures": [{**d["exposures"][0],
                                                     "audience": "everyone with the link"}]}
                                if d["id"] == "l3-a" else d for d in wider["active_diamonds"]]
    assert any("changes" in v for v in _write(p, wider))
    assert not any("changes" in v for v in _write(p, good)), "control: the repair alone"


def test_the_record_keeps_exposures_json_safe(tmp_path):
    p = _project(tmp_path, [_l3()])
    rec = dr.record(Path(p), "s1")
    json.dumps(rec)  # dates from YAML must not break the record
    assert rec["l3-a"]["exposures"][0]["audience"] == RUNNING["audience"]


# P16, closed fail-closed (v0.307.9, DL-1371) --------------------------------------------------

def _old_record_and_break(p: str) -> dict:
    """A rulings record from before 0.307.7 (no exposures), no snapshot, no commit, and the file
    broken outside any shell command: the residual 0.307.7 left."""
    good = _disk(p)
    (Path(p) / ".claude" / "state" / "diamond-rulings.json").write_text(json.dumps(
        {d["id"]: {"sig": dr.signature(d), "scale": d["scale"]} for d in good["active_diamonds"]}))
    (Path(p) / AF).write_text("active_diamonds: [broken\n")
    return good


def test_a_repair_that_cannot_see_an_l3s_exposures_is_refused_for_it(tmp_path):
    p = _project(tmp_path, [_l3()])
    good = _old_record_and_break(p)
    wider = copy.deepcopy(good)
    wider["active_diamonds"] = [{**d, "exposures": [{**d["exposures"][0],
                                                     "audience": "everyone with the link"}]}
                                if d["id"] == "l3-a" else d for d in wider["active_diamonds"]]
    for doc in (wider, good, _without(good, "l3-a")):  # widened, unchanged, removed
        out = _write(p, doc)
        assert any("cannot be checked" in v and "l3-a" in v for v in out), out


def test_control_the_remedy_repairs_without_the_exposures_first(tmp_path):
    p = _project(tmp_path, [_l3()])
    good = _old_record_and_break(p)
    bare = copy.deepcopy(good)
    bare["active_diamonds"] = [{k: v for k, v in d.items() if k != "exposures"}
                               for d in bare["active_diamonds"]]
    assert not any("cannot be checked" in v for v in _write(p, bare)), "the repair alone passes"


def test_control_a_new_record_knows_an_l3_with_no_exposures(tmp_path):
    l3 = {k: v for k, v in _l3().items() if k != "exposures"}
    p = _project(tmp_path, [l3])
    rec = dr.record(Path(p), "s1")
    assert rec["l3-a"]["exposures"] == [], "an empty list says it has none; absence is unknown"
    good = _disk(p)
    (Path(p) / AF).write_text("active_diamonds: [broken\n")
    assert not any("cannot be checked" in v for v in _write(p, good))
