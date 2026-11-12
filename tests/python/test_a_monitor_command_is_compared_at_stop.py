"""A shell command whose after half never runs is compared at the end of the turn (v0.336.0).

WHAT WAS WRONG. Claude Code 2.1.314 runs the PreToolUse hooks matching Bash on a command the
Monitor tool starts, and no PostToolUse for it (measured 2026-11-03 on 2.1.317). The shell-state
guard snapshots the files that switch a stop off, and the diamonds file, in its before half, and
compares and puts back only in its after half. So a Monitor command that switched a stop off by a
route the before-command gates cannot read was neither put back nor reported, and its snapshot was
dropped after a day.

WHAT HOLDS NOW. At Stop (`bash_state_guard.py stop`), every snapshot of this session that is
still open is compared as its after half would have, put back, said, and removed. A file the
person was asked about while the command ran, by a shell command or an edit tool, is taken into
every open snapshot, so the end-of-turn comparison does not undo it.

The paths are built from parts so that this file's own text is not a write to guard state.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
HOOK = PLUGIN / "hooks" / "bash-state-guard.sh"
_spec = importlib.util.spec_from_file_location("bash_state_guard",
                                               PLUGIN / "scripts" / "bash_state_guard.py")
bsg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bsg)

SKIP_ACK = ".claude/state/" + "discovery-skip" + "-ack"
VIA_VARIABLE = "f=" + SKIP_ACK + '; echo "2026-11-12 mine" > "$f"'
VISIBLE = 'echo "2026-11-12 mine" > ' + SKIP_ACK
RECORD = ".claude/diamonds/active.yml"


@pytest.fixture
def project(tmp_path: Path, monkeypatch) -> Path:
    (tmp_path / ".claude" / "canvas").mkdir(parents=True)
    (tmp_path / ".claude" / "state").mkdir()
    (tmp_path / ".claude" / "diamonds").mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("MYCELIUM_GUARD_STATE_EDIT", raising=False)
    return tmp_path


def _payload(command: str = "", call: str = "mon-1", session: str = "s1", **extra) -> dict:
    return {"tool_name": "Bash", "tool_use_id": call, "session_id": session,
            "tool_input": {"command": command}, **extra}


def _stop(project: Path, capsys, session: str = "s1") -> str:
    assert bsg.stop({"session_id": session, "hook_event_name": "Stop"}, project) == 0
    return capsys.readouterr().out.strip()


def test_a_monitor_command_that_switched_a_stop_off_is_put_back_at_stop(project, capsys):
    """RED BEFORE 0.336.0: no after half ran, so the file stayed and nothing was said."""
    ack = project / SKIP_ACK
    assert bsg.pre(_payload(VIA_VARIABLE), project) == 0     # the Monitor command's before half
    ack.write_text("2026-11-12 mine\n")                       # what the command did; no post half
    said = json.loads(_stop(project, capsys))
    assert not ack.exists(), "the stop stayed off after the turn ended"
    assert said["decision"] == "block"
    assert SKIP_ACK in said["reason"] and "Monitor" in said["reason"]
    assert SKIP_ACK in said["systemMessage"] and "you were not asked" in said["systemMessage"]
    assert list((project / bsg.STATE_REL / bsg.GUARD_SNAP).iterdir()) == []
    assert _stop(project, capsys) == "", "a second Stop says it again"


def test_a_monitor_command_that_changed_the_diamonds_file_is_put_back_at_stop(project, capsys):
    """RED BEFORE 0.336.0, the diamonds half of the same hole."""
    record = project / RECORD
    record.write_text("active_diamonds: []\n")
    assert bsg.pre(_payload("python3 tool.py"), project) == 0
    record.write_text("active_diamonds: [{id: x}]\n")
    said = json.loads(_stop(project, capsys))
    assert record.read_text() == "active_diamonds: []\n"
    assert RECORD in said["reason"]


def test_the_hook_runs_the_stop_half(project):
    """Through the real hook script, as Claude Code calls it at Stop."""
    ack = project / SKIP_ACK
    env = {"PATH": os.environ["PATH"], "HOME": str(project), "TMPDIR": str(project),
           "CLAUDE_PROJECT_DIR": str(project), "CLAUDE_PLUGIN_ROOT": str(PLUGIN)}

    def run(half: str, payload: dict) -> str:
        done = subprocess.run(["bash", str(HOOK), half], input=json.dumps(payload), text=True,
                              capture_output=True, env=env, timeout=60, check=False)
        assert done.returncode == 0, done.stderr
        return done.stdout.strip()

    assert run("pre", _payload(VIA_VARIABLE)) == ""
    ack.write_text("2026-11-12 mine\n")
    out = run("stop", {"session_id": "s1", "hook_event_name": "Stop"})
    assert not ack.exists() and SKIP_ACK in json.loads(out)["reason"]


def test_stop_is_registered_in_claude_code():
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())["hooks"]
    on_stop = [h["command"] for e in hooks["Stop"] for h in e["hooks"]]
    assert any("bash-state-guard.sh" in c and c.rstrip().endswith("stop") for c in on_stop)


# ---------------------------------------------------------------- what is left alone

def test_control_a_command_whose_after_half_ran_leaves_nothing_for_stop(project, capsys):
    ack = project / SKIP_ACK
    assert bsg.pre(_payload(VIA_VARIABLE, call="b"), project) == 0
    ack.write_text("2026-11-12 mine\n")
    assert bsg.post(_payload(VIA_VARIABLE, call="b"), project) == 0
    assert "put it back" in capsys.readouterr().out
    assert _stop(project, capsys) == ""


def test_control_another_sessions_open_command_is_not_judged(project, capsys):
    """A command of another session in the same project may still be running."""
    ack = project / SKIP_ACK
    assert bsg.pre(_payload(VIA_VARIABLE, session="other"), project) == 0
    ack.write_text("2026-11-12 mine\n")
    assert _stop(project, capsys, session="s1") == ""
    assert ack.exists()


def test_control_a_visible_write_the_person_approved_meanwhile_stands(project, capsys):
    """RED WITHOUT `_take_in`: the Monitor's snapshot still held the old file, and the end-of-turn
    comparison would undo a write the person was asked about and said yes to."""
    ack = project / SKIP_ACK
    assert bsg.pre(_payload("python3 watch.py", call="mon"), project) == 0
    assert bsg.pre(_payload(VISIBLE, call="y"), project) == 0
    ack.write_text("2026-11-12 mine\n")                       # y's approved write
    assert bsg.post(_payload(VISIBLE, call="y"), project) == 0
    assert capsys.readouterr().out.strip() == ""
    assert _stop(project, capsys) == ""
    assert ack.read_text() == "2026-11-12 mine\n"


def test_control_an_edit_tool_write_the_person_approved_meanwhile_stands(project, capsys):
    """guard-state-gate.sh asks before an edit tool writes the file; `edited` takes it in."""
    ack = project / SKIP_ACK
    ack.write_text("old\n")
    assert bsg.pre(_payload("python3 watch.py", call="mon"), project) == 0
    ack.write_text("2026-11-12 mine\n")                       # the approved Write
    assert bsg.edited({"tool_name": "Write", "tool_input": {"file_path": str(ack)}}, project) == 0
    assert _stop(project, capsys) == ""
    assert ack.read_text() == "2026-11-12 mine\n"


def test_control_an_approved_removal_meanwhile_stands(project, capsys):
    ack = project / SKIP_ACK
    ack.write_text("old\n")
    assert bsg.pre(_payload("python3 watch.py", call="mon"), project) == 0
    rm = "rm " + SKIP_ACK
    assert bsg.pre(_payload(rm, call="y"), project) == 0
    ack.unlink()
    assert bsg.post(_payload(rm, call="y"), project) == 0
    assert _stop(project, capsys) == ""
    assert not ack.exists()


def test_two_commands_at_once_still_do_not_read_each_others_before(project, capsys):
    """The end-of-turn comparison does not move into another call's after half: a command still
    running in the same turn is judged by its own after half (test_guard_state_put_back)."""
    ack = project / SKIP_ACK
    assert bsg.pre(_payload(VIA_VARIABLE, call="a"), project) == 0
    ack.write_text("2026-11-12 mine\n")
    assert bsg.pre(_payload("ls", call="b"), project) == 0
    assert bsg.post(_payload("ls", call="b"), project) == 0
    assert capsys.readouterr().out.strip() == "" and ack.exists()


def test_main_routes_the_stop_mode(project, monkeypatch, capsys):
    import io
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"session_id": "s1"})))
    assert bsg.main(["stop"]) == 0
    assert capsys.readouterr().out == ""


def test_an_unreadable_open_snapshot_is_said_at_stop(project, capsys):
    """Its session cannot be read either, so it is judged here, and the comparison says that
    nothing was compared (fail-open-reviewed: bash_state_guard.py@a10d0d64f3)."""
    assert bsg.pre(_payload("python3 watch.py"), project) == 0
    (project / bsg.STATE_REL / bsg.GUARD_SNAP / "mon-1" / "index.json").write_text("{not json")
    said = json.loads(_stop(project, capsys))
    assert "WARNING" in said["systemMessage"] and "nothing was put back" in said["reason"]
