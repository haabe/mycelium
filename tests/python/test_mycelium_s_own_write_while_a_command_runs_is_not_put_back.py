"""Mycelium's own write of the diamonds file while a shell command runs is not the command's
(v0.325.1).

WHAT WAS WRONG, dogfood 2026-10-15, the first live session on 0.325.0. Session start runs
`derive_closing_path.py --all --write` in the background. The agent's first command, a read-only
`git log`, ran while it was writing. The shell guard compares the diamonds file around every
command, so it took the closing-path write for the command's: it put the file back and told the
person the agent had changed it without asking. The script went on writing after the put-back,
diamond by diamond, so the file matched neither the committed version nor the script's output.

WHAT HOLDS NOW. The writer applies its own edit to the guard's copies from before each running
command, before it writes, so the comparison sees only what the command did. A command that also
changed the file is put back as before, to a version that keeps the writer's change, whichever of
the two wrote first.

Every test drives both halves of the guard around a write the test makes in between, standing in
for the background script and, where named, the command.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
sys.path.insert(0, str(PLUGIN / "scripts"))
import bash_state_guard as bsg  # noqa: E402
import derive_closing_path as dcp  # noqa: E402

REC = ".claude/diamonds/active.yml"
RECORD = ("active_diamonds:\n- id: l1-strategy\n  scale: L1\n  definition_of_done:\n"
          "    outcome: builders talk to users\n- id: l2-reach\n  scale: L2\n"
          "completed_diamonds: []\n")
NEW_BAR = ("builders talk to users", "builders find posts in time")
ENTRY = {"stored_at": "2026-10-15", "gates": [], "inputs": [], "fired": []}
OTHER = {"stored_at": "2026-10-15", "gates": [], "inputs": [], "fired": []}


@pytest.fixture
def project(tmp_path: Path, monkeypatch) -> Path:
    for sub in (".claude/canvas", ".claude/diamonds", ".claude/state"):
        (tmp_path / sub).mkdir(parents=True)
    (tmp_path / REC).write_text(RECORD)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("MYCELIUM_GUARD_STATE_EDIT", raising=False)
    monkeypatch.delenv("GIT_DIR", raising=False)
    return tmp_path


def _payload(project: Path, call: str = "call-1", command: str = "git log -3") -> dict:
    return {"tool_name": "Bash", "tool_use_id": call, "session_id": "s1", "cwd": str(project),
            "tool_input": {"command": command}}


def _around(project: Path, act, capsys, command: str = "git log -3") -> dict:
    assert bsg.pre(_payload(project, command=command), project) == 0
    capsys.readouterr()
    act()
    assert bsg.post(_payload(project, command=command), project) == 0
    out = capsys.readouterr().out.strip()
    return json.loads(out) if out else {}


def _derived(text: str) -> str:
    return dcp.with_closes_on(dcp.with_closes_on(text, "l1-strategy", ENTRY), "l2-reach", OTHER)


def _background_write(project: Path) -> None:
    dcp.write_closes_on(project, "l1-strategy", ENTRY)
    dcp.write_closes_on(project, "l2-reach", OTHER)


def _command_changes_the_bar(project: Path) -> None:
    rec = project / REC
    rec.write_text(rec.read_text().replace(*NEW_BAR))


# ---------------------------------------------------------------- the misfire, closed


def test_the_start_up_write_during_a_read_only_command_stands_and_nothing_is_said(project,
                                                                                 capsys):
    """RED ON 0.325.0: the write was put back and the agent's `git log` was blamed."""
    said = _around(project, lambda: _background_write(project), capsys)
    assert (project / REC).read_text() == _derived(RECORD)
    assert "not asked first" not in json.dumps(said)
    assert not list((project / ".claude/state/bash-guard").glob("put-back/*"))


def test_without_telling_the_guard_the_write_is_put_back(project, capsys, monkeypatch):
    """The control: the test is not green by construction. With the call taken out, the race is
    the one seen in dogfood."""
    monkeypatch.setattr(bsg, "own_writer_writes", lambda *_a, **_k: None)
    said = _around(project, lambda: _background_write(project), capsys)
    assert (project / REC).read_text() == RECORD
    assert "you were not asked first" in said["reason"]


def test_a_write_landing_between_two_running_commands_is_kept_out_of_both(project, capsys):
    assert bsg.pre(_payload(project, "call-1"), project) == 0
    assert bsg.pre(_payload(project, "call-2"), project) == 0
    _background_write(project)
    assert bsg.post(_payload(project, "call-1"), project) == 0
    assert bsg.post(_payload(project, "call-2"), project) == 0
    assert "not asked first" not in capsys.readouterr().out
    assert (project / REC).read_text() == _derived(RECORD)


# ---------------------------------------------------------------- what the command did is still put back


def test_a_command_s_change_before_the_write_is_put_back_and_the_write_kept(project, capsys):
    """The writer reads the file with the command's change in it. Copying that file into the
    guard's copy would have taken the command's change for the writer's."""
    def act():
        _command_changes_the_bar(project)
        _background_write(project)

    said = _around(project, act, capsys, command="python3 tool.py")
    assert (project / REC).read_text() == _derived(RECORD)
    assert "A shell command changed .claude/diamonds/active.yml (l1-strategy)" in said["reason"]


def test_a_command_s_change_after_the_write_is_put_back_and_the_write_kept(project, capsys):
    def act():
        _background_write(project)
        _command_changes_the_bar(project)

    said = _around(project, act, capsys, command="python3 tool.py")
    assert (project / REC).read_text() == _derived(RECORD)
    assert "you were not asked first" in said["reason"]


def test_a_command_that_runs_the_writer_after_its_own_change_is_put_back(project, capsys):
    """`python3 tool.py; derive_closing_path.py --write` is not the writer run on its own, and
    running the writer afterwards does not launder what the script did."""
    def act():
        _command_changes_the_bar(project)
        dcp.write_closes_on(project, "l1-strategy", ENTRY)

    said = _around(project, act, capsys,
                   command=f"python3 tool.py; python3 {PLUGIN}/scripts/derive_closing_path.py "
                           "--all --write")
    text = (project / REC).read_text()
    assert NEW_BAR[0] in text and NEW_BAR[1] not in text
    assert "you were not asked first" in said["reason"]


# ---------------------------------------------------------------- the writer on its own


def test_the_writer_with_no_command_running_writes_as_before(project):
    assert dcp.write_closes_on(project, "l1-strategy", ENTRY) is True
    assert dcp.write_closes_on(project, "l1-strategy", ENTRY) is False
    assert (project / REC).read_text() == dcp.with_closes_on(RECORD, "l1-strategy", ENTRY)


def test_a_diamond_the_file_does_not_hold_is_not_written(project):
    assert dcp.write_closes_on(project, "l9-absent", ENTRY) is False
    assert (project / REC).read_text() == RECORD
