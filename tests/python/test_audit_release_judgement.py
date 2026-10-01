"""The release path's judgement, from the 2026-10-01 control audit (DL-1370, batch 1c: K2, F1, F2,
P9). Each gap was reproduced on 0.307.4 before it was fixed; every diamond here records its
decisions directly (founder rule, 2026-10-01).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import scale_locks as sl  # noqa: E402
import test_scale_locks as tsl  # noqa: E402 - the suite's canvas ladder, nothing converted

DEVELOP = [{"decision": d, "on": "2026-09-20"}
           for d in ("set_target", "start_experiment", "commit_to_build")]
RELEASED = [*DEVELOP, {"decision": "release", "on": "2026-09-22"}]
CLOSED = [*RELEASED, {"decision": "close", "on": "2026-09-24"}]


@pytest.fixture(autouse=True)
def _today(monkeypatch):
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-09-25")


def _l3(decisions, **record) -> dict:
    rec = {**tsl.RECORD, **record}
    return {"id": "l3-a", "scale": "L3", "object_ref": "sol-001", "evidence_type": "anecdotal",
            "theory_gates_status": dict(tsl.EXPOSE_PASSED), "decisions": list(decisions),
            "exposures": [{k: v for k, v in rec.items() if v is not None}]}


def _project(tmp_path: Path, diamonds: list[dict], **kw) -> str:
    return tsl._project(tmp_path, purpose=tsl.PURPOSE, opps=tsl._full_opps(), diamonds=diamonds,
                        **kw)


# K2 -------------------------------------------------------------------------------------------

def _doc(**lists) -> str:
    return yaml.safe_dump({"active_diamonds": [], **lists})


L5 = {"id": "l5-a", "scale": "L5"}


@pytest.mark.parametrize("after", [
    _doc(active_diamonds=[{**L5, "decisions": CLOSED}]),
    _doc(completed_diamonds=[{**L5, "decisions": CLOSED}]),
])
def test_closing_an_l5_that_already_delivers_asks_the_person(after):
    """K2: 0.292.0 claimed the floor asks for a move "into deliver or complete"; an L5 already in
    deliver read as already launched, so closing it asked no one."""
    before = _doc(active_diamonds=[{**L5, "decisions": RELEASED}])
    assert sl.launch_moves(before, after) == ["l5-a"]


def test_control_an_edit_that_moves_no_l5_asks_nobody():
    for decisions in (RELEASED, CLOSED):
        before = _doc(active_diamonds=[{**L5, "decisions": decisions}])
        after = _doc(active_diamonds=[{**L5, "decisions": decisions, "confidence": 0.7}])
        assert sl.launch_moves(before, after) == []
    done = _doc(completed_diamonds=[{**L5, "decisions": CLOSED}])
    assert sl.launch_moves(done, done) == [], "already complete, written again"


# F1 -------------------------------------------------------------------------------------------

def test_a_current_exposure_widens_on_the_record_before_release(tmp_path):
    """F1, ruling (b): every widening re-runs the gates. The check ran only once the L3 recorded
    `release`, while an exposure record that is current already lets the work be released."""
    st = sl.State(_project(tmp_path, [_l3(DEVELOP)]))
    before = _l3(DEVELOP)
    assert sl.exposure_state(_project(tmp_path / "x", [before]))[0], "the record is current"
    wider = _l3(DEVELOP, audience="everyone with the link", channel="public link")
    assert st.audience_change_missing(before, wider)


def test_a_started_exposure_widens_on_the_record_before_release(tmp_path):
    st = sl.State(_project(tmp_path, [_l3(DEVELOP, started="2026-09-21")]))
    before = _l3(DEVELOP, started="2026-09-21", consent=None)  # not current, but people are in it
    wider = _l3(DEVELOP, started="2026-09-21", consent=None, until="2027-02-01")
    assert st.audience_change_missing(before, wider)


def test_control_a_plan_that_reaches_nobody_is_not_a_widening(tmp_path):
    """A record that is neither current nor started is a plan (the 0b-2 re-model: refusing a
    recorded audience on an L3 still planning would block planning)."""
    st = sl.State(_project(tmp_path, [_l3(DEVELOP, consent=None)]))
    before = _l3(DEVELOP, consent=None)
    assert st.audience_change_missing(before, _l3(DEVELOP, consent=None, audience="two sites")) \
        is None


# F2 -------------------------------------------------------------------------------------------

def test_the_develop_trial_is_an_exposure_and_says_so(tmp_path):
    """F2, ruling (a) (2026-09-30): a moderated trial with named outsiders IS an exposure, with its
    gates sized to the bounded audience; the 0.284.0 carve-out said it was not."""
    l3 = {**_l3(DEVELOP), "exposures": []}
    line = sl.exposure_line(_project(tmp_path, [l3]), {"session_id": "s", "prompt": "morning"},
                            today="2026-09-25")
    assert "not a release" not in line and "Develop's own evidence" not in line, line
    assert "is an exposure" in line and "exposures" in line, line


# P9 -------------------------------------------------------------------------------------------

def _line(p: str, prompt: str = "Tom will deploy it to production tonight") -> str:
    return sl.exposure_line(p, {"session_id": "s", "prompt": prompt}, today="2026-09-25")


@pytest.mark.parametrize("missing", ["consent", "data_class"])
def test_the_prompt_line_speaks_when_the_release_gate_would_refuse(tmp_path, missing):
    """P9: the line judged "ready" by the pre-0.295 diamond rule and stayed silent while the gate
    refused for the record; it is the only guard when someone else deploys."""
    p = _project(tmp_path, [_l3(RELEASED, **{missing: None})])
    assert sl._release_decision(p, "fly deploy")[0] == "deny"
    assert _line(p).startswith("MYCELIUM EXPOSURE STATE"), _line(p)


def test_the_prompt_line_speaks_for_an_l4_with_no_record(tmp_path):
    l3 = {**_l3(CLOSED), "exposures": [{**tsl.RECORD, "ended": {
        "how": "handed_to_l4", "on": "2026-09-24", "l4": "l4-a"}}]}
    l4 = {"id": "l4-a", "scale": "L4", "parent": "l3-a", "object_ref": "sol-001",
          "theory_gates_status": dict(tsl.EXPOSE_PASSED), "decisions": list(RELEASED)}
    # The user's ack waives the L4's chain (its L3 is at anecdotal), so the record is the only
    # thing missing; without the ack the line spoke for the lock, and showed nothing.
    p = _project(tmp_path, [l3, l4], ack="l4-a L4 2026-09-25 user: ship it, my call\n")
    assert sl._release_decision(p, "fly deploy")[0] == "deny", "the gate refuses: no record"
    assert _line(p).startswith("MYCELIUM EXPOSURE STATE"), _line(p)


def test_the_change_line_speaks_when_a_record_stops_being_current(tmp_path):
    p = _project(tmp_path, [_l3(RELEASED)])
    assert sl.exposure_change_line(p) == "", "the first reading sets the baseline"
    active = Path(p) / ".claude" / "diamonds" / "active.yml"
    doc = yaml.safe_load(active.read_text())
    doc["active_diamonds"] = [{**d, "exposures": [{**d["exposures"][0], "consent": None}]}
                              if d["id"] == "l3-a" else d for d in doc["active_diamonds"]]
    active.write_text(yaml.safe_dump(doc))
    assert sl.exposure_change_line(p).startswith("MYCELIUM EXPOSURE STATE CHANGED")


def test_control_the_prompt_line_is_silent_under_a_current_record(tmp_path):
    p = _project(tmp_path, [_l3(RELEASED)])
    assert sl._release_decision(p, "fly deploy") is None, "the gate allows"
    assert _line(p) == ""
