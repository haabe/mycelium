""""Evidence since the last assessment" is judged on one clock, to the second (v0.250.0).

E2E run 19: the delivering L3 was ruled on with a typed world date (2026-09-26) that the file clock
(2026-09-24) never reached, so a month of pilot evidence never made next_item propose it. The same
comparison fails in ordinary use: evidence landing later on the day of a ruling is never "since" it,
and a typed date ahead of the machine's silences the diamond. scripts/diamond_rulings.py records the
machine time of each assessment at the write; next_item compares that with file times and ignores
files the ruling session wrote itself.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "plugins" / "mycelium" / "scripts"
sys.path.insert(0, str(SCRIPTS))


def _mod(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


dr = _mod("diamond_rulings")
ni = _mod("next_item")

L3 = """\
active_diamonds:
  - id: l3-x
    scale: L3
    phase: deliver
    progression_ruled_at: "{ruled}"
"""


def _project(tmp_path: Path, ruled: str) -> Path:
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    (tmp_path / ".claude" / "canvas").mkdir(parents=True)
    (tmp_path / "research").mkdir()
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text(L3.format(ruled=ruled))
    return tmp_path


def _at(path: Path, when: dt.datetime, text: str = "x") -> None:
    path.write_text(text)
    os.utime(path, (when.timestamp(), when.timestamp()))


def _rule(root: Path, when: dt.datetime, session: str = "s-rule") -> None:
    """A ruling as the hook records it: first sight, then a change at `when`."""
    dr.record(root, "s0", now="2000-01-01T00:00:00+00:00")
    active = root / ".claude" / "diamonds" / "active.yml"
    active.write_text(active.read_text().replace("progression_ruled_at", "progression_history: [{}]\n"
                                                 "    progression_ruled_at"))
    dr.record(root, session, now=when.isoformat())


NOW = dt.datetime(2026, 9, 24, 10, 0, tzinfo=dt.UTC)


def test_evidence_later_the_same_day_is_since_the_ruling(tmp_path):
    root = _project(tmp_path, "2026-09-24")
    _rule(root, NOW)
    _at(root / "research" / "pilot.md", NOW + dt.timedelta(hours=5))
    items = ni._unassessed(root, "2026-09-24")
    assert [i["diamond"] for i in items] == ["l3-x"]
    assert "1 new evidence entry since" in items[0]["text"]


def test_a_typed_date_ahead_of_the_clock_does_not_silence_it(tmp_path):
    root = _project(tmp_path, "2026-10-26")  # the world date run 19 typed
    _rule(root, NOW)
    _at(root / "research" / "pilot.md", NOW + dt.timedelta(days=1))
    assert [i["diamond"] for i in ni._unassessed(root, "2026-09-25")] == ["l3-x"]


def test_files_the_ruling_session_wrote_do_not_count(tmp_path):
    root = _project(tmp_path, "2026-09-24")
    _rule(root, NOW, session="s-rule")
    note = root / ".claude" / "canvas" / "opportunities.yml"
    _at(note, NOW + dt.timedelta(minutes=2))
    (root / ".claude" / "state" / "change-log.jsonl").write_text(
        json.dumps({"file_path": str(note), "session_id": "s-rule"}) + "\n")
    assert ni._unassessed(root, "2026-09-24") == []


def test_nothing_since_the_ruling_is_quiet(tmp_path):
    root = _project(tmp_path, "2026-09-24")
    _at(root / "research" / "old.md", NOW - dt.timedelta(hours=1))
    _rule(root, NOW)
    assert ni._unassessed(root, "2026-09-24") == []


def test_a_diamond_first_seen_already_ruled_has_no_known_time(tmp_path):
    root = _project(tmp_path, "2026-09-20")
    rec = dr.record(root, "s1", now=NOW.isoformat())
    assert rec["l3-x"]["ts"] is None  # when it was ruled is unknown; the typed date is used


def test_the_recorder_runs_from_the_hook_payload(tmp_path, monkeypatch):
    import io
    root = _project(tmp_path, "")
    active = root / ".claude" / "diamonds" / "active.yml"
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(
        {"session_id": "s1", "tool_input": {"file_path": str(active)}})))
    assert dr.main() == 0
    rec = dr.load(root)
    assert rec["l3-x"]["session"] == "s1" and rec["l3-x"]["ts"] is None  # first sight: no time


def test_the_recorder_ignores_other_payloads(tmp_path, monkeypatch):
    import io
    for payload in ("not json", "[]", json.dumps({"tool_input": {"file_path": "x/canvas/a.yml"}})):
        monkeypatch.setattr("sys.stdin", io.StringIO(payload))
        assert dr.main() == 0


def test_the_recorder_survives_a_missing_or_broken_file(tmp_path):
    assert dr.record(tmp_path, "s1") == {}
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text("a: [unclosed\n")
    assert dr.record(tmp_path, "s1") == {}
    (tmp_path / ".claude" / "state").mkdir()
    (tmp_path / ".claude" / "state" / "diamond-rulings.json").write_text("[1, 2]")
    assert dr.load(tmp_path) == {}


def test_an_unchanged_diamond_keeps_its_recorded_time(tmp_path):
    root = _project(tmp_path, "2026-09-24")
    _rule(root, NOW)
    again = dr.record(root, "s-later", now=(NOW + dt.timedelta(days=3)).isoformat())
    assert again["l3-x"]["ts"] == NOW.isoformat() and again["l3-x"]["session"] == "s-rule"


def test_a_never_assessed_diamond_stays_never_assessed_after_the_recorder_sees_it(tmp_path):
    """v0.250.2: 0.250.0 stamped first sight as an assessment, which hid a never-ruled diamond."""
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text(
        "active_diamonds:\n  - id: l0-x\n    scale: L0\n    phase: discover\n")
    dr.record(tmp_path, "s1", now=NOW.isoformat())
    items = ni._unassessed(tmp_path, "2026-09-24")
    assert [i["diamond"] for i in items] == ["l0-x"]
    assert "has never been assessed" in items[0]["text"]
