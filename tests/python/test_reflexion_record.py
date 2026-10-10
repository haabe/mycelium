"""reflexion_record.py: a failed command is counted, not kept (v0.318.0).

Anthropic's plugin directory review of v0.317.4: reflexion-gate.sh kept 160 characters of each
failed command and 200 of its error output, unmasked, in .claude/state/reflexion-log.jsonl, so a
password typed into a failing command was stored in plain text in every project the plugin ran
in. These tests hold the new row shape, the opt-in, the scrub of old rows, and the hook wiring.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"
HOOK = SCRIPTS.parent / "hooks" / "reflexion-gate.sh"
_spec = importlib.util.spec_from_file_location("reflexion_record", SCRIPTS / "reflexion_record.py")
rr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rr)

SECRET = "hunter2-correct-horse"  # noqa: S105 — a fixture the log must never contain


def _payload(command: str, stderr: str = "ERROR: password authentication failed", code: int = 2) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command},
            "tool_response": {"exit_code": code, "stderr": stderr}}


def _rows(state: Path) -> list[dict]:
    return [json.loads(line) for line in (state / rr.LOG_NAME).read_text().splitlines()]


def test_a_default_row_keeps_no_command_and_no_error_output(tmp_path):
    state = tmp_path / ".claude" / "state"
    rr.record(state, _payload(f"PGPASSWORD={SECRET} psql -h db -U app", f"bad password {SECRET}"),
              environ={})
    raw = (state / rr.LOG_NAME).read_text()
    assert SECRET not in raw
    (row,) = _rows(state)
    assert row["program"] == "psql" and row["exit_code"] == 2 and row["tool"] == "Bash"
    assert "command_head" not in row and "stderr_head" not in row and "masked" not in row


@pytest.mark.parametrize(("command", "program"), [
    ("git push origin main", "git"),
    ("./build.sh --release", "build.sh"),
    ("/usr/bin/env python3 x.py", "env"),
    ("A=1 B=2 make test", "make"),
    ('"$(cat ~/.secret)" --go', None),
    ("mysql -p'x'", "mysql"),
    ("", None),
    ("TOKEN=abc", None),
])
def test_the_program_is_a_plain_first_word_or_nothing(command, program):
    assert rr.program_of(command) == program


def test_opting_in_keeps_the_command_masked(tmp_path):
    state = tmp_path / ".claude" / "state"
    token = "ghp_abcdefghijklmnopqrstuvwxyz0123"  # noqa: S105 — fixture
    rr.record(state, _payload(f"GITHUB_TOKEN={token} gh api user", "x" * 500),
              environ={"MYCELIUM_LEDGER_TRIGGER": "on"})
    (row,) = _rows(state)
    assert row["masked"] is True
    assert token not in row["command_head"] and "<masked>" in row["command_head"]
    assert len(row["command_head"]) <= 160 and len(row["stderr_head"]) <= 200


def test_a_documented_non_failure_keeps_its_reason(tmp_path):
    state = tmp_path / ".claude" / "state"
    rr.record(state, _payload("grep -n foo bar", "", 1), "grep exit 1 = no match", environ={})
    assert _rows(state)[0]["suppressed"] == "grep exit 1 = no match"


def test_recording_creates_the_folder_with_its_ignore_file(tmp_path):
    state = tmp_path / ".claude" / "state"
    rr.record(state, _payload("make"), environ={})
    assert (state / ".gitignore").is_file()


def test_scrub_strips_old_rows_and_keeps_masked_ones(tmp_path):
    state = tmp_path / ".claude" / "state"
    state.mkdir(parents=True)
    old = {"ts": "t", "tool": "Bash", "command_head": f"mysql -p{SECRET}", "exit_code": "1",
           "stderr_head": f"denied {SECRET}"}
    masked = {"ts": "t", "command_head": "gh api <masked>", "stderr_head": None, "masked": True}
    (state / rr.LOG_NAME).write_text(
        json.dumps(old) + "\n" + "{torn line\n" + json.dumps(masked) + "\n" + json.dumps({"ts": "t"}) + "\n")
    assert rr.scrub(state) == 1
    text = (state / rr.LOG_NAME).read_text()
    assert SECRET not in text and "{torn line" in text and "gh api <masked>" in text
    first = json.loads(text.splitlines()[0])
    assert first == {"ts": "t", "tool": "Bash", "exit_code": "1"}


def test_scrub_writes_nothing_when_nothing_is_old(tmp_path):
    state = tmp_path / ".claude" / "state"
    state.mkdir(parents=True)
    log = state / rr.LOG_NAME
    log.write_text(json.dumps({"ts": "t", "program": "git"}) + "\n")
    before = log.stat().st_mtime_ns
    assert rr.scrub(state) == 0
    assert log.stat().st_mtime_ns == before
    assert rr.scrub(tmp_path / "missing") == 0


def test_cli_records_from_stdin_and_scrubs(tmp_path, monkeypatch):
    state = tmp_path / ".claude" / "state"
    monkeypatch.delenv("MYCELIUM_LEDGER_TRIGGER", raising=False)
    assert rr.main(["record", "--state-dir", str(state)],
                   stdin=io.StringIO(json.dumps(_payload(f"curl -u me:{SECRET} https://x")))) == 0
    assert rr.main(["record", "--state-dir", str(state)], stdin=io.StringIO("not json")) == 0
    assert rr.main(["scrub", "--state-dir", str(state)]) == 0
    assert SECRET not in (state / rr.LOG_NAME).read_text()
    assert [r["program"] for r in _rows(state)] == ["curl", None]


def test_the_hook_writes_the_new_row_shape(tmp_path):
    """Wiring: reflexion-gate.sh hands its payload to reflexion_record.py and the command never
    reaches the log."""
    payload = _payload(f"mysql -p{SECRET} -e 'select 1'")
    payload["cwd"] = str(tmp_path)
    env = {k: v for k, v in os.environ.items() if k != "MYCELIUM_LEDGER_TRIGGER"}
    env.update(CLAUDE_PROJECT_DIR=str(tmp_path), CLAUDE_PLUGIN_ROOT=str(SCRIPTS.parent))
    subprocess.run(["bash", str(HOOK)], input=json.dumps(payload), capture_output=True, text=True,
                   env=env, timeout=30, check=False)
    state = tmp_path / ".claude" / "state"
    assert SECRET not in (state / rr.LOG_NAME).read_text()
    assert _rows(state)[0]["program"] == "mysql"
    assert (state / ".gitignore").is_file()
