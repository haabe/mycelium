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
    assert "demand_type" in joined


def test_demand_type_absence_is_reported_like_its_siblings(tmp_path):
    """v0.130.0. demand_type shipped in v0.129.0 WITH its consumer — the fix for the
    producer-without-reader defect — but WITHOUT the absence WARN gates_fired and
    regressions carry. A field that goes quiet when unpopulated is how 0-of-16
    compliance survives for months, so the asymmetry is pinned here."""
    c = _cycle(gates_fired=[], regressions={"in_cycle_count": 0},
               rework={"post_delivery_corrections": 0})
    out = _mod().cycle_field_coverage(_write(tmp_path, [c]), today=TODAY)
    assert len(out) == 1
    assert "demand_type" in out[0]
    assert "Demand mix" in out[0]


def test_a_recorded_zero_is_not_a_miss(tmp_path):
    """Rule 1. An honest empty measurement must never be flagged."""
    c = _cycle(gates_fired=[], regressions={"in_cycle_count": 0},
               rework={"post_delivery_corrections": 0}, demand_type="value")
    assert _mod().cycle_field_coverage(_write(tmp_path, [c]), today=TODAY) == []


def test_recent_cycles_are_excluded_from_the_rework_denominator(tmp_path):
    """Rule 2. Closed three days ago — the field cannot exist yet."""
    c = _cycle(completed_at="2026-08-20", gates_fired=[], regressions={"in_cycle_count": 0},
               demand_type="value")
    assert _mod().cycle_field_coverage(_write(tmp_path, [c]), today=TODAY) == []


def test_an_old_cycle_missing_rework_is_reported(tmp_path):
    c = _cycle(completed_at="2026-07-01", gates_fired=[], regressions={"in_cycle_count": 0},
               demand_type="value")
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
    c = _cycle(completed_at="not-a-date", gates_fired=[], regressions={"in_cycle_count": 0},
               demand_type="value")
    out = _mod().cycle_field_coverage(_write(tmp_path, [c]), today=TODAY)
    assert out == [] or "unreadable completed_at" in out[0]


# --- rot mode 4: it alarms on an observation nobody could have made (v0.161.0) ---
#
# The same shape as rot mode 2 above, one step further out. Mode 2 is "the evidence cannot
# exist YET"; this is "the evidence was never captured and cannot be recovered". A
# reconstructed record backfills work that shipped before the trigger existed, so nobody was
# watching which gates fired. engine/cycle-learning.md already exempts these records from every
# calibration aggregate; this extends that to the two OBSERVATIONAL fields for the same stated
# reason, and the doc records the extension.

def test_a_reconstructed_record_is_exempt_from_the_observational_fields(tmp_path):
    """gates_fired/regressions/rework were never observed on a backfilled arc.

    Writing `gates_fired: []` there would not record a measurement — it would add a fabricated
    zero to framework-health's denominator and deflate measured gate effectiveness.
    """
    c = _cycle(reconstructed_post_hoc=True)
    out = _mod().cycle_field_coverage(_write(tmp_path, [c]), today=TODAY)
    joined = " ".join(out)
    for field in ("gates_fired", "regressions", "rework"):
        assert field not in joined, f"{field} must be exempt on a reconstructed record"


def test_demand_type_is_not_exempt_on_a_reconstructed_record(tmp_path):
    """The exemption is per-field, not per-record, and this is the line it draws.

    Seddon's demand_type classifies WHY the work was asked for, not what was observed while it
    ran. That stays determinable from the record long afterwards — the dogfood project filled it
    on three reconstructed cycles from the opportunity they traced to. Exempting a whole record
    would have silently lost that.
    """
    c = _cycle(reconstructed_post_hoc=True)
    out = " ".join(_mod().cycle_field_coverage(_write(tmp_path, [c]), today=TODAY))
    assert "demand_type" in out


def test_the_exemption_does_not_silence_an_ordinary_gap(tmp_path):
    """The whole risk of an exemption is that it hides the case the check exists for."""
    out = _mod().cycle_field_coverage(_write(tmp_path, [_cycle()]), today=TODAY)
    joined = " ".join(out)
    for field in ("gates_fired", "regressions", "demand_type", "rework"):
        assert field in joined, f"{field} must still be reported on an observed cycle"


def test_the_count_says_how_many_records_were_excluded(tmp_path):
    """A coverage number that quietly shrinks its own population is the defect this repo keeps
    finding. If records are dropped, the line must say so."""
    cycles = [_cycle(cycle_id="obs"), _cycle(cycle_id="recon", reconstructed_post_hoc=True)]
    out = " ".join(_mod().cycle_field_coverage(_write(tmp_path, cycles), today=TODAY))
    assert "1 reconstructed record(s) are excluded" in out
    assert "1 of 1 closed cycles carry no `gates_fired`" in out, (
        "the denominator must be the OBSERVED population, not the whole file"
    )
