"""A shell command that no hook can read does not take the scope hold off (v0.324.0).

WHAT WAS WRONG, found while the hold was being built and before any release carried it. The hold
reads the folders a delivery cycle may write to from `.claude/diamonds/active.yml`. A write that
names, changes or removes them is put to the person by `scope-gate.sh`, and a shell command that
visibly writes that file is refused by `bash-state-guard.sh`. A script whose command line names no
file (`python3 tool.py`) is neither: tried in a scratch project, it could delete the record, take
the folders off it, or empty the list, and afterwards nothing was said and an outside write passed.
The fourteen steps the idea had been held to did not cover it.

WHAT HOLDS NOW. `bash-state-guard.sh` keeps a copy of the diamonds file with each command's
snapshot and compares what every delivery cycle names afterwards. If the command changed it, the
whole file is put back as that copy, and the person and the agent are told (maintainer's ruling
2026-10-13: "Put it back, tell me"; the cost was said to him: anything else that command changed
in the file is undone with it). A change that came through the edit tools while the command ran
is not the command's: `diamond-state-audit.sh` refreshes the copy when one lands.

Every test drives both halves around a change the test itself makes, standing in for the command:
what is under test is the comparison, not any reading of the command.
"""

from __future__ import annotations

import io
import json
import os
import site
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
HOOKS = PLUGIN / "hooks"
sys.path.insert(0, str(PLUGIN / "scripts"))
import bash_state_guard as bsg  # noqa: E402
import scope_check  # noqa: E402

REC = ".claude/diamonds/active.yml"
OPAQUE = "python3 tool.py"  # names nothing a hook can read
FOLDERS = "  in_scope_paths: [app/billing/]\n"
RECORD = ("active_diamonds:\n- id: l4-billing\n  scale: L4\n  confidence: 0.5\n  phase: deliver\n"
          "  parent: null\n  children: []\n  created: '2026-10-01'\n  last_updated: '2026-10-02'\n"
          "  evidence: []\n  blockers: []\n  decisions:\n"
          "  - {decision: set_target, on: '2026-10-01'}\n"
          "  - {decision: start_experiment, on: '2026-10-02'}\n"
          "  - {decision: commit_to_build, on: '2026-10-02'}\n"
          + FOLDERS + "completed_diamonds: []\n")


@pytest.fixture
def project(tmp_path: Path, monkeypatch) -> Path:
    for sub in (".claude/canvas", ".claude/diamonds", ".claude/state", "app/billing", "app/users"):
        (tmp_path / sub).mkdir(parents=True)
    (tmp_path / REC).write_text(RECORD)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("MYCELIUM_GUARD_STATE_EDIT", raising=False)
    return tmp_path


def _payload(project: Path, command: str = OPAQUE, call: str = "call-1") -> dict:
    return {"tool_name": "Bash", "tool_use_id": call, "permission_mode": "default",
            "session_id": "s1", "cwd": str(project), "tool_input": {"command": command}}


def _around(project: Path, act, capsys, command: str = OPAQUE, call: str = "call-1") -> dict:
    """The guard's before half, then what the command did, then its after half. Returns what the
    after half printed, as a dict ({} when it said nothing)."""
    assert bsg.pre(_payload(project, command, call), project) == 0
    capsys.readouterr()
    act()
    assert bsg.post(_payload(project, command, call), project) == 0
    out = capsys.readouterr().out.strip()
    return json.loads(out) if out else {}


def _outside_write(project: Path) -> str:
    """What the scope hold answers for a write outside the named folder, through its hook."""
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Write", "permission_mode": "default",
               "cwd": str(project), "session_id": "s1",
               "tool_input": {"file_path": str(project / "app/users/a.py"), "content": "x"}}
    env = {"PATH": os.environ["PATH"], "HOME": str(project), "TMPDIR": str(project),
           "CLAUDE_PROJECT_DIR": str(project), "CLAUDE_PLUGIN_ROOT": str(PLUGIN),
           "PYTHONUSERBASE": site.getuserbase()}
    done = subprocess.run(["bash", str(HOOKS / "scope-gate.sh")], input=json.dumps(payload),
                          text=True, capture_output=True, env=env, cwd=project, timeout=60,
                          check=False)
    assert done.returncode == 0, done.stderr[:300]
    return json.loads(done.stdout)["hookSpecificOutput"]["permissionDecision"] if done.stdout.strip() else "allow"


