"""prune_state_logs.py: activity logs keep 90 days by default, decisions are kept (v0.318.0).

Founder ruling 2026-10-10, after Anthropic's plugin directory review of v0.317.4 asked how long
each log is kept: trimmed by default, for a number of days MYCELIUM_LOG_RETENTION_DAYS changes.
"""

from __future__ import annotations

import datetime as _dt
import importlib.util
import json
import os
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ps = _load("prune_state_logs")
rr = _load("reconcile_reflexions")
NOW = _dt.datetime(2026, 10, 10, 12, 0, tzinfo=_dt.UTC)


def _iso(days_ago: int) -> str:
    return (NOW - _dt.timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join((r if isinstance(r, str) else json.dumps(r)) + "\n" for r in rows))


def _rows(path: Path) -> list[str]:
    return path.read_text().splitlines()


@pytest.mark.parametrize(("raw", "days"), [
    ("", 90), ("30", 30), ("0", 0), ("off", 0), ("never", 0), ("-5", 90), ("soon", 90)])
def test_the_flag_sets_the_days(raw, days):
    assert ps.retention_days({ps.ENV: raw}) == days


def test_old_activity_lines_go_and_recent_and_undated_ones_stay(tmp_path):
    state = tmp_path / ".claude" / "state"
    _write(state / "read-log.jsonl", [{"ts": _iso(120), "file_path": "old"}, {"ts": _iso(10), "file_path": "new"},
                                      {"file_path": "undated"}, "{torn"])
    _write(state / "shell-safety-guard-log.jsonl", [{"at": _iso(91)}, {"at": _iso(89)}])
    _write(state / "scale-lock-fires.jsonl", [{"ts": "2026-06-01T00:00:00+00:00"}])
    report = ps.prune(state, 90, now=NOW)
    assert report == {"read-log.jsonl": 1, "scale-lock-fires.jsonl": 1, "shell-safety-guard-log.jsonl": 1}
    assert [json.loads(x).get("file_path") for x in _rows(state / "read-log.jsonl")[:2]] == ["new", "undated"]
    assert "{torn" in _rows(state / "read-log.jsonl")


def test_decision_records_are_never_trimmed(tmp_path):
    state = tmp_path / ".claude" / "state"
    for name in ("advisory-ledger.jsonl", "reflexion-dismissed.jsonl", "exposure-uses.jsonl",
                 "skip-ack-uses.jsonl", "next-item-log.jsonl"):
        _write(state / name, [{"ts": _iso(400)}])
    assert ps.prune(state, 90, now=NOW) == {}
    assert all(len(_rows(p)) == 1 for p in state.glob("*.jsonl"))


def test_zero_days_keeps_everything_and_writes_nothing(tmp_path):
    state = tmp_path / ".claude" / "state"
    _write(state / "read-log.jsonl", [{"ts": _iso(999)}])
    assert ps.prune(state, 0, now=NOW) == {}
    assert not (state / ps.STAMP).exists()


def test_it_runs_at_most_once_a_day_unless_forced(tmp_path):
    state = tmp_path / ".claude" / "state"
    _write(state / "read-log.jsonl", [{"ts": _iso(200)}])
    (state / ps.STAMP).touch()
    assert ps.prune(state, 90) == {}
    assert ps.prune(state, 90, force=True) == {"read-log.jsonl": 1}
    stamp = state / ps.STAMP
    old = (NOW - _dt.timedelta(days=2)).timestamp()
    os.utime(stamp, (old, old))
    assert ps._due(state, NOW)


def test_trimmed_reflexions_still_count_as_fired(tmp_path):
    """Three old firings, two answered; one new unanswered. Trimming the old three must leave the
    new one outstanding, not hide it behind the two old credits."""
    state = tmp_path / ".claude" / "state"
    (tmp_path / ".claude" / "memory").mkdir(parents=True)
    (tmp_path / ".claude" / "memory" / "corrections.md").write_text("# Corrections\n")
    _write(state / "reflexion-log.jsonl", [{"ts": _iso(200)}, {"ts": _iso(150)}, {"ts": _iso(120)},
                                           {"ts": _iso(130), "suppressed": "grep exit 1"}, {"ts": _iso(1)}])
    (state / "reflexion-ledger.json").write_text(json.dumps({"credited": 2, "corrections_baseline": 0}))
    before = rr.status(tmp_path)["outstanding"]
    ps.prune(state, 90, now=NOW)
    assert json.loads((state / "reflexion-ledger.json").read_text())["pruned_fired"] == 3
    after = rr.status(tmp_path)
    assert before == after["outstanding"] == 2
    assert len(_rows(state / "reflexion-log.jsonl")) == 1


def test_rebaseline_keeps_the_pruned_count(tmp_path, capsys):
    state = tmp_path / ".claude" / "state"
    _write(state / "reflexion-log.jsonl", [{"ts": _iso(1)}])
    (state / "reflexion-ledger.json").write_text(json.dumps({"credited": 0, "corrections_baseline": 0,
                                                             "pruned_fired": 4}))
    rr.rebaseline(tmp_path)
    ledger = json.loads((state / "reflexion-ledger.json").read_text())
    assert ledger["credited"] == 5 and ledger["pruned_fired"] == 4
    assert rr.status(tmp_path)["outstanding"] == 0


def test_cli_reports_and_never_fails(tmp_path, capsys, monkeypatch):
    state = tmp_path / ".claude" / "state"
    _write(state / "change-log.jsonl", [{"ts": "2020-01-01T00:00:00Z"}])
    monkeypatch.setenv(ps.ENV, "30")
    assert ps.main(["--state-dir", str(state), "--force"]) == 0
    assert "change-log.jsonl: 1 line(s) older than 30 days removed" in capsys.readouterr().out
    assert ps.main(["--state-dir", str(tmp_path / "missing")]) == 0
