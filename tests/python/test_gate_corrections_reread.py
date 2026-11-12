"""gate.sh check 3: after corrections.md changes, a read of the file is what lets calls through.

Until 0.334.1 a changed corrections.md made the gate refuse the next call with "Re-read corrections
and re-run preflight." and delete the preflight stamp. The next call of any kind then found no
stamp, ran preflight itself and passed, so the refusal cleared on a blind retry and checked no
read; and the agent's own preflight command, the remedy the message named, was refused like any
other call (dogfood 2026-10-11 and 2026-10-12).

Now the gate asks the read log whether the file was read after it changed. Read: the stamp takes
the new hash and the call (the preflight command included) goes through. Not read: refused, and the
refusal holds until a read. A project with no read log keeps the old once-then-retry behaviour.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2] / "plugins" / "mycelium"
GATE = PLUGIN / "hooks" / "gate.sh"
PREFLIGHT = PLUGIN / "hooks" / "preflight.sh"
READ_LOG = PLUGIN / "hooks" / "read-log.sh"


def _env(root: Path) -> dict:
    stamps = root / "stamps"
    stamps.mkdir(exist_ok=True)
    return {"CLAUDE_PROJECT_DIR": str(root), "CLAUDE_PLUGIN_ROOT": str(PLUGIN),
            "MYCELIUM_CROSS_REPO_WATCH": "", "MYCELIUM_ADVISORY_LEDGER": "off",
            "TMPDIR": str(stamps), "HOME": str(root),
            "PATH": str(Path(sys.executable).parent) + os.pathsep + "/usr/bin:/bin:/usr/sbin:/sbin"}


def _project(root: Path, *, read_log: bool = True) -> Path:
    for d in ("canvas", "memory", "state"):
        (root / ".claude" / d).mkdir(parents=True, exist_ok=True)
    corrections = root / ".claude" / "memory" / "corrections.md"
    corrections.write_text("# corrections\n")
    if read_log:
        (root / ".claude" / "state" / "read-log.jsonl").write_text("")
    subprocess.run(["bash", str(PREFLIGHT)], input="", capture_output=True, text=True,
                   env=_env(root), check=True, timeout=120)
    return corrections


def _stamp(root: Path) -> Path:
    found = list((root / "stamps").glob("mycelium-preflight-stamp-*"))
    assert len(found) == 1, found
    return found[0]


def _change(corrections: Path) -> None:
    time.sleep(0.05)
    with corrections.open("a") as fh:
        fh.write("- **A new correction (2026-11-12, process)**: read me.\n")


def _read(root: Path, corrections: Path) -> None:
    """The Read tool's PostToolUse event, through the shipped read-log hook."""
    time.sleep(0.05)
    payload = json.dumps({"tool_name": "Read", "tool_input": {"file_path": str(corrections)},
                          "session_id": "s1"})
    subprocess.run(["bash", str(READ_LOG)], input=payload, capture_output=True, text=True,
                   env=_env(root), check=True, timeout=60)


def _bash(root: Path, command: str) -> subprocess.CompletedProcess:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command},
                          "session_id": "s1", "tool_use_id": "toolu_1"})
    return subprocess.run(["bash", str(GATE)], input=payload, capture_output=True, text=True,
                          env=_env(root), check=False, timeout=120)


def _preflight_command(root: Path) -> str:
    return f'CLAUDE_PROJECT_DIR="{root}" bash {PREFLIGHT} </dev/null'


def test_a_read_after_the_change_lets_the_preflight_run_through(tmp_path):
    """RED ON 0.334.1: the preflight command the message asked for was refused."""
    corrections = _project(tmp_path)
    _change(corrections)
    _read(tmp_path, corrections)
    done = _bash(tmp_path, _preflight_command(tmp_path))
    assert done.returncode == 0, done.stderr
    stamp = json.loads(_stamp(tmp_path).read_text())
    assert stamp["corrections_hash"] != "none"
    assert _bash(tmp_path, "git status").returncode == 0


def test_without_a_read_the_refusal_holds_and_says_what_clears_it(tmp_path):
    """RED ON 0.334.1: the second, identical call went through with no read in between."""
    corrections = _project(tmp_path)
    _change(corrections)
    first = _bash(tmp_path, "git status")
    second = _bash(tmp_path, _preflight_command(tmp_path))
    assert first.returncode == 2
    assert second.returncode == 2
    assert "Read it" in first.stderr
    assert "re-running preflight does not" in first.stderr
    _read(tmp_path, corrections)
    assert _bash(tmp_path, "git status").returncode == 0


def test_a_read_from_before_the_change_does_not_count(tmp_path):
    """GREEN ON 0.334.1 TOO (it refused the first call after any change); pins the timing rule."""
    corrections = _project(tmp_path)
    _read(tmp_path, corrections)
    _change(corrections)
    assert _bash(tmp_path, "git status").returncode == 2


def test_a_shell_read_of_the_file_is_let_through(tmp_path):
    """On a runtime with no Read tool a shell read is the only way to re-read the file."""
    corrections = _project(tmp_path)
    _change(corrections)
    assert _bash(tmp_path, "cat .claude/memory/corrections.md").returncode == 0
    assert _bash(tmp_path, "echo .claude/memory/corrections.md; git status").returncode == 2


def test_control_no_read_log_keeps_the_refuse_once_then_retry_behaviour(tmp_path):
    """GREEN ON 0.334.1 TOO, except for the wording: with no read log the gate cannot see a read."""
    corrections = _project(tmp_path, read_log=False)
    _change(corrections)
    first = _bash(tmp_path, "git status")
    assert first.returncode == 2
    assert _bash(tmp_path, "git status").returncode == 0


def test_control_an_unchanged_file_is_not_refused(tmp_path):
    _project(tmp_path)
    assert _bash(tmp_path, "git status").returncode == 0