# ---------------------------------------------------------------- the hole, closed


@pytest.mark.parametrize(("what", "left", "says"), [
    ("the record is deleted", None, "took the cycle out of the record"),
    ("the folders line is taken out", RECORD.replace(FOLDERS, ""), "the command left nothing said"),
    ("the list is emptied", RECORD.replace("[app/billing/]", "[]"), "the command left no hold"),
    ("another folder is added", RECORD.replace("[app/billing/]", "[app/billing/, app/users/]"),
     "the command left app/billing/, app/users/"),
])
def test_a_command_that_changes_the_folders_is_undone_and_said(project, capsys, what, left, says):
    """RED BEFORE THIS WAS BUILT: nothing was said, and the outside write below passed."""
    rec = project / REC

    def act():
        if left is None:
            rec.unlink()
        else:
            rec.write_text(left)

    said = _around(project, act, capsys)
    assert rec.read_text() == RECORD, f"{what}: the record was not put back"
    assert said["decision"] == "block"
    for text in (said["reason"], said["systemMessage"]):
        assert "you were not asked first" in text and "delivery cycle l4-billing: was app/billing/" in text
        assert says in text and "put .claude/diamonds/active.yml back" in text
        assert "undone with it" in text
    assert "Do not try another way" in said["reason"]
    assert _outside_write(project) == "ask", "the hold is not on again"


def test_what_else_the_command_changed_in_the_record_goes_with_it(project, capsys):
    """The cost said to the maintainer: the whole file is put back, not the one line."""
    rec = project / REC
    said = _around(project, lambda: rec.write_text(
        RECORD.replace(FOLDERS, "").replace("confidence: 0.5", "confidence: 0.9")), capsys)
    assert rec.read_text() == RECORD and "undone with it" in said["reason"]


def test_a_command_that_leaves_the_folders_alone_is_undone_without_naming_them(project, capsys):
    """Until 0.325.0 this was left: the check spoke only about the folders. Now any change a shell
    command makes to the record is put back (test_bash_state_guard.py has the 2026-10-14 case);
    the folders are named only when they changed."""
    rec = project / REC
    changed = RECORD.replace("last_updated: '2026-10-02'", "last_updated: '2026-10-13'")
    said = _around(project, lambda: rec.write_text(changed), capsys)
    assert rec.read_text() == RECORD
    assert "where a delivery cycle may write" not in json.dumps(said)
    assert "changed .claude/diamonds/active.yml (l4-billing)" in said["reason"]


def test_a_command_that_touches_nothing_says_nothing(project, capsys):
    assert _around(project, lambda: None, capsys) == {}
    assert (project / REC).read_text() == RECORD


def test_a_cycle_moved_to_the_completed_list_with_its_folders_is_not_a_change(project, capsys):
    """How a close is recorded. Mycelium's own writers touch the record from the shell too, and
    run on their own they are not put back (v0.325.0)."""
    rec = project / REC
    cycle = RECORD.split("active_diamonds:\n")[1].split("completed_diamonds")[0]
    moved = "active_diamonds: []\ncompleted_diamonds:\n" + cycle
    said = _around(project, lambda: rec.write_text(moved), capsys,
                   command=f"python3 {PLUGIN}/scripts/migrate_phase.py --project-dir .")
    assert rec.read_text() == moved
    assert "where a delivery cycle may write" not in json.dumps(said)


# ---------------------------------------------------------------- what is not put back


def test_a_record_the_command_created_is_said_and_left(project, capsys):
    rec = project / REC
    rec.unlink()
    said = _around(project, lambda: rec.write_text(RECORD), capsys)
    assert rec.read_text() == RECORD
    assert "there was no diamonds file before the command" in said["reason"]
    assert "was nothing said, the command left app/billing/" in said["reason"]


