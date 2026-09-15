"""Coverage for check_opportunity_shape: a triage list, never a gate."""
import importlib.util
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/mycelium/scripts/check_opportunity_shape.py"


def _mod():
    spec = importlib.util.spec_from_file_location("cos", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["cos"] = m
    spec.loader.exec_module(m)
    return m


def _canvas(tmp_path, opps):
    d = tmp_path / ".claude" / "canvas"
    d.mkdir(parents=True)
    (d / "opportunities.yml").write_text(yaml.safe_dump({"opportunities": opps}, sort_keys=False))
    return d


def test_score_reads_the_name_and_the_solution_leaf():
    m = _mod()
    assert m.score({"name": "A builder needs to see the tree", "solutions": [{"id": "s"}]}) == (3, [])
    n, missing = m.score({"name": "Refactor the validator"})
    assert n == 0 and missing == ["no need-language", "no human subject", "no solution leaf"]


def test_the_report_groups_by_root_and_lists_low_scores(tmp_path):
    d = _canvas(tmp_path, [
        {"id": "opp-1", "name": "A builder needs to see the tree", "rolls_up_to": "adoption",
         "solutions": [{"id": "s"}]},
        {"id": "opp-2", "name": "Refactor the validator", "rolls_up_to": "framework"},
    ])
    r = subprocess.run([sys.executable, str(SCRIPT), "--canvas-dir", str(d)],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0
    assert "root 'framework': n=1  mean=0.00" in r.stdout
    assert "[0/3]  opp-2" in r.stdout and "opp-1" not in r.stdout.split("candidates for triage")[1]
    assert "A LOW SCORE IS NOT A VERDICT" in r.stdout


def test_summarise_is_one_line_and_empty_without_entries(tmp_path):
    m = _mod()
    d = _canvas(tmp_path, [{"id": "opp-1", "name": "Users need to know", "rolls_up_to": "r"}])
    line = m.summarise(d / "opportunities.yml")
    assert line.startswith("r: n=1 mean=2.00 <=1: 0") and "\n" not in line
    empty = _canvas(tmp_path / "e", [])
    assert m.summarise(empty / "opportunities.yml") == ""


def test_no_entries_is_not_a_pass_and_no_file_is_a_precondition(tmp_path):
    d = _canvas(tmp_path, [])
    r = subprocess.run([sys.executable, str(SCRIPT), "--canvas-dir", str(d)],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 1 and "NOT A PASS" in r.stdout
    r2 = subprocess.run([sys.executable, str(SCRIPT), "--canvas-dir", str(tmp_path / "none")],
                        capture_output=True, text=True, check=False)
    assert r2.returncode == 2


def test_report_and_main_in_process(tmp_path, monkeypatch, capsys):
    m = _mod()
    d = _canvas(tmp_path, [
        {"id": "opp-1", "name": "A builder needs to see the tree", "rolls_up_to": "adoption",
         "solutions": [{"id": "s"}]},
        {"id": "opp-2", "name": "Refactor the validator"},
        "not a mapping",
    ])
    assert m.report(d / "opportunities.yml") == 0
    out = capsys.readouterr().out
    assert "root '(untagged)'" in out and "1 of 2 entries score <=1" in out
    monkeypatch.setattr("sys.argv", ["x", "--canvas-dir", str(d)])
    assert m.main() == 0
    monkeypatch.setattr("sys.argv", ["x", "--canvas-dir", str(tmp_path / "none")])
    assert m.main() == 2
    empty = _canvas(tmp_path / "e", [])
    assert m.report(empty / "opportunities.yml") == 1
