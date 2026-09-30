"""Coverage for check_scale_occupancy: records against cycles, per scale."""
import importlib.util
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/mycelium/scripts/check_scale_occupancy.py"


def _mod():
    spec = importlib.util.spec_from_file_location("cso", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["cso"] = m
    spec.loader.exec_module(m)
    return m


def _project(tmp_path, opps, diamonds, outcomes=("out-a",)):
    canvas = tmp_path / ".claude" / "canvas"
    canvas.mkdir(parents=True)
    doc = {"desired_outcomes": [{"id": o, "metric": o} for o in outcomes], "opportunities": opps}
    (canvas / "opportunities.yml").write_text(yaml.safe_dump(doc))
    (tmp_path / ".claude" / "diamonds").mkdir()
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text(yaml.safe_dump(diamonds))
    return canvas


def test_records_are_outcomes_and_chosen_targets(tmp_path):
    """v0.302.0 (DL-1367): an L2 opens on an outcome and an L3 on an L2's target. Many
    opportunities under one L2, and many ideas under one L3, are the model, not a backlog."""
    m = _mod()
    canvas = _project(tmp_path, [
        {"id": "opp-1", "solutions": [{"id": "sol-1"}, {"id": "sol-2"}]}, {"id": "opp-2"},
    ], {"active_diamonds": [{"id": "l1", "scale": "L1"},
                            {"id": "l2", "scale": "L2", "target": {"opportunity": "opp-1"}}],
        "completed_diamonds": [{"id": "l2-done", "scale": "L2"}]}, outcomes=("out-a", "out-b"))
    assert m.records(canvas) == {"L2": 2, "L3": 1}
    assert m.cycles(canvas)["L2"] == {"active": 1, "ever": 2}
    out = m.findings(canvas)
    assert len(out) == 1 and out[0].startswith("L3: 1 target(s) chosen and no L3 diamond")


def test_an_old_shape_l2_counts_its_opportunity_as_its_target(tmp_path):
    m = _mod()
    canvas = _project(tmp_path, [{"id": "opp-1"}],
                      {"active_diamonds": [{"id": "l2", "scale": "L2", "object_ref": "opp-1"}]})
    assert m.records(canvas)["L3"] == 1


def test_active_zero_but_ever_nonzero_is_the_softer_finding(tmp_path):
    m = _mod()
    canvas = _project(tmp_path, [{"id": "opp-1"}],
                      {"completed_diamonds": [{"id": "l2-done", "scale": "L2"}]})
    assert m.findings(canvas) == ["L2: 1 desired outcome(s), 0 active L2 diamond(s) (1 ever)"]


def test_report_and_cli(tmp_path, monkeypatch, capsys):
    m = _mod()
    canvas = _project(tmp_path, [{"id": "opp-1"}],
                      {"active_diamonds": [{"id": "l2", "scale": "L2", "target": "opp-1"}]})
    monkeypatch.setattr("sys.argv", ["x", "--canvas-dir", str(canvas)])
    assert m.main() == 0
    out = capsys.readouterr().out
    assert "L2: 1 outcome(s); 1 active diamond(s), 1 ever" in out and "FINDING L3:" in out
    empty = tmp_path / "e" / ".claude" / "canvas"
    empty.mkdir(parents=True)
    assert m.report(empty) == 1
