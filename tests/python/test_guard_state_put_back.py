"""A shell write the hook cannot read does not switch a stop off (v0.321.1).

WHAT WAS WRONG. `guard-state-gate.sh` asks the person before a tool call writes one of the files
that switch a blocking hook off, and it can only ask about a write target it can read. A blind
read of 0.321.0 found, and a replay through the released hook confirmed, that a shell write through
a variable or a command substitution was allowed in silence, while README.md told the reader the
agent cannot write those files and the operating contract told the agent the hooks read such
writes too.

WHAT HOLDS NOW. `bash-state-guard.sh` compares those files before and after every shell command.
One that the command created, changed or removed, and that the person was not asked about, is put
back, and the person and the agent are told (maintainer's ruling, 2026-10-11: "Put it back and tell
me"). Every test drives the real hook, both halves, around a write the test itself performs: what
is under test is the comparison, not any reading of the command.

The paths are built from parts so that this file's own text is not a write to guard state.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
HOOK = PLUGIN / "hooks" / "bash-state-guard.sh"
sys.path.insert(0, str(PLUGIN / "scripts"))
import _hook_input as hi  # noqa: E402

STATE = ".claude/state/"
SKIP_ACK = STATE + "discovery-skip" + "-ack"
LOCK_ACK = STATE + "scale-lock" + "-ack"
#: The shape that got through on 0.321.0: the target is a variable, so no hook can read it.
VIA_VARIABLE = "f=" + SKIP_ACK + '; echo "2026-10-11 mine" > "$f"'
VISIBLE = 'echo "2026-10-11 mine" > ' + SKIP_ACK


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / ".claude" / "canvas").mkdir(parents=True)
    (tmp_path / ".claude" / "state").mkdir()
    return tmp_path


def _run(project: Path, half: str, command: str, call: str = "call-1", **extra_env) -> str:
    payload = {"tool_name": "Bash", "tool_use_id": call, "permission_mode": "default",
               "session_id": "s1", "cwd": str(project), "tool_input": {"command": command}}
    env = {"PATH": os.environ["PATH"], "HOME": str(project), "TMPDIR": str(project),
           "CLAUDE_PROJECT_DIR": str(project), "CLAUDE_PLUGIN_ROOT": str(PLUGIN), **extra_env}
    done = subprocess.run(["bash", str(HOOK), half], input=json.dumps(payload), text=True,
                          capture_output=True, env=env, timeout=60, check=False)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def _around(project: Path, command: str, act, **kw) -> str:
    """The hook's before half, then what the command did, then its after half."""
    assert _run(project, "pre", command, **kw) == ""
    act()
    return _run(project, "post", command, **kw)


# ---------------------------------------------------------------- the hole, closed

def test_an_off_switch_written_through_a_variable_is_removed_and_said(project):
    """RED BEFORE 0.321.1: the file stayed, nothing was said, and the first-file stop was off."""
    ack = project / SKIP_ACK
    out = _around(project, VIA_VARIABLE, lambda: ack.write_text("2026-10-11 mine\n"))
    assert not ack.exists(), "the stop was switched off by a write nobody was asked about"
    said = json.loads(out)
    assert SKIP_ACK in said["reason"] and "put it back" in said["reason"]
    assert said["decision"] == "block"                       # the agent hears it in the same turn
    assert SKIP_ACK in said["systemMessage"]                 # and so does the person
    assert "you were not asked" in said["systemMessage"]


def test_an_existing_off_switch_changed_that_way_gets_its_old_content_back(project):
    """RED BEFORE 0.321.1. The person's own record must not be widened under them either."""
    ack = project / LOCK_ACK
    ack.write_text("l3-a L3 2026-10-01 mine, for this one diamond\n")
    out = _around(project, "f=" + LOCK_ACK + '; echo "l4-b L4 2026-10-11 also" >> "$f"',
                  lambda: ack.write_text(ack.read_text() + "l4-b L4 2026-10-11 also\n"))
    assert ack.read_text() == "l3-a L3 2026-10-01 mine, for this one diamond\n"
    assert "restored" in json.loads(out)["reason"]


def test_an_off_switch_removed_that_way_comes_back(project):
    """The person's override is theirs in both directions. RED BEFORE 0.321.1."""
    ack = project / SKIP_ACK
    ack.write_text("2026-10-01 mine\n")
    out = _around(project, "f=" + SKIP_ACK + '; rm "$f"', ack.unlink)
    assert ack.read_text() == "2026-10-01 mine\n"
    assert SKIP_ACK in json.loads(out)["reason"]


def test_every_off_switch_file_is_covered(project):
    """The list is `_hook_input.GUARD_STATE_REL`, read here so a file added there is tested."""
    def write_all():
        for rel in hi.GUARD_STATE_REL:
            f = project / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("x\n")
    out = _around(project, 'for f in $FILES; do echo x > "$f"; done', write_all)
    assert [rel for rel in hi.GUARD_STATE_REL if (project / rel).exists()] == []
    assert all(rel in out for rel in hi.GUARD_STATE_REL)


