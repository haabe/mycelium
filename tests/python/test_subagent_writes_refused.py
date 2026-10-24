"""A subagent does not write the canvas or the diamonds file (v0.330.0).

orchestration/agent-teams.md and fan-out-fan-in.md have said since May that workers never update
canvas files and never progress diamonds; only the lead agent does. No hook read who was writing,
so the rule was prose (dogfood review 2026-10-24, against Anthropic's 2026-10-22 article on folding
subagents into the main loop). Claude Code puts `agent_id` on a PreToolUse payload when the call
comes from a subagent or an in-process teammate; the guard-state gate now refuses such a call when
it writes under .claude/canvas/ or .claude/diamonds/.
"""
import io
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

SUB = {"agent_id": "a1b2c3", "agent_type": "general-purpose"}


@pytest.fixture(autouse=True)
def _capture(capsys):
    _decide.capsys = capsys


def _project(tmp_path):
    for d in ("state", "canvas", "diamonds"):
        (tmp_path / ".claude" / d).mkdir(parents=True, exist_ok=True)


def _decide(tmp_path, tool, tool_input, who):
    _project(tmp_path)
    capsys = _decide.capsys
    capsys.readouterr()
    try:
        hi.subagent_write_check("t", {"tool_name": tool, "tool_input": tool_input, **who},
                                str(tmp_path))
    except SystemExit:
        pass
    text = capsys.readouterr().out.strip()
    return json.loads(text)["hookSpecificOutput"] if text else None


@pytest.mark.parametrize(("tool", "tool_input"), [
    ("Write", {"file_path": ".claude/canvas/landscape.yml", "content": "x"}),
    ("Edit", {"file_path": ".claude/diamonds/active.yml", "old_string": "a", "new_string": "b"}),
    ("MultiEdit", {"file_path": ".claude/canvas/opportunities.yml",
                   "edits": [{"old_string": "a", "new_string": "b"}]}),
    ("NotebookEdit", {"notebook_path": ".claude/canvas/x.ipynb", "new_source": "x"}),
    ("mcp__filesystem__write_file", {"path": ".claude/canvas/purpose.yml", "content": "x"}),
    ("mcp__filesystem__move_file", {"source": ".claude/canvas/purpose.yml",
                                    "destination": "/tmp/purpose.yml"}),
    ("Bash", {"command": "echo '- id: comp-999' >> .claude/canvas/landscape.yml"}),
    ("Bash", {"command": "cd .claude && printf x > diamonds/active.yml"}),
])
def test_a_subagent_write_to_the_lead_only_files_is_refused(tmp_path, tool, tool_input):
    out = _decide(tmp_path, tool, tool_input, SUB)
    assert out is not None and out["permissionDecision"] == "deny"
    assert "general-purpose" in out["permissionDecisionReason"]
    assert "lead agent" in out["permissionDecisionReason"]


def test_a_shell_write_the_scan_cannot_read_is_refused_when_it_names_the_canvas(tmp_path):
    cmd = {"command": 'f=.claude/canvas/landscape.yml; echo x > "$f"'}
    scan = hi.bash_write_targets(cmd["command"], str(tmp_path))
    assert scan.opaque, "the fixture must be a write the scan cannot read"
    out = _decide(tmp_path, "Bash", cmd, SUB)
    assert out is not None and out["permissionDecision"] == "deny"
    assert "cannot read" in out["permissionDecisionReason"]


def test_the_reason_names_a_subagent_when_the_type_is_missing(tmp_path):
    out = _decide(tmp_path, "Write", {"file_path": ".claude/canvas/a.yml", "content": "x"},
                  {"agent_id": "x"})
    assert out is not None and out["permissionDecisionReason"].startswith("Mycelium t: a subagent")


@pytest.mark.parametrize("who", [{}, {"agent_type": "my-main-agent"}, {"agent_id": ""}])
def test_control_the_main_session_writes_the_canvas_as_before(tmp_path, who):
    """No agent_id: the main session, including one started with --agent (agent_type only)."""
    assert _decide(tmp_path, "Write", {"file_path": ".claude/canvas/a.yml", "content": "x"},
                   who) is None


@pytest.mark.parametrize(("tool", "tool_input"), [
    ("Write", {"file_path": "src/app.py", "content": "x"}),
    ("Write", {"file_path": ".claude/canvas-notes/x.md", "content": "x"}),
    ("Write", {"file_path": ".claude/state/scratch.json", "content": "x"}),
    ("Write", {"file_path": "docs/canvas/notes.md", "content": "x"}),
    ("Bash", {"command": "ls .claude/canvas"}),
    ("Bash", {"command": "cat .claude/diamonds/active.yml"}),
    ("Bash", {"command": "grep -n comp- .claude/canvas/landscape.yml > /tmp/out.txt"}),
])
def test_control_a_subagent_reads_the_canvas_and_writes_elsewhere(tmp_path, tool, tool_input):
    assert _decide(tmp_path, tool, tool_input, SUB) is None


@pytest.mark.parametrize(("rel", "lead_only"), [
    (None, False), ("", False), (".claude/canvas", True), (".claude/canvas/a.yml", True),
    (".claude/diamonds/active.yml", True), (".claude/canvasx/a.yml", False), ("canvas/a.yml", False),
])
def test_which_paths_are_the_leads(rel, lead_only):
    assert hi._lead_only(rel) is lead_only


def test_the_gate_entry_point_runs_the_check(tmp_path, monkeypatch, capsys):
    """_guard_state_hook is what the shell hook calls; the check must sit inside it."""
    _project(tmp_path)
    monkeypatch.delenv("MYCELIUM_GUARD_STATE_EDIT", raising=False)
    payload = {"tool_name": "Write", "permission_mode": "default", **SUB,
               "tool_input": {"file_path": ".claude/canvas/a.yml", "content": "x"}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    with pytest.raises(SystemExit):
        hi._guard_state_hook("guard-state-gate", str(tmp_path))
    assert json.loads(capsys.readouterr().out)["hookSpecificOutput"]["permissionDecision"] == "deny"


# Through the shell hook, whose cheap first look decides whether python runs at all.

def _hook(tmp_path, tool, tool_input, who):
    _project(tmp_path)
    payload = json.dumps({"tool_name": tool, "permission_mode": "default",
                          "tool_input": tool_input, **who})
    env = {"CLAUDE_PROJECT_DIR": str(tmp_path),
           "PATH": "/usr/bin:/bin:" + str(Path(sys.executable).parent)}
    out = subprocess.run(["bash", str(HOOK)], input=payload, capture_output=True, text=True,
                         env=env, check=True).stdout.strip()
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else "allow"


@pytest.mark.parametrize(("tool", "tool_input"), [
    ("Write", {"file_path": ".claude/canvas/landscape.yml", "content": "x"}),
    ("Edit", {"file_path": ".claude/diamonds/active.yml", "old_string": "a", "new_string": "b"}),
    ("Bash", {"command": "echo x >> .claude/canvas/landscape.yml"}),
])
def test_the_hook_itself_refuses_a_subagent_write(tmp_path, tool, tool_input):
    assert _hook(tmp_path, tool, tool_input, SUB) == "deny"


@pytest.mark.parametrize(("tool", "tool_input", "who"), [
    ("Write", {"file_path": ".claude/canvas/landscape.yml", "content": "x"}, {}),
    ("Write", {"file_path": "src/canvas.py", "content": "x"}, SUB),
    ("Bash", {"command": "ls .claude/canvas"}, SUB),
])
def test_control_the_hook_lets_the_rest_through(tmp_path, tool, tool_input, who):
    assert _hook(tmp_path, tool, tool_input, who) == "allow"
