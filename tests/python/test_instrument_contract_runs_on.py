"""check_instrument_contract.py — the RUNNABLE NOW, NEVER RUN advisory (v0.183.0).

A live instrument with `runs_on: disk` or `network` is listed oldest first with its age, WARN past 14
days; `runs_on: human` and scored instruments are not listed; the advisory never moves the exit code
or the problem count; main() accepts argv. In-process for the per-file coverage floor.
"""
import datetime as _dt
import importlib.util
import subprocess
from pathlib import Path

import _scratch_git

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
    _scratch_git.init(tmp_path)
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


WAITING = """---
type: assumption-test
frozen_at: 2026-10-16
frozen_before: "any traffic read after the event"
score_by: {score_by}
status: live
runs_on: network
waits_for: {waits_for}
does_not_reproduce: "whether anyone who arrives uses it"
decision_class: light
test_weight: light
---

# Test

## Frozen prediction

- P1: holds.
"""


def _write_waiting(root, name, score_by, waits_for):
    p = root / ".claude" / "evals" / "assumption-tests" / name
    p.write_text(WAITING.format(score_by=score_by, waits_for=waits_for))


def _section(out, head):
    return out.split(head)[1].split("\n\n")[0] if head in out else ""


def test_waits_for_before_score_by_is_waiting_not_runnable(tmp_path, capsys):
    """v0.330.1: a test whose data window has not closed says so in `waits_for` and is listed
    apart, with its line and date, so the session-start count does not include it."""
    root = _repo(tmp_path)
    _write_waiting(root, "w.md", "2026-10-30", '"the 14-day window after the event, closing 2026-10-29"')
    _write(root, "a-old.md", "2026-06-12")
    _commit(root)
    rc = cic.main(["--root", str(root), "--today", "2026-10-24"])
    out = capsys.readouterr().out
    assert rc == 0 and "problems: 0" in out
    assert "w.md" not in _section(out, "RUNNABLE NOW, NEVER RUN")
    assert "a-old.md" in _section(out, "RUNNABLE NOW, NEVER RUN")
    assert ("w.md (runs_on network, score_by 2026-10-30): the 14-day window after the event, "
            "closing 2026-10-29") in _section(out, "WAITING ON DATA")


def test_wait_holds_through_score_by_day_and_ends_after(tmp_path, capsys):
    root = _repo(tmp_path)
    _write_waiting(root, "w.md", "2026-10-30", "the window closing 2026-10-29")
    _commit(root)
    cic.main(["--root", str(root), "--today", "2026-10-30"])
    on_day = capsys.readouterr().out
    assert "w.md" in _section(on_day, "WAITING ON DATA") and "RUNNABLE NOW" not in on_day
    cic.main(["--root", str(root), "--today", "2026-10-31"])
    after = capsys.readouterr().out
    assert "WAITING ON DATA" not in after
    assert "w.md (runs_on network, 15 days live)" in _section(after, "RUNNABLE NOW, NEVER RUN")
    assert "w.md (due 2026-10-30, 1 days ago)" in after


def test_no_cap_on_the_wait(tmp_path, capsys):
    """A 30-day retention window is the same shape as a 14-day traffic window."""
    root = _repo(tmp_path)
    _write_waiting(root, "w.md", "2026-12-20", "30-day retention of the November cohort")
    _commit(root)
    cic.main(["--root", str(root), "--today", "2026-10-24"])
    out = capsys.readouterr().out
    assert "w.md" in _section(out, "WAITING ON DATA") and "RUNNABLE NOW" not in out


def test_empty_waits_for_or_no_score_by_stays_runnable(tmp_path, capsys):
    root = _repo(tmp_path)
    _write_waiting(root, "empty.md", "2026-10-30", '""')
    p = root / ".claude" / "evals" / "assumption-tests" / "undated.md"
    p.write_text(WAITING.format(score_by="", waits_for="the window"))
    _commit(root)
    cic.main(["--root", str(root), "--today", "2026-10-24"])
    out = capsys.readouterr().out
    runnable = _section(out, "RUNNABLE NOW, NEVER RUN")
    assert "empty.md" in runnable and "undated.md" in runnable
    assert "WAITING ON DATA" not in out


def test_session_start_counts_only_the_runnable_section(tmp_path):
    """The hook's own sed range over the check's real output: the waiting test is not counted."""
    root = _repo(tmp_path)
    _write_waiting(root, "w.md", "2026-10-30", "the window")
    _write(root, "a-old.md", "2026-06-12")
    _commit(root)
    out = subprocess.run(["python3", str(_MOD), "--root", str(root), "--today", "2026-10-24"],
                         capture_output=True, text=True, check=True).stdout
    counted = subprocess.run(["sed", "-n", "/^RUNNABLE NOW, NEVER RUN/,/^$/p"], input=out,
                             capture_output=True, text=True, check=True).stdout
    lines = [ln for ln in counted.splitlines() if ln.startswith("  ")]
    assert lines == ["  a-old.md (runs_on disk, 134 days live)  WARN"]


def test_runs_on_without_frozen_date_reports_unknown_age(tmp_path, capsys):
    root = _repo(tmp_path)
    p = root / ".claude" / "evals" / "assumption-tests" / "e.md"
    p.write_text(HEADER.format(frozen_at="", status="live", runs_on="disk"))
    _commit(root)
    cic.main(["--root", str(root), "--today", "2026-09-09"])
    out = capsys.readouterr().out
    assert "e.md (runs_on disk, ? days live)" in out