def test_a_command_that_fails_is_checked_too():
    """RED BEFORE 0.321.1: the after half ran on PostToolUse only, so a command that wrote the
    file and then exited non-zero was never compared. Both runtimes with a failure event register
    it there; Codex reports failures on PostToolUse."""
    claude = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())["hooks"]
    on_failure = [h["command"] for e in claude["PostToolUseFailure"] for h in e["hooks"]]
    assert any("bash-state-guard.sh" in c and c.rstrip().endswith("post") for c in on_failure)
    cursor = json.loads((PLUGIN / "hooks" / "hooks.cursor.json").read_text())["hooks"]
    assert any("bash-state-guard.sh" in e["command"] and e["command"].rstrip().endswith("post")
               for e in cursor["postToolUseFailure"])


def test_two_commands_at_once_do_not_read_each_others_before(project):
    """Each call compares against its OWN before. With one shared snapshot, a second command
    starting while the first runs would overwrite the first's "before" with a state that already
    holds the first's write, and the first would then find nothing to put back."""
    ack = project / SKIP_ACK
    assert _run(project, "pre", VIA_VARIABLE, call="a") == ""
    ack.write_text("2026-10-11 mine\n")                      # what call a did
    assert _run(project, "pre", "ls", call="b") == ""        # b starts while a is still running
    assert _run(project, "post", "ls", call="b") == ""       # b changed nothing, so says nothing
    assert ack.exists()
    out = _run(project, "post", VIA_VARIABLE, call="a")      # a is judged against a's before
    assert not ack.exists()
    assert SKIP_ACK in json.loads(out)["reason"]


# ---------------------------------------------------------------- what is left alone

def test_control_a_visible_write_the_person_was_asked_about_stands(project):
    """`guard-state-gate.sh` asks about this one; a command that then runs was approved."""
    ack = project / SKIP_ACK
    out = _around(project, VISIBLE, lambda: ack.write_text("2026-10-11 mine\n"))
    assert ack.read_text() == "2026-10-11 mine\n"
    assert out == ""


def test_control_a_command_that_touches_none_of_them_says_nothing(project):
    ack = project / SKIP_ACK
    ack.write_text("2026-10-01 mine\n")
    notes = project / "notes.txt"
    out = _around(project, "echo hello > notes.txt", lambda: notes.write_text("hello\n"))
    assert out == "" and notes.read_text() == "hello\n" and ack.read_text() == "2026-10-01 mine\n"


def test_control_the_persons_own_setup_switch_is_honoured(project):
    """`MYCELIUM_GUARD_STATE_EDIT=1` in the person's own shell already lifts the ask (gate.sh)."""
    ack = project / SKIP_ACK
    out = _around(project, VIA_VARIABLE, lambda: ack.write_text("2026-10-11 mine\n"),
                  MYCELIUM_GUARD_STATE_EDIT="1")
    assert ack.exists() and out == ""


def test_control_myceliums_own_upgrade_script_is_not_undone(project):
    manifest = project / ".claude" / "manifest.yml"
    out = _around(project, "bash plugins/mycelium/scripts/upgrade.sh",
                  lambda: manifest.write_text("framework: {}\n"))
    assert manifest.exists() and out == ""


def test_naming_the_upgrade_script_beside_another_command_is_not_a_pass(project):
    """Only the script run on its own. A comment or a chained command does not borrow its name."""
    ack = project / SKIP_ACK
    for i, command in enumerate((VIA_VARIABLE + "  # then upgrade.sh",
                                 "bash upgrade.sh; " + VIA_VARIABLE)):
        out = _around(project, command, lambda: ack.write_text("2026-10-11 mine\n"), call=f"c{i}")
        assert not ack.exists(), command
        assert out != ""


def test_nothing_else_is_ever_undone(project):
    """The put-back is for the off-switch files only. Code and canvas the command wrote stay."""
    code = project / "app.py"
    canvas = project / ".claude" / "canvas" / "notes.md"
    ack = project / SKIP_ACK

    def act():
        code.write_text("x = 1\n")
        canvas.write_text("a note\n")
        ack.write_text("2026-10-11 mine\n")

    _around(project, VIA_VARIABLE, act)
    assert code.read_text() == "x = 1\n" and canvas.read_text() == "a note\n"
    assert not ack.exists()


def test_the_snapshot_is_cleaned_up(project):
    ack = project / SKIP_ACK
    _around(project, VIA_VARIABLE, lambda: ack.write_text("2026-10-11 mine\n"))
    snaps = project / ".claude" / "state" / "bash-guard" / "guard-state"
    assert not snaps.exists() or list(snaps.iterdir()) == []
