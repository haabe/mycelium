"""check_instrument_contract.py — the RUNNABLE NOW, NEVER RUN advisory (v0.183.0).

A live instrument with `runs_on: disk` or `network` is listed oldest first with its age, WARN past 14
days; `runs_on: human` and scored instruments are not listed; the advisory never moves the exit code
or the problem count; main() accepts argv. In-process for the per-file coverage floor.
"""
import datetime as _dt
import importlib.util
import subprocess
from pathlib import Path

_MOD = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts" / "check_instrument_contract.py"
_spec = importlib.util.spec_from_file_location("check_instrument_contract_runs_on", _MOD)
cic = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(cic)

HEADER = """---
type: assumption-test
frozen_at: {frozen_at}
frozen_before: "the analyzer is launched"
score_by: 2026-12-31
status: {status}
runs_on: {runs_on}
---

# Test

## Frozen prediction

- P1: holds.
"""


def _repo(tmp_path: Path) -> Path:
    (tmp_path / ".claude" / "evals" / "assumption-tests").mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    return tmp_path


def _write(root, name, frozen_at, status="live", runs_on="disk"):
    p = root / ".claude" / "evals" / "assumption-tests" / name
    p.write_text(HEADER.format(frozen_at=frozen_at, status=status, runs_on=runs_on))


def _commit(root):
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "add"], cwd=root, check=True)


def test_runnable_listed_oldest_first_with_warn_and_no_problem(tmp_path, capsys):
    root = _repo(tmp_path)
    _write(root, "a-old.md", "2026-06-12")
    _write(root, "b-new.md", "2026-09-05", runs_on="network")
    _write(root, "c-human.md", "2026-06-12", runs_on="human")
    _write(root, "d-scored.md", "2026-06-12", status="scored")
    _commit(root)
    rc = cic.main(["--root", str(root), "--today", "2026-09-09"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "RUNNABLE NOW, NEVER RUN" in out
    i_old, i_new = out.index("a-old.md"), out.index("b-new.md")
    assert i_old < i_new
    assert "a-old.md (runs_on disk, 89 days live)  WARN" in out
    assert "b-new.md (runs_on network, 4 days live)" in out and "b-new.md (runs_on network, 4 days live)  WARN" not in out
    assert "c-human.md" not in out.split("RUNNABLE NOW")[1].split("\n\n")[0]
    assert "d-scored.md" not in out.split("RUNNABLE NOW")[1].split("\n\n")[0]
    assert "problems: 0" in out


def test_no_runnable_prints_no_section(tmp_path, capsys):
    root = _repo(tmp_path)
    _write(root, "c-human.md", "2026-06-12", runs_on="human")
    _commit(root)
    rc = cic.main(["--root", str(root), "--today", "2026-09-09"])
    out = capsys.readouterr().out
    assert rc == 0 and "RUNNABLE NOW" not in out


def test_runs_on_without_frozen_date_reports_unknown_age(tmp_path, capsys):
    root = _repo(tmp_path)
    p = root / ".claude" / "evals" / "assumption-tests" / "e.md"
    p.write_text(HEADER.format(frozen_at="", status="live", runs_on="disk"))
    _commit(root)
    cic.main(["--root", str(root), "--today", "2026-09-09"])
    out = capsys.readouterr().out
    assert "e.md (runs_on disk, ? days live)" in out
