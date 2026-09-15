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


def _project(tmp_path, opps, diamonds):
    canvas = tmp_path / ".claude" / "canvas"
    canvas.mkdir(parents=True)
    (canvas / "opportunities.yml").write_text(yaml.safe_dump({"opportunities": opps}))
    (tmp_path / ".claude" / "diamonds").mkdir()
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text(yaml.safe_dump(diamonds))
    return canvas


def test_records_exclude_terminal_solutions_and_findings_name_the_empty_scale(tmp_path):
    m = _mod()
    canvas = _project(tmp_path, [
        {"id": "opp-1", "solutions": [{"id": "sol-1", "status": "candidate"},
                                      {"id": "sol-2", "status": "shipped"}]},
        {"id": "opp-2"},
    ], {"active_diamonds": [{"id": "l1", "scale": "L1"}, {"id": "l2-old", "scale": "L2"}],
        "completed_diamonds": [{"id": "l2-done", "scale": "L2"}]})
    assert m.records(canvas) == {"L2": 2, "L3": 1}
    assert m.cycles(canvas)["L2"] == {"active": 1, "ever": 2}
    out = m.findings(canvas)
    assert len(out) == 1 and out[0].startswith("L3: 1 record(s) and no L3 diamond has ever")


def test_active_zero_but_ever_nonzero_is_the_softer_finding(tmp_path):
    m = _mod()
    canvas = _project(tmp_path, [{"id": "opp-1"}],
                      {"completed_diamonds": [{"id": "l2-done", "scale": "L2"}]})
    assert m.findings(canvas) == ["L2: 1 record(s), 0 active L2 diamond(s) (1 ever)"]


def test_report_and_cli(tmp_path, monkeypatch, capsys):
    m = _mod()
    canvas = _project(tmp_path, [{"id": "opp-1", "solutions": [{"id": "s", "status": "candidate"}]}],
                      {"active_diamonds": [{"id": "l2", "scale": "L2"}]})
    monkeypatch.setattr("sys.argv", ["x", "--canvas-dir", str(canvas)])
    assert m.main() == 0
    out = capsys.readouterr().out
    assert "L2: 1 record(s); 1 active diamond(s), 1 ever" in out and "FINDING L3:" in out
    empty = tmp_path / "e" / ".claude" / "canvas"
    empty.mkdir(parents=True)
    assert m.report(empty) == 1
    r = subprocess.run([sys.executable, str(SCRIPT), "--canvas-dir", str(tmp_path / "none")],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 2
