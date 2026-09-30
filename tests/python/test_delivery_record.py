"""An L3's learning delivery can be recorded as an exposure (v0.296.0, phase migration stage 2b).

One record, not two: every rule on an L3's learning delivery (its fields, its end date, how it
ended, a change to its audience, end date, channel or data) reads `learning_delivery` when the
diamond carries it and the exposure record otherwise. Recording an exposure is not a start.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import next_item  # noqa: E402
import scale_locks as sl  # noqa: E402

EXPOSURE = {"recorded_at": "2026-10-01", "audience": "Harbour staff, opted in",
            "channel": "moderated session", "data_class": "none", "until": "2026-10-25",
            "consent": "signed pilot note"}


def _l3(phase: str = "deliver", **extra) -> dict:
    return {"id": "l3-a", "scale": "L3", "phase": phase, **extra}


def test_an_exposure_record_is_the_learning_delivery(tmp_path, monkeypatch):
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-10-05")
    state = sl.State(str(tmp_path))
    assert state.learning_delivery_missing(_l3(exposures=[EXPOSURE])) == []
    assert state.learning_delivery_recorded(_l3(exposures=[EXPOSURE])) is None
    out = state.learning_delivery_missing(_l3())
    assert out and "audience, until, means" in out[0], "control: nothing recorded"


def test_an_exposure_past_its_end_date_is_still_running(tmp_path, monkeypatch):
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-10-26")
    out = sl.State(str(tmp_path)).learning_delivery_missing(_l3(exposures=[EXPOSURE]))
    assert out and "`exposures[].until`" in out[0] and "still running" in out[0]


def test_recording_an_exposure_is_not_a_start():
    assert sl._reaches_people(_l3("develop", exposures=[EXPOSURE])) == ""
    started = {**EXPOSURE, "started": "2026-10-02"}
    assert sl._reaches_people(_l3("develop", exposures=[started])) != ""


def test_how_an_exposure_ended_is_read_by_the_l3s_end_rule(tmp_path, monkeypatch):
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-10-30")
    state = sl.State(str(tmp_path))
    withdrawn = {**EXPOSURE, "ended": {"how": "withdrawn", "on": "2026-10-25"}}
    assert state.learning_delivery_end_missing(_l3("complete", exposures=[withdrawn])) is None
    dated = {**EXPOSURE, "ended": "2026-10-25"}
    why = state.learning_delivery_end_missing(_l3("complete", exposures=[dated]))
    assert why and "`exposures[].ended" in why and "`how`" in why


def test_a_change_to_an_exposure_is_on_the_record(tmp_path):
    state = sl.State(str(tmp_path))
    before = _l3(exposures=[EXPOSURE])
    wider = {**EXPOSURE, "audience": "Harbour and Quay staff, opted in"}
    why = state.audience_change_missing(before, _l3(exposures=[wider]))
    assert why and "`exposures[].changes`" in why
    entry = {"on": "2026-10-10", "audience_was": EXPOSURE["audience"], "kind": "widened",
             "reassessed": ["security", "privacy", "service_quality"]}
    assert state.audience_change_missing(before, _l3(exposures=[{**wider, "changes": [entry]}])) \
        is None
    personal = {**EXPOSURE, "data_class": "personal"}
    why = state.audience_change_missing(before, _l3(exposures=[personal]))
    assert why and "data" in why and "data_was" in why, "more data is a widening"


def test_learning_delivery_wins_when_both_are_recorded():
    ld = {"audience": "five testers", "until": "2026-11-01", "means": "by hand"}
    view = sl.delivery_of(_l3(learning_delivery=ld, exposures=[EXPOSURE]))
    assert view == ld
    assert sl.delivery_key(_l3(learning_delivery=ld, exposures=[EXPOSURE]), "until") \
        == "learning_delivery.until"


def test_the_running_exposure_is_read_before_an_ended_one():
    old = {**EXPOSURE, "recorded_at": "2026-10-20", "audience": "first wave",
           "ended": {"how": "withdrawn", "on": "2026-10-21"}}
    assert sl.delivery_of(_l3(exposures=[old, EXPOSURE]))["audience"] == EXPOSURE["audience"]


def test_next_item_reads_the_same_record(monkeypatch):
    assert next_item._ld(_l3(exposures=[EXPOSURE]))["means"] == "moderated session"
    monkeypatch.setattr(next_item, "sl", None)
    ld = {"audience": "five testers"}
    assert next_item._ld(_l3(learning_delivery=ld)) == ld, "without scale_locks: the field"