def test_with_the_person_s_override_on_nothing_is_put_back(project, capsys, monkeypatch):
    monkeypatch.setenv("MYCELIUM_GUARD_STATE_EDIT", "1")
    rec = project / REC
    changed = RECORD.replace(FOLDERS, "")
    said = _around(project, lambda: rec.write_text(changed), capsys)
    assert rec.read_text() == changed
    assert "where a delivery cycle may write" not in json.dumps(said)


def test_an_override_the_command_set_for_itself_does_not_count(project, capsys, monkeypatch):
    """The override is read BEFORE the command, as for the other files that are put back."""
    rec = project / REC

    def act():
        monkeypatch.setenv("MYCELIUM_GUARD_STATE_EDIT", "1")
        rec.write_text(RECORD.replace(FOLDERS, ""))

    _around(project, act, capsys)
    assert rec.read_text() == RECORD


def test_a_change_the_edit_tool_made_while_the_command_ran_is_not_the_command_s(project, capsys):
    """The person said yes to new folders through the edit tool while a long command was running.
    The copy is refreshed when that write lands, so the command is not held to have made it."""
    rec = project / REC
    approved = RECORD.replace("[app/billing/]", "[app/billing/, app/users/]")

    def act():
        rec.write_text(approved)
        edit = {"tool_name": "Edit", "session_id": "s1", "cwd": str(project),
                "tool_input": {"file_path": str(rec), "old_string": "a", "new_string": "b"}}
        assert bsg.edited(edit, project) == 0

    said = _around(project, act, capsys)
    assert rec.read_text() == approved
    assert "where a delivery cycle may write" not in json.dumps(said)


def test_and_what_the_command_did_after_that_edit_is_still_undone(project, capsys):
    rec = project / REC
    approved = RECORD.replace("[app/billing/]", "[app/billing/, app/users/]")

    def act():
        rec.write_text(approved)
        bsg.edited({"tool_name": "Write", "tool_input": {"file_path": str(rec), "content": ""}},
                   project)
        rec.write_text(approved.replace("  in_scope_paths: [app/billing/, app/users/]\n", ""))

    said = _around(project, act, capsys)
    assert rec.read_text() == approved, "put back to what the person said yes to, not further"
    assert "was app/billing/, app/users/, the command left nothing said" in said["reason"]


def test_an_edit_to_another_file_refreshes_nothing(project, capsys):
    rec = project / REC

    def act():
        rec.write_text(RECORD.replace(FOLDERS, ""))
        other = {"tool_name": "Edit", "tool_input": {"file_path": str(project / "app/users/a.py"),
                                                     "old_string": "a", "new_string": "b"}}
        assert bsg.edited(other, project) == 0
        assert bsg.edited({"tool_name": "Edit", "tool_input": {"file_path": ["not", "a path"]}},
                          project) == 0

    _around(project, act, capsys)
    assert rec.read_text() == RECORD


def test_two_commands_at_once_each_keep_their_own_copy(project, capsys):
    """The second command's before half must not hide what the first command did."""
    rec = project / REC
    assert bsg.pre(_payload(project, call="first"), project) == 0
    rec.write_text(RECORD.replace(FOLDERS, ""))
    assert bsg.pre(_payload(project, "ls", call="second"), project) == 0
    capsys.readouterr()
    assert bsg.post(_payload(project, call="first"), project) == 0
    assert "you were not asked first" in capsys.readouterr().out
    assert rec.read_text() == RECORD


def test_a_snapshot_from_an_earlier_version_is_left_alone(project, capsys):
    """A command that was running across the upgrade: its snapshot keeps no copy to put back."""
    rec = project / REC
    changed = RECORD.replace(FOLDERS, "")

    def act():
        index = project / ".claude/state/bash-guard" / bsg.GUARD_SNAP / "call-1" / "index.json"
        data = json.loads(index.read_text())
        del data["record"]
        index.write_text(json.dumps(data))
        rec.write_text(changed)

    _around(project, act, capsys)
    assert rec.read_text() == changed


