"""Coverage proof for check_log_reconcile.py.

THIS GUARD SHIPS GREEN, so its test file carries more weight than usual: the only
evidence it works is here. Measured 2026-08-20 on the dogfood corpus — BVSSH 8 log
events against 14 canvas rows, DORA 3 against 9, zero log-only in either — so the
red path has no real instance and must be proven synthetically or not at all.

Scenario-per-guardpost:
  happy — every dated log event has a canvas row        -> clean, exit 0
  happy — canvas ahead of the log                       -> INFO, never a failure
  happy — neither side has anything                     -> skip, not a pass it did not earn
  sad   — a dated log event with no canvas row          -> ORPHANED, exit 1
  sad   — log events exist, canvas history missing      -> ORPHANED (the original shape)
  bad   — no decision log at all                        -> UNKNOWN, exit 2
  wiring— a deactivated registry row is SKIPPED, not silently dropped
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_MOD = (Path(__file__).resolve().parents[2]
        / "plugins" / "mycelium" / "scripts" / "check_log_reconcile.py")
_spec = importlib.util.spec_from_file_location("check_log_reconcile", _MOD)
clr = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(clr)


def _repo(tmp_path: Path, log: str | None, history: str | None) -> Path:
    if log is not None:
        d = tmp_path / ".claude" / "harness"
        d.mkdir(parents=True)
        (d / "decision-log.md").write_text(log, encoding="utf-8")
    if history is not None:
        c = tmp_path / ".claude" / "canvas"
        c.mkdir(parents=True, exist_ok=True)
        (c / "dora-metrics.yml").write_text(history, encoding="utf-8")
    return tmp_path


DORA_LOG = "### DORA measured, and the real finding was the bookkeeping — 2026-08-09\nbody\n"


def test_matched_event_and_row_is_clean(tmp_path):
    root = _repo(tmp_path, DORA_LOG, "measurement_history:\n  - date: 2026-08-09\n")
    assert not clr.analyse(root)["orphans"]


def test_dated_log_event_without_a_canvas_row_is_orphaned(tmp_path):
    """The 2026-08-09 failure exactly: the measurement was taken, the row was not written."""
    root = _repo(tmp_path, DORA_LOG, "measurement_history:\n  - date: 2026-07-17\n")
    orphans = clr.analyse(root)["orphans"]
    assert orphans and orphans[0][2] == ["2026-08-09"]


def test_missing_canvas_history_with_log_events_is_orphaned(tmp_path):
    """The original BVSSH shape: log events exist and the canvas side does not."""
    root = _repo(tmp_path, DORA_LOG, None)
    orphans = clr.analyse(root)["orphans"]
    assert orphans and "unreadable" in orphans[0][1]


def test_canvas_ahead_of_the_log_is_info_not_failure(tmp_path):
    """Failing this direction would train people to stop writing the canvas."""
    root = _repo(tmp_path, "### unrelated entry — 2026-01-01\n",
                 "measurement_history:\n  - date: 2026-08-09\n  - date: 2026-07-17\n")
    r = clr.analyse(root)
    assert not r["orphans"]
    assert r["info"] and r["info"][0][1] == 2


def test_nothing_on_either_side_is_skipped_not_passed(tmp_path):
    root = _repo(tmp_path, "### unrelated — 2026-01-01\n", None)
    r = clr.analyse(root)
    assert not r["orphans"]
    assert any("no log events" in why for _, why in r["skipped"])


def test_deactivated_row_is_skipped_visibly(tmp_path):
    """A registry row another check owns must be reported, not silently dropped —
    an omitted class reads as an oversight, a deactivated one reads as a decision."""
    root = _repo(tmp_path, DORA_LOG, "measurement_history:\n  - date: 2026-08-09\n")
    skipped = clr.analyse(root)["skipped"]
    assert any("BVSSH" in name for name, _ in skipped)


def test_missing_decision_log_is_unknown_not_clean(tmp_path, monkeypatch):
    """A check that cannot run must never report a pass."""
    monkeypatch.setattr(sys, "argv", ["x", "--root", str(tmp_path)])
    assert clr.main() == 2


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
