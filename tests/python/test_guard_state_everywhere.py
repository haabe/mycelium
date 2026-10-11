"""The files that switch a gate off are the user's to write, in every project (v0.281.0).

E2E relay on 0.280.0: the builder, running with permissions bypassed, wrote its own
`.claude/state/scale-lock-ack` ("My judgment call, my override") and opened an L4 past its lock.
The guard-state check asked, and in that mode nobody is asked; and the three guards that called it
were each conditional, so in an ordinary project nothing guarded the ack files at all.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "plugins" / "mycelium" / "scripts"
HOOK = ROOT / "plugins" / "mycelium" / "hooks" / "guard-state-gate.sh"
sys.path.insert(0, str(SCRIPTS))
import _hook_input as hi  # noqa: E402

ACK = ".claude/state/scale-lock-ack"


@pytest.fixture(autouse=True)
def _capture(capsys):
    _decide.capsys = capsys  # the guard reconfigures stdout, which pytest's capture supports


def _decide(tmp_path, monkeypatch, tool_input, mode, tool="Write"):
    monkeypatch.delenv("MYCELIUM_GUARD_STATE_EDIT", raising=False)
    (tmp_path / ".claude" / "state").mkdir(parents=True, exist_ok=True)
    capsys = _decide.capsys
    capsys.readouterr()
    try:
        hi.guard_state_check("t", tool, tool_input, str(tmp_path), mode)
    except SystemExit:
        pass
    text = capsys.readouterr().out.strip()
    return json.loads(text)["hookSpecificOutput"]["permissionDecision"] if text else "allow"


@pytest.mark.parametrize("mode", ["bypassPermissions", "auto", "dontAsk"])
def test_where_nobody_is_asked_the_agent_cannot_write_an_off_switch(tmp_path, monkeypatch, mode):
    assert _decide(tmp_path, monkeypatch, {"file_path": ACK, "content": "x"}, mode) == "deny"


@pytest.mark.parametrize("mode", ["default", "acceptEdits", "plan", None, ""])
def test_where_a_person_is_asked_it_still_asks(tmp_path, monkeypatch, mode):
    assert _decide(tmp_path, monkeypatch, {"file_path": ACK, "content": "x"}, mode) == "ask"


def test_a_shell_write_is_judged_the_same(tmp_path, monkeypatch):
    cmd = {"command": "echo 'l4-a L4 2026-10-18 mine' >> .claude/state/scale-lock-ack"}
    assert _decide(tmp_path, monkeypatch, cmd, "bypassPermissions", tool="Bash") == "deny"


# v0.318.0: with neither .claude/canvas nor .claude/diamonds every hook exits at once, so removing
# them is the widest off-switch. Found by the subagent that updated the shell tests for the prelude.

@pytest.mark.parametrize("cmd", ["rm -rf .claude/canvas", "git rm -r .claude/diamonds",
                                 "mv .claude/canvas /tmp/x", "rmdir .claude/diamonds",
                                 "rm -rf .claude", "cd app && rm -rf '../.claude/canvas'"])
def test_removing_what_makes_it_a_mycelium_project_is_a_persons_call(tmp_path, monkeypatch, cmd):
    assert _decide(tmp_path, monkeypatch, {"command": cmd}, "default", tool="Bash") == "ask"
    assert _decide(tmp_path, monkeypatch, {"command": cmd}, "bypassPermissions", tool="Bash") == "deny"


def test_an_mcp_move_of_the_canvas_is_judged_the_same(tmp_path, monkeypatch):
    move = {"source": ".claude/canvas", "destination": "/tmp/canvas"}
    assert _decide(tmp_path, monkeypatch, move, "default", tool="mcp__filesystem__move_file") == "ask"


@pytest.mark.parametrize("cmd", ["rm .claude/canvas/old.yml", "ls .claude/canvas",
                                 "cp x.yml .claude/canvas/", "rm -rf .claude/state"])
def test_control_ordinary_work_in_those_folders_is_not_asked(tmp_path, monkeypatch, cmd):
    assert _decide(tmp_path, monkeypatch, {"command": cmd}, "bypassPermissions", tool="Bash") == "allow"


def test_control_any_other_file_is_not_this_gates_business(tmp_path, monkeypatch):
    assert _decide(tmp_path, monkeypatch, {"file_path": "src/app.py", "content": "x"},
                   "bypassPermissions") == "allow"


def test_the_gate_runs_in_an_ordinary_project(tmp_path):
    """No autonomous run, no scope, no framework repo: the gate still decides."""
    (tmp_path / ".claude" / "state").mkdir(parents=True)
    (tmp_path / ".claude" / "canvas").mkdir()  # a Mycelium project (v0.318.0 prelude)
    payload = json.dumps({"tool_name": "Write", "permission_mode": "bypassPermissions",
                          "tool_input": {"file_path": ACK, "content": "x"}})
    env = {"CLAUDE_PROJECT_DIR": str(tmp_path), "PATH": "/usr/bin:/bin:" + str(Path(sys.executable).parent)}
    out = subprocess.run(["bash", str(HOOK)], input=payload, capture_output=True, text=True,
                         env=env, check=True).stdout
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"
    for manifest in ("hooks.json", "hooks.codex.json", "hooks.cursor.json"):
        assert "guard-state-gate.sh" in (HOOK.parent / manifest).read_text(), manifest


# v0.318.3: every removal test above feeds the PYTHON helper. The shell hook in front of it left
# with exit 0 on any call that named no guard-state FILE, so a marker-folder removal never reached
# the helper: asked about in Python, unreachable from the hook, in every permission mode (dogfood
# harms check 2026-10-11, replayed in a scratch project). These run the HOOK.

def _hook(tmp_path, tool, tool_input, mode):
    (tmp_path / ".claude" / "state").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".claude" / "canvas").mkdir(exist_ok=True)
    (tmp_path / ".claude" / "diamonds").mkdir(exist_ok=True)
    payload = json.dumps({"tool_name": tool, "permission_mode": mode, "tool_input": tool_input,
                          "transcript_path": "/home/someone/.claude/projects/p/t.jsonl"})
    env = {"CLAUDE_PROJECT_DIR": str(tmp_path), "PATH": "/usr/bin:/bin:" + str(Path(sys.executable).parent)}
    out = subprocess.run(["bash", str(HOOK)], input=payload, capture_output=True, text=True,
                         env=env, check=True).stdout.strip()
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else "allow"


@pytest.mark.parametrize("cmd", ["rm -rf .claude/canvas .claude/diamonds", "git rm -r .claude/diamonds",
                                 "mv .claude/canvas /tmp/x", "rmdir .claude/diamonds",
                                 "rm -rf .claude", "cd app && rm -rf '../.claude/canvas'"])
def test_the_hook_itself_judges_a_marker_folder_removal(tmp_path, cmd):
    assert _hook(tmp_path, "Bash", {"command": cmd}, "default") == "ask"
    assert _hook(tmp_path, "Bash", {"command": cmd}, "bypassPermissions") == "deny"


def test_the_hook_itself_judges_an_mcp_move_of_the_canvas(tmp_path):
    move = {"source": ".claude/canvas", "destination": "/tmp/canvas"}
    assert _hook(tmp_path, "mcp__filesystem__move_file", move, "default") == "ask"


@pytest.mark.parametrize("cmd", ["rm .claude/canvas/old.yml", "ls .claude/canvas", "git status",
                                 "confirm .claude/canvas/x.yml", "rm -rf build && ls .claude/canvas"])
def test_control_the_hook_lets_ordinary_commands_through(tmp_path, cmd):
    """Including the ones its loose first look sends to the helper: the helper still says no."""
    assert _hook(tmp_path, "Bash", {"command": cmd}, "bypassPermissions") == "allow"
