"""Coverage for check_target_progress (founder ruling 2026-08-31: "target_value: wire it").

THE GAP. `target_value` sat beside `current_value` in the canvas and NOTHING read either —
measured that day across every script and hook. The two halves of a measurement were adjacent
in the same object and the gap between them was never computed. A target beside an actual
LOOKS like a measurement while none is happening.

WAYS THIS COULD ROT:
  1. THE MIDDLE STATE DISAPPEARS. "target set, never measured" is the finding; collapsing it
     into n/a would make the check report clean over exactly the population it exists for.
  2. SKIPS GO SILENT. A prose target must be reported as skipped WITH a reason, or the check
     covers a fraction of its population while printing a pass.
  3. IT PASSES OVER NOTHING. No canvas, or no targets at all, must refuse rather than pass.
"""
import datetime
import importlib.util
import sys
from pathlib import Path

import yaml

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/mycelium/scripts/check_target_progress.py"


def _mod():
    spec = importlib.util.spec_from_file_location("ctp", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["ctp"] = m
    spec.loader.exec_module(m)
    return m


def _canvas(tmp_path, doc):
    d = tmp_path / ".claude" / "canvas"
    d.mkdir(parents=True, exist_ok=True)
    (d / "north-star.yml").write_text(yaml.safe_dump(doc, sort_keys=False))
    return d


def _main(monkeypatch, canvas_dir, *extra):
    import contextlib
    import io
    m = _mod()
    monkeypatch.setattr(sys, "argv", ["check_target_progress.py", "--canvas-dir",
                                      str(canvas_dir), *extra])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = m.main()
    return rc, buf.getvalue()


def test_a_numeric_pair_is_measured_and_the_gap_is_computed(tmp_path):
    m = _mod()
    measured, unmeasured, na = m.scan(
        _canvas(tmp_path, {"name": "shipped", "target_value": 10, "current_value": 4}))
    assert unmeasured == [] and na == []
    assert measured[0][2] == "4 of 10 (40%)"


def test_a_target_never_measured_against_is_the_finding(tmp_path):
    """Rot-mode 1. A target nothing is measured against cannot fail."""
    m = _mod()
    _, unmeasured, _ = m.scan(
        _canvas(tmp_path, {"name": "shipped", "target_value": 10, "current_value": None}))
    assert len(unmeasured) == 1
    assert "null" in unmeasured[0][2]


def test_a_prose_target_is_skipped_with_a_stated_reason(tmp_path):
    """Rot-mode 2. Real canvases carry targets like "100 (3-year, Gilad's band)"."""
    m = _mod()
    _, _, na = m.scan(_canvas(tmp_path, {"name": "stars",
                                         "target_value": {"stars_total": "100 (3-year)"},
                                         "current_value": {"stars_total": 30}}))
    assert len(na) == 1
    assert "cannot be subtracted" in na[0][2]


def test_a_boolean_is_not_a_measurement(tmp_path):
    """True is not 1 here. Subtracting booleans produces a number that means nothing."""
    m = _mod()
    _, _, na = m.scan(
        _canvas(tmp_path, {"name": "done", "target_value": True, "current_value": False}))
    assert len(na) == 1


def test_strict_fails_only_on_the_never_measured_state(tmp_path, monkeypatch):
    d = _canvas(tmp_path, {"name": "shipped", "target_value": 10, "current_value": None})
    assert _main(monkeypatch, d, "--strict")[0] == 1
    d2 = _canvas(tmp_path, {"name": "shipped", "target_value": 10, "current_value": 4})
    assert _main(monkeypatch, d2, "--strict")[0] == 0


def test_report_only_by_default_because_aspirational_targets_are_legitimate(tmp_path, monkeypatch):
    """Failing a build over an unmeasured target teaches people to delete the target rather
    than measure it — the exact inversion the field exists to prevent."""
    d = _canvas(tmp_path, {"name": "shipped", "target_value": 10, "current_value": None})
    rc, out = _main(monkeypatch, d)
    assert rc == 0
    assert "UNMEASURED" in out


def test_no_canvas_is_a_refusal(tmp_path, monkeypatch):
    """Rot-mode 3."""
    rc, out = _main(monkeypatch, tmp_path / "nope", "--strict")
    assert rc == 1
    assert "NOT A PASS" in out


def test_a_canvas_with_no_targets_at_all_refuses_rather_than_passing(tmp_path, monkeypatch):
    """Rot-mode 3, the subtler half: zero targets is not 'everything on target'."""
    d = _canvas(tmp_path, {"name": "nothing here"})
    rc, out = _main(monkeypatch, d, "--strict")
    assert rc == 1
    assert "NOT A PASS" in out


# --- v0.206.0: the freshness pass is independent of the target ----------------------------


def test_freshness_reads_as_of_inside_a_dict_current_value(tmp_path):
    m = _mod()
    d = _canvas(tmp_path, {"input_metrics": [
        {"name": "Waste prevented", "target_value": None,
         "current_value": {"killed": 2, "as_of": "2026-09-02"}},
    ]})
    fresh, stale, undated = m.scan_freshness(d, datetime.date(2026, 9, 14), 30)
    assert [r[1] for r in fresh] == ["Waste prevented"]
    assert "12 days ago" in fresh[0][2]
    assert stale == [] and undated == []


def test_a_metric_with_no_target_can_still_be_stale(tmp_path):
    """The defect: no target meant n/a meant never overdue, so a live metric rotted green."""
    m = _mod()
    d = _canvas(tmp_path, {"input_metrics": [
        {"name": "Waste prevented", "target_value": None,
         "current_value": {"killed": 0, "as_of": "2026-06-18"}},
    ]})
    fresh, stale, undated = m.scan_freshness(d, datetime.date(2026, 9, 14), 30)
    assert [r[1] for r in stale] == ["Waste prevented"]
    assert "88 days ago (limit 30)" in stale[0][2]


def test_an_undated_metric_is_reported_as_unable_to_go_overdue(tmp_path):
    m = _mod()
    d = _canvas(tmp_path, {"input_metrics": [
        {"name": "Adoption", "target_value": 10, "current_value": 3},
        {"name": "Odd", "target_value": 1, "as_of": "not-a-date"},
    ]})
    fresh, stale, undated = m.scan_freshness(d, datetime.date(2026, 9, 14), 30)
    labels = sorted(r[1] for r in undated)
    assert labels == ["Adoption", "Odd"]
    assert any("cannot go overdue" in r[2] for r in undated)
    assert any("unreadable" in r[2] for r in undated)


def test_freshness_is_printed_and_never_fails_strict(tmp_path, monkeypatch):
    d = _canvas(tmp_path, {"input_metrics": [
        {"name": "Old", "target_value": 5, "current_value": {"v": 1, "as_of": "2020-01-01"}},
    ]})
    rc, out = _main(monkeypatch, d, "--strict", "--today", "2026-09-14", "--stale-days", "30")
    assert rc == 0                       # measured against a target; stale is report-only
    assert "1 STALE (> 30 d)" in out
    assert "STALE      [north-star] Old" in out
