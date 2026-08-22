"""Coverage for the fire/override ledgers on shell-safety-guard and absence-claim-guard (v0.119.0).

WHY THESE TWO GUARDS GOT AN INSTRUMENT. On 2026-08-22 a working session measured them:
both fired correctly and repeatedly, both were read past, and both errors they described
happened anyway — a push reported as successful when it had not landed, and a false
absence claim that reached a released changelog. **That override was visible only in a
transcript, and transcripts die.**

Two existing rules make the ledger part of the ship rather than telemetry:

  - `opportunities.yml#sol-048a`: a guard whose ACTION RATE stays near zero is narrowed or
    retired, not left running. Unenforceable without a count.
  - The same session's finding: without an OVERRIDE rate, an advisory guard cannot be told
    apart from an effective one. Both look identical from outside — they fire and nothing
    breaks.

THE OVERRIDE MEASURE, AND WHY IT NEEDS NO SELF-REPORTING. Each fire carries a `signature`
derived from what matched. The same signature firing again is an agent that was warned and
carried on; a corrected agent does not re-trigger the same rule. Nobody has to admit
anything, which matters when the thing being measured is the agent doing the measuring.

The three ways this could rot, and the tests that stop them:

  1. THE LEDGER BREAKS THE SESSION. A guard that throws while logging is worse than one
     that never logged. Every write is wrapped and every failure is silent.
  2. THE SIGNATURE IS UNSTABLE. If the same trap produced a different signature each time,
     repeats would be invisible and the override rate would read as zero forever.
  3. IT LOGS WHEN IT DID NOT FIRE. A ledger with phantom rows makes the action rate look
     healthy, which is the exact failure that would let a dead guard keep running.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins/mycelium/scripts"
SHELL = SCRIPTS / "shell_safety_guard.py"
ABSENCE = SCRIPTS / "absence_claim_guard.py"

TRAP = "git push | tail -4; echo $?"          # $? after a pipe — the real 2026-08-22 case
OTHER_TRAP = "ls | grep foo && echo done"      # grep gating an && chain
CANVAS = "/Users/x/proj/.claude/canvas/user-needs.yml"
OWED = "A reply is still owed to him."


def _run(script, payload, project_dir):
    return subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(project_dir)},
        check=False,
    )


def _rows(project_dir, hook):
    log = Path(project_dir) / ".claude" / "state" / f"{hook}-log.jsonl"
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text().splitlines() if line.strip()]


@pytest.fixture
def project(tmp_path):
    return tmp_path


def test_shell_guard_logs_a_fire(project):
    r = _run(SHELL, {"tool_input": {"command": TRAP}}, project)
    assert r.returncode == 0
    assert r.stdout.strip(), "guard should have warned"
    rows = _rows(project, "shell-safety-guard")
    assert len(rows) == 1
    assert rows[0]["hook"] == "shell-safety-guard"
    assert rows[0]["fires"] >= 1
    assert rows[0]["signature"]
    assert rows[0]["at"]


def test_silent_runs_write_nothing(project):
    """A ledger with phantom rows makes a dead guard look alive."""
    r = _run(SHELL, {"tool_input": {"command": "echo hello"}}, project)
    assert r.returncode == 0
    assert not r.stdout.strip()
    assert _rows(project, "shell-safety-guard") == []


def test_same_trap_twice_yields_the_same_signature(project):
    """This is the whole override measure. Unstable signatures would hide every repeat."""
    for _ in range(2):
        _run(SHELL, {"tool_input": {"command": TRAP}}, project)
    rows = _rows(project, "shell-safety-guard")
    assert len(rows) == 2
    assert rows[0]["signature"] == rows[1]["signature"]


def test_different_traps_yield_different_signatures(project):
    """Otherwise every fire collapses into one and the rate is meaningless."""
    _run(SHELL, {"tool_input": {"command": TRAP}}, project)
    _run(SHELL, {"tool_input": {"command": OTHER_TRAP}}, project)
    rows = _rows(project, "shell-safety-guard")
    assert len({r["signature"] for r in rows}) == 2


def test_absence_guard_logs_a_fire(project):
    payload = {"tool_name": "Write", "tool_input": {"file_path": CANVAS, "content": OWED}}
    r = _run(ABSENCE, payload, project)
    assert r.returncode == 0
    assert r.stdout.strip(), "guard should have warned"
    rows = _rows(project, "absence-claim-guard")
    assert len(rows) == 1
    assert rows[0]["hook"] == "absence-claim-guard"


def test_absence_guard_silent_run_writes_nothing(project):
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": CANVAS, "content": "confidence 0.45 holds."},
    }
    r = _run(ABSENCE, payload, project)
    assert not r.stdout.strip()
    assert _rows(project, "absence-claim-guard") == []


def test_the_row_records_what_fired_not_the_whole_input(project):
    """Enough to compute a rate, not enough to be a transcript."""
    long_command = TRAP + " # " + ("x" * 500)
    _run(SHELL, {"tool_input": {"command": long_command}}, project)
    row = _rows(project, "shell-safety-guard")[0]
    assert len(row["first_match"]) <= 120
    assert "x" * 200 not in json.dumps(row)


def test_an_unwritable_state_dir_does_not_break_the_guard(project, monkeypatch):
    """An instrument that breaks a session is worse than one with a gap."""
    blocked = project / "blocked"
    blocked.write_text("not a directory")
    r = _run(SHELL, {"tool_input": {"command": TRAP}}, blocked)
    assert r.returncode == 0
    assert r.stdout.strip(), "the warning must still be emitted when logging fails"
