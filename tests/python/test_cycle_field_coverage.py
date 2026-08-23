"""Coverage for check_cycle_recording.cycle_field_coverage (v0.121.0).

WHY THIS EXISTS. `engine/cycle-learning.md` specifies `gates_fired` and `regressions` on
every cycle record, each with a comment naming the `/framework-health` dimension it
closes. `/mycelium:retrospective` instructs writing them and cites anti-pattern #9 by
number. Measured on a real project 2026-08-23: **zero of sixteen records carried either
field**, including one written the same day its cycle closed. A rule in prose, with no
schema and no check behind it, moved nothing.

THE THREE WAYS THIS CHECK COULD ROT, AND THE TESTS THAT STOP THEM:

  1. IT TREATS A RECORDED ZERO AS A MISS. `gates_fired: []` and `in_cycle_count: 0` are
     measurements — the cycle ran and nothing fired. If the check flagged those, authors
     would learn that recording an honest zero is punished, which is the opposite of the
     behaviour it exists to produce.
  2. IT ALARMS ON EVIDENCE THAT CANNOT EXIST YET. `rework` is populated on a 14-day lag by
     design. Counting a cycle that closed on Tuesday as missing it is the failure this
     project logged as "absence is only a finding once it could have been filled".
  3. IT BREAKS THE VALIDATOR. A coverage report that raises on a malformed file is worse
     than one with a gap — it takes the whole canvas check down with it.
"""
import datetime
import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/mycelium/scripts/check_cycle_recording.py"
TODAY = datetime.date(2026, 8, 23)


def _mod():
    spec = importlib.util.spec_from_file_location("ccr_cov", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["ccr_cov"] = m
    spec.loader.exec_module(m)
    return m


def _write(tmp_path, cycles):
    f = tmp_path / "cycle-history.yml"
    f.write_text(yaml.safe_dump({"cycles": cycles}, sort_keys=False))
    return f


def _cycle(**kw):
    base = {
        "cycle_id": "cycle-001", "leaf_id": "l", "opportunity_id": "o",
        "started_at": "2026-01-01", "completed_at": "2026-01-10",
        "terminal_state": "launched", "cycle_class": "meta-dogfood",
    }
    base.update(kw)
    return base


def test_absent_fields_are_reported(tmp_path):
    out = _mod().cycle_field_coverage(_write(tmp_path, [_cycle()]), today=TODAY)
    joined = " ".join(out)
    assert "gates_fired" in joined
    assert "regressions" in joined
    assert "rework" in joined


def test_a_recorded_zero_is_not_a_miss(tmp_path):
    """Rule 1. An honest empty measurement must never be flagged."""
    c = _cycle(gates_fired=[], regressions={"in_cycle_count": 0},
               rework={"post_delivery_corrections": 0})
    assert _mod().cycle_field_coverage(_write(tmp_path, [c]), today=TODAY) == []


def test_recent_cycles_are_excluded_from_the_rework_denominator(tmp_path):
    """Rule 2. Closed three days ago — the field cannot exist yet."""
    c = _cycle(completed_at="2026-08-20", gates_fired=[], regressions={"in_cycle_count": 0})
    assert _mod().cycle_field_coverage(_write(tmp_path, [c]), today=TODAY) == []


def test_an_old_cycle_missing_rework_is_reported(tmp_path):
    c = _cycle(completed_at="2026-07-01", gates_fired=[], regressions={"in_cycle_count": 0})
    out = _mod().cycle_field_coverage(_write(tmp_path, [c]), today=TODAY)
    assert len(out) == 1 and "rework" in out[0]


def test_in_flight_cycles_are_not_counted(tmp_path):
    """An open cycle has not had the chance to record an outcome."""
    c = _cycle(terminal_state="in_flight", completed_at=None)
    assert _mod().cycle_field_coverage(_write(tmp_path, [c]), today=TODAY) == []


def test_the_report_names_the_denominator(tmp_path):
    """A bare count is unactionable; 3 of 3 and 3 of 40 are different findings."""
    cycles = [_cycle(cycle_id=f"cycle-{i:03d}") for i in range(1, 4)]
    out = _mod().cycle_field_coverage(_write(tmp_path, cycles), today=TODAY)
    assert "3 of 3" in out[0]
    assert "cycle-001" in out[0] and "cycle-003" in out[0]


def test_unparseable_file_returns_no_findings_and_does_not_raise(tmp_path):
    """Rule 3."""
    f = tmp_path / "cycle-history.yml"
    f.write_text("cycles: [oops\n")
    assert _mod().cycle_field_coverage(f, today=TODAY) == []


def test_empty_and_missing_cycle_lists_are_silent(tmp_path):
    f = tmp_path / "cycle-history.yml"
    f.write_text(yaml.safe_dump({"cycles": []}))
    assert _mod().cycle_field_coverage(f, today=TODAY) == []
    f.write_text(yaml.safe_dump({"schema_version": 1}))
    assert _mod().cycle_field_coverage(f, today=TODAY) == []


def test_undated_cycles_are_skipped_and_the_skip_is_reported(tmp_path):
    """Silently dropping them would shrink the denominator without saying so."""
    c = _cycle(completed_at="not-a-date", gates_fired=[], regressions={"in_cycle_count": 0})
    out = _mod().cycle_field_coverage(_write(tmp_path, [c]), today=TODAY)
    assert out == [] or "unreadable completed_at" in out[0]
