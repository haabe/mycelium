"""The record a leaf owes, said at the write that creates the gap (v0.287.0)."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "plugins" / "mycelium" / "scripts" / "leaf_record_nudge.py"
HOOK = ROOT / "plugins" / "mycelium" / "hooks" / "post-write-nudge.sh"
_spec = importlib.util.spec_from_file_location("leaf_record_nudge", SCRIPT)
lrn = importlib.util.module_from_spec(_spec)
sys.path.insert(0, str(SCRIPT.parent))
_spec.loader.exec_module(lrn)


def _canvas(tmp_path: Path) -> Path:
    c = tmp_path / ".claude" / "canvas"
    c.mkdir(parents=True)
    (c / "opportunities.yml").write_text(
        "opportunities:\n- id: opp-1\n  solutions:\n"
        "  - id: sol-1a\n    status: shipped\n  - id: sol-1b\n    status: shipped\n")
    (c / "cycle-history.yml").write_text("cycles:\n- cycle_id: cycle-001\n  leaf_id: sol-1b\n")
    return c


def _run(canvas: Path, new_string: str) -> str:
    payload = {"tool_name": "Edit", "tool_input": {
        "file_path": str(canvas / "opportunities.yml"), "old_string": "x", "new_string": new_string}}
    return subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(payload), text=True,
                          capture_output=True, check=True).stdout


def test_a_leaf_this_write_shipped_without_a_cycle_row_is_named(tmp_path):
    out = _run(_canvas(tmp_path), "  - id: sol-1a\n    status: shipped\n")
    assert "sol-1a is `shipped` with no cycle-history.yml row" in out


def test_control_a_leaf_with_its_cycle_row_owes_nothing(tmp_path):
    assert _run(_canvas(tmp_path), "  - id: sol-1b\n    status: shipped\n") == ""


def test_control_a_leaf_this_write_did_not_touch_is_not_nagged(tmp_path):
    assert _run(_canvas(tmp_path), "  - id: sol-9z\n    note: unrelated\n") == ""


def test_the_hook_carries_it_on_writes_to_the_tree(tmp_path):
    canvas = _canvas(tmp_path)
    payload = {"tool_name": "Edit", "tool_input": {
        "file_path": str(canvas / "opportunities.yml"), "old_string": "x",
        "new_string": "  - id: sol-1a\n    status: shipped\n"}}
    out = subprocess.run(["bash", str(HOOK)], input=json.dumps(payload), text=True,
                         capture_output=True, check=False,
                         env={"CLAUDE_PROJECT_DIR": str(tmp_path),
                              "PATH": str(Path(sys.executable).parent) + ":/usr/bin:/bin"}).stdout
    assert "LEAF RECORDS OWED BY THIS WRITE" in out and "sol-1a" in out


# ------------------------------------------------------------------ in process (coverage)


def _main(monkeypatch, capsys, payload) -> str:
    import io
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload if isinstance(payload, str)
                                                  else json.dumps(payload)))
    assert lrn.main() == 0
    return capsys.readouterr().out


def test_main_names_the_owed_row_in_process(tmp_path, monkeypatch, capsys):
    canvas = _canvas(tmp_path)
    out = _main(monkeypatch, capsys, {"tool_input": {
        "file_path": str(canvas / "opportunities.yml"),
        "edits": [{"new_string": "  - id: sol-1a\n"}]}})
    assert "sol-1a is `shipped`" in out


def test_main_is_silent_on_other_files_bad_input_and_no_leaf(tmp_path, monkeypatch, capsys):
    canvas = _canvas(tmp_path)
    assert _main(monkeypatch, capsys, "not json") == ""
    assert _main(monkeypatch, capsys, {"tool_input": {"file_path": str(canvas / "purpose.yml"),
                                                       "content": "sol-1a"}}) == ""
    assert _main(monkeypatch, capsys, {"tool_input": {
        "file_path": str(canvas / "opportunities.yml"), "content": "no leaf here"}}) == ""


def test_a_new_solution_with_no_stance_is_named(tmp_path, monkeypatch):
    canvas = _canvas(tmp_path)
    import check_purpose_stance as cps
    monkeypatch.setattr(cps, "purpose_stance_findings", lambda c, d: [
        "sol-1a (under opp-1): no purpose_stance against 1 binding properties (pp-001)"])
    out = lrn.owed(canvas, {"sol-1a"})
    assert any("sol-1a has no purpose_stance" in x for x in out)


def test_a_check_that_cannot_run_says_so(tmp_path, monkeypatch):
    import check_cycle_recording as ccr
    import check_purpose_stance as cps

    def boom(*a, **k):
        raise RuntimeError("x")
    monkeypatch.setattr(ccr, "terminal_leaf_without_cycle_findings", boom)
    monkeypatch.setattr(cps, "purpose_stance_findings", boom)
    out = lrn.owed(_canvas(tmp_path), {"sol-1a"})
    assert out == ["(cycle-record check could not run: RuntimeError)",
                   "(purpose-stance check could not run: RuntimeError)"]
