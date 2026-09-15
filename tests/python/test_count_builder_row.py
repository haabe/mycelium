"""Coverage for count_builder_row: a builder's own row, from their own record, sent nowhere."""
import importlib.util
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/mycelium/scripts/count_builder_row.py"


def _mod():
    spec = importlib.util.spec_from_file_location("cbr", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["cbr"] = m
    spec.loader.exec_module(m)
    return m


def _git(cwd, *args, when="2026-06-02T12:00:00"):
    env = {**os.environ, "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when,
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@x"}
    subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True)


def _project(tmp_path):
    p = tmp_path / "proj"
    (p / ".claude" / "harness").mkdir(parents=True)
    (p / ".claude" / "canvas").mkdir()
    (p / ".claude" / "state").mkdir()
    (p / ".claude" / "harness" / "decision-log.md").write_text(
        "## 2026-05-20 — DL-1: kill the widget idea after https://example.com/thread\n\nbody\n"
        "## 2026-05-25 — DL-2: pick the CLI shape\n\nfrom my own head\n"
        "## 2026-06-10 — DL-3: after code, interview said x\n\n")
    (p / ".claude" / "canvas" / "cycle-history.yml").write_text(
        "cycles:\n  - {leaf_id: sol-1, terminal_state: killed, completed_at: '2026-05-21'}\n"
        "  - {leaf_id: sol-2, terminal_state: killed, completed_at: '2026-07-01'}\n")
    (p / ".claude" / "canvas" / "archived-solutions.yml").write_text(
        "archived:\n  - {id: sol-3, archived_at: '2026-05-30'}\n")
    (p / ".claude" / "state" / "read-log.jsonl").write_text(
        '{"session_id": "a"}\n{"session_id": "b"}\nbad\n')
    (p / ".claude" / "state" / "change-log.jsonl").write_text('{"session_id": "a"}\n')
    _git(p, "init", "-q")
    (p / "README.md").write_text("x")
    _git(p, "add", ".")
    _git(p, "commit", "-q", "-m", "docs", when="2026-05-01T12:00:00")
    (p / "src").mkdir()
    (p / "src" / "main.py").write_text("print(1)\n")
    _git(p, "add", ".")
    _git(p, "commit", "-q", "-m", "code", when="2026-06-02T12:00:00")
    return p


def test_row_counts_before_the_first_source_file(tmp_path):
    m = _mod()
    p = _project(tmp_path)
    assert m.first_source_date(p) == date(2026, 6, 2)
    r = m.row(p)
    assert r == {"first_source": "2026-06-02", "decisions_total": 3,
                 "decisions_before_first_source": 2, "citing_outside_evidence": 1,
                 "kills_before_code": 2, "sessions": 2}


def test_no_git_or_no_code_means_unknown_and_nothing_before(tmp_path):
    m = _mod()
    p = tmp_path / "nogit"
    (p / ".claude" / "harness").mkdir(parents=True)
    (p / ".claude" / "harness" / "decision-log.md").write_text("## 2026-05-20 — DL-1: x\n")
    assert m.first_source_date(p) is None
    r = m.row(p)
    assert r["first_source"] == "unknown" and r["decisions_before_first_source"] == 0
    assert r["kills_before_code"] == 0 and r["sessions"] == 0


def test_cli_prints_one_line_and_refuses_without_a_log(tmp_path):
    p = _project(tmp_path)
    r = subprocess.run([sys.executable, str(SCRIPT), "--project-dir", str(p)],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0
    assert r.stdout.startswith("mycelium row | first source file 2026-06-02 | decisions before it 2")
    assert "lexical proxy" in r.stdout and "Nothing was sent" in r.stdout
    j = subprocess.run([sys.executable, str(SCRIPT), "--project-dir", str(p), "--json"],
                       capture_output=True, text=True, check=False)
    assert json.loads(j.stdout)["sessions"] == 2
    empty = tmp_path / "empty"
    empty.mkdir()
    r2 = subprocess.run([sys.executable, str(SCRIPT), "--project-dir", str(empty)],
                        capture_output=True, text=True, check=False)
    assert r2.returncode == 1 and "NOT A PASS" in r2.stdout


def test_main_in_process(tmp_path, monkeypatch, capsys):
    m = _mod()
    p = _project(tmp_path)
    monkeypatch.setattr("sys.argv", ["x", "--project-dir", str(p)])
    assert m.main() == 0 and "mycelium row" in capsys.readouterr().out
    monkeypatch.setattr("sys.argv", ["x", "--project-dir", str(p), "--json"])
    assert m.main() == 0
