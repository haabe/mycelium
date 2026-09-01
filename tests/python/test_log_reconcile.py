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


# --- canvas-to-canvas: killed leaves with no cycle row -----------------------
# Measured 2026-09-01: archived-solutions.yml held THREE killed leaves (all
# archived_at 2026-08-16, reason failed-assumption, each with ICE at archive and a
# decision-log ref) while cycle-history.yml reported 16 launched and ZERO killed. Nothing
# compared the two surfaces, so a reader saw a 0% discard rate and concluded nothing is
# ever killed — which an agent did, and wrote up as a finding, before opening the archive.


def _two_canvases(tmp_path, archived: str, cycles: str):
    d = tmp_path / ".claude" / "canvas"
    d.mkdir(parents=True, exist_ok=True)
    (d / "archived-solutions.yml").write_text(archived)
    (d / "cycle-history.yml").write_text(cycles)
    h = tmp_path / ".claude" / "harness"
    h.mkdir(parents=True, exist_ok=True)
    (h / "decision-log.md").write_text("# log\n")
    return tmp_path


def test_an_archived_leaf_with_no_cycle_row_is_an_orphan(tmp_path):
    root = _two_canvases(tmp_path,
                         'archived:\n  - leaf_id: sol-047a\n    archived_at: "2026-08-16"\n',
                         "cycles:\n  - leaf_id: meta-something\n    terminal_state: launched\n")
    res = clr.analyse(root)
    assert any("sol-047a" in o[2] for o in res["orphans"]), res


def test_the_first_field_on_a_dash_line_is_found(tmp_path):
    """The extractor originally anchored on whitespace alone and matched NOTHING, because
    the first field of a YAML list item sits on the `- ` line. The class then reported
    'absent or empty' over a file holding three entries — a silent false pass, caught only
    because the number looked wrong."""
    d = tmp_path / ".claude" / "canvas"
    d.mkdir(parents=True, exist_ok=True)
    (d / "archived-solutions.yml").write_text(
        "archived:\n  - leaf_id: sol-047a\n    reason: failed-assumption\n")
    vals = clr._block_field_values(d / "archived-solutions.yml", "archived", "leaf_id")
    assert vals == {"sol-047a"}


def test_a_matching_cycle_row_clears_it(tmp_path):
    root = _two_canvases(tmp_path,
                         "archived:\n  - leaf_id: sol-047a\n",
                         "cycles:\n  - leaf_id: sol-047a\n    terminal_state: killed\n")
    res = clr.analyse(root)
    assert not [o for o in res["orphans"] if "killed leaves" in o[0]], res


def test_an_empty_archive_is_skipped_not_passed(tmp_path):
    """A consumer that has never archived anything must not read as reconciled."""
    root = _two_canvases(tmp_path, "archived: []\n", "cycles: []\n")
    res = clr.analyse(root)
    assert any("killed leaves" in s[0] for s in res["skipped"]), res


def test_a_list_item_at_the_same_indent_as_its_key_stays_in_the_block(tmp_path):
    """YAML permits `cycles:` at column 0 with `- cycle_id:` also at column 0, and
    cycle-history.yml is written that way. Breaking on indent alone ended the scan on the
    first item and returned an EMPTY SET, so every source id read as missing — the check
    reported three archived leaves as orphaned when two had just been recorded."""
    d = tmp_path / ".claude" / "canvas"
    d.mkdir(parents=True, exist_ok=True)
    (d / "cycle-history.yml").write_text(
        "cycles:\n- cycle_id: cycle-001\n  leaf_id: sol-047a\n- cycle_id: cycle-002\n"
        "  leaf_id: sol-047d\n")
    assert clr._block_field_values(d / "cycle-history.yml", "cycles", "leaf_id") == {
        "sol-047a", "sol-047d"}


def test_a_comment_between_items_does_not_end_the_block(tmp_path):
    """Canvases carry comment banners between list items. A `#` at the key's indent is not a
    sibling key — treating it as one ended the scan before the entries below it."""
    d = tmp_path / ".claude" / "canvas"
    d.mkdir(parents=True, exist_ok=True)
    (d / "cycle-history.yml").write_text(
        "cycles:\n- cycle_id: cycle-001\n  leaf_id: sol-old\n"
        "# a banner explaining what follows\n"
        "- cycle_id: cycle-002\n  leaf_id: sol-new\n")
    assert clr._block_field_values(d / "cycle-history.yml", "cycles", "leaf_id") == {
        "sol-old", "sol-new"}


def test_a_sibling_key_does_end_the_block(tmp_path):
    """The break must still work, or the scan runs into the next top-level section."""
    d = tmp_path / ".claude" / "canvas"
    d.mkdir(parents=True, exist_ok=True)
    (d / "cycle-history.yml").write_text(
        "cycles:\n- cycle_id: cycle-001\n  leaf_id: sol-in\n"
        "calibration_summary:\n  leaf_id: sol-out\n")
    assert clr._block_field_values(d / "cycle-history.yml", "cycles", "leaf_id") == {"sol-in"}