def test_when_it_cannot_be_put_back_that_is_what_is_said(project, capsys, monkeypatch):
    rec = project / REC
    changed = RECORD.replace(FOLDERS, "")

    def refuse(*_a, **_k):
        raise PermissionError("no")

    def act():
        rec.write_text(changed)
        monkeypatch.setattr(bsg, "_replace_text", refuse)

    said = _around(project, act, capsys)
    assert "COULD NOT BE PUT BACK (PermissionError)" in said["reason"]
    assert "Mycelium has not changed that file" in said["systemMessage"]
    assert rec.read_text() == changed


def test_when_the_hold_s_own_script_cannot_be_loaded_that_is_said(project, capsys, monkeypatch):
    rec = project / REC
    real = bsg._load  # the loader is what is being failed here

    def act():
        rec.write_text(RECORD.replace(FOLDERS, ""))
        monkeypatch.setattr(bsg, "_load", lambda name: None if name == "scope_check" else real(name))

    said = _around(project, act, capsys)
    assert "the folders could not be compared" in said["reason"]
    assert "the scope hold's own script could not be loaded" in said["reason"]


# ---------------------------------------------------------------- the helper's own words


@pytest.mark.parametrize(("before", "after", "expected"), [
    (RECORD, RECORD, []),
    (None, None, []),
    (RECORD, None, [("delivery cycle l4-billing: was app/billing/, and the command took the "
                     "cycle out of the record")]),
    (RECORD.replace(FOLDERS, ""), RECORD,
     ["delivery cycle l4-billing: was nothing said, the command left app/billing/"]),
    (RECORD.replace("[app/billing/]", "[]"), RECORD,
     ["delivery cycle l4-billing: was no hold, the command left app/billing/"]),
    (RECORD, "active_diamonds: [not closed\n", []),
    ("- a list\n", RECORD, []),
])
def test_changed_between_says_one_line_per_cycle(before, after, expected):
    assert scope_check.changed_between(before, after) == expected


# ---------------------------------------------------------------- through the real hooks


def _hook(project: Path, hook: str, payload: dict, *args: str) -> str:
    env = {"PATH": os.environ["PATH"], "HOME": str(project), "TMPDIR": str(project),
           "CLAUDE_PROJECT_DIR": str(project), "CLAUDE_PLUGIN_ROOT": str(PLUGIN),
           "PYTHONUSERBASE": site.getuserbase()}
    done = subprocess.run(["bash", str(HOOKS / hook), *args], input=json.dumps(payload), text=True,
                          capture_output=True, env=env, cwd=project, timeout=60, check=False)
    assert done.returncode == 0, done.stderr[:300]
    return done.stdout.strip()


def test_through_the_hooks_as_the_runtime_calls_them(project):
    """Both halves of bash-state-guard.sh around a change, and diamond-state-audit.sh for the
    edit tool: the wiring, which the in-process tests above do not exercise."""
    rec = project / REC
    assert _hook(project, "bash-state-guard.sh", _payload(project), "pre") == ""
    rec.write_text(RECORD.replace(FOLDERS, ""))
    said = json.loads(_hook(project, "bash-state-guard.sh", _payload(project), "post"))
    assert "you were not asked first" in said["systemMessage"] and rec.read_text() == RECORD

    approved = RECORD.replace("[app/billing/]", "[app/billing/, app/users/]")
    assert _hook(project, "bash-state-guard.sh", _payload(project, call="call-2"), "pre") == ""
    rec.write_text(approved)
    _hook(project, "diamond-state-audit.sh",
          {"tool_name": "Edit", "session_id": "s1", "cwd": str(project),
           "tool_input": {"file_path": str(rec), "old_string": "a", "new_string": "b"}})
    out = _hook(project, "bash-state-guard.sh", _payload(project, call="call-2"), "post")
    assert "where a delivery cycle may write" not in out and rec.read_text() == approved


def test_the_entry_point_takes_the_third_mode(project, monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"tool_name": "Edit", "tool_input": {"file_path": str(project / REC)}})))
    assert bsg.main(["edited"]) == 0
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
    assert bsg.main(["something-else"]) == 0
