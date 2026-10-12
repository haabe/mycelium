"""A Mycelium switch set in a Claude Code settings file is the person's to set (v0.322.6).

WHAT WAS WRONG. Three environment variables loosen a Mycelium stop, and a hook cannot tell who set
a variable. Claude Code takes variables from the `env` block of a settings file, re-reads the file
while a session runs, and has two more keys that end every hook: `disableAllHooks`, and
`enabledPlugins` with the plugin set to false. No Mycelium gate looked at a write to those files.
Replayed 2026-10-12 on 0.322.1: a tool call putting `MYCELIUM_GUARD_STATE_EDIT` into
`.claude/settings.local.json` drew no decision from any gate; in the same replay a write to
`discovery-skip-ack` was asked about.

WHAT HOLDS NOW. A file tool that would leave a NEW Mycelium switch in a settings file asks the
person, or is refused where nobody is asked. A shell command that leaves one has it taken out
again, with the rest of the file kept, and the person is told; the plugin switched off in
`enabledPlugins` is reported and left alone, because Claude Code's own plugin commands write it.
An ordinary settings edit is not asked about. Every hook test drives the real hook script.

Not shown here: anything in a live session. That Claude Code hands the `env` block to hook
commands, and re-reads it mid-session, is its documentation's statement, not a test.
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
GATE = PLUGIN / "hooks" / "guard-state-gate.sh"
SHELL_GUARD = PLUGIN / "hooks" / "bash-state-guard.sh"
sys.path.insert(0, str(PLUGIN / "scripts"))
import settings_switches as ss  # noqa: E402

LOCAL = ".claude/settings.local.json"
SHARED = ".claude/settings.json"
OVERRIDE = "MYCELIUM_GUARD_STATE_" + "EDIT"
ORDINARY = {"permissions": {"allow": ["Bash(npm test)"]}, "env": {"NODE_ENV": "test"}}


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A Mycelium project in a folder of its own, with a separate home folder beside it."""
    proj = tmp_path / "proj"
    (proj / ".claude" / "canvas").mkdir(parents=True)
    (proj / ".claude" / "state").mkdir()
    (proj / LOCAL).write_text(json.dumps(ORDINARY, indent=2) + "\n")
    (tmp_path / "home" / ".claude").mkdir(parents=True)
    return proj


def _env(project: Path, **extra) -> dict:
    return {"PATH": os.environ["PATH"], "HOME": str(project.parent / "home"),
            "TMPDIR": str(project.parent), "CLAUDE_PROJECT_DIR": str(project),
            "CLAUDE_PLUGIN_ROOT": str(PLUGIN), **extra}


def _gate(project: Path, tool: str, tool_input: dict, mode: str = "default", **extra) -> dict:
    payload = {"tool_name": tool, "tool_input": tool_input, "permission_mode": mode,
               "cwd": str(project), "session_id": "s1"}
    done = subprocess.run(["bash", str(GATE)], input=json.dumps(payload), text=True,
                          capture_output=True, env=_env(project, **extra), timeout=60, check=False)
    assert done.returncode == 0, done.stderr
    out = done.stdout.strip()
    return json.loads(out)["hookSpecificOutput"] if out else {}


def _write(project: Path, rel: str, doc: dict) -> dict:
    return {"file_path": str(project / rel), "content": json.dumps(doc, indent=2)}


def _with(**changes) -> dict:
    doc = json.loads(json.dumps(ORDINARY))
    for key, value in changes.items():
        if key == "env":
            doc["env"].update(value)
        else:
            doc[key] = value
    return doc


# ---------------------------------------------------------------- a file tool, before the write


def test_control_an_ordinary_settings_edit_is_not_asked_about(project):
    more = _with(permissions={"allow": ["Bash(npm test)", "Bash(ls)"]})
    assert _gate(project, "Write", _write(project, LOCAL, more)) == {}


@pytest.mark.parametrize("rel", [LOCAL, SHARED])
@pytest.mark.parametrize("doc", [
    _with(env={OVERRIDE: "1"}),
    _with(env={"MYCELIUM_NEXT_ACTION_CHECK": "off"}),
    _with(env={"MYCELIUM_TODAY": "2020-01-01"}),
    _with(env={"CLAUDE_PLUGIN_ROOT": "/somewhere/else"}),
    _with(disableAllHooks=True),
    _with(enabledPlugins={"mycelium@haabe-mycelium": False}),
], ids=["override", "next-action", "today", "plugin-root", "all-hooks-off", "plugin-off"])
def test_a_write_that_sets_a_switch_asks_the_person(project, rel, doc):
    """RED BEFORE 0.322.6: no decision at all."""
    said = _gate(project, "Write", _write(project, rel, doc))
    assert said.get("permissionDecision") == "ask", said
    assert rel in said["permissionDecisionReason"]


def test_the_question_names_what_would_be_set(project):
    said = _gate(project, "Write", _write(project, LOCAL, _with(env={OVERRIDE: "1"})))
    assert f"env.{OVERRIDE}=1" in said["permissionDecisionReason"]


@pytest.mark.parametrize("mode", ["auto", "bypassPermissions", "dontAsk"])
def test_where_nobody_is_asked_it_is_refused(project, mode):
    """The same rule as the other files that switch a stop off (v0.281.0)."""
    said = _gate(project, "Write", _write(project, LOCAL, _with(env={OVERRIDE: "1"})), mode=mode)
    assert said.get("permissionDecision") == "deny", said


def test_a_runtime_that_cannot_ask_is_refused_too(project):
    """Codex treats a hook's ask as an allow (v0.286.0), so there the answer is no."""
    said = _gate(project, "Write", _write(project, LOCAL, _with(env={OVERRIDE: "1"})),
                 MYCELIUM_RUNTIME="codex")
    assert said.get("permissionDecision") == "deny", said


def test_an_edit_is_judged_by_what_it_leaves_not_by_its_own_words(project):
    """RED BEFORE 0.322.6. The new text alone names no switch: `true` replaces `false`."""
    (project / LOCAL).write_text(json.dumps(_with(disableAllHooks=False), indent=2))
    edit = {"file_path": str(project / LOCAL), "old_string": '"disableAllHooks": false',
            "new_string": '"disableAllHooks": true'}
    assert _gate(project, "Edit", edit).get("permissionDecision") == "ask"


def test_control_an_edit_that_leaves_an_existing_switch_as_it_was_is_not_asked(project):
    """The person set it; an unrelated edit to the same file is ordinary work."""
    (project / LOCAL).write_text(json.dumps(_with(env={"MYCELIUM_TODAY": "2026-01-01"}), indent=2))
    edit = {"file_path": str(project / LOCAL), "old_string": '"NODE_ENV": "test"',
            "new_string": '"NODE_ENV": "ci"'}
    assert _gate(project, "Edit", edit) == {}


def test_changing_a_switchs_value_is_a_new_switch(project):
    (project / LOCAL).write_text(json.dumps(_with(env={"MYCELIUM_TODAY": "2026-01-01"}), indent=2))
    edit = {"file_path": str(project / LOCAL), "old_string": "2026-01-01",
            "new_string": "2020-01-01"}
    assert _gate(project, "Edit", edit).get("permissionDecision") == "ask"


def test_control_taking_a_switch_out_is_not_asked_about(project):
    (project / LOCAL).write_text(json.dumps(_with(env={"MYCELIUM_TODAY": "2020-01-01"}), indent=2))
    assert _gate(project, "Write", _write(project, LOCAL, ORDINARY)) == {}


def test_an_edit_whose_result_cannot_be_worked_out_asks(project):
    edit = {"file_path": str(project / LOCAL), "old_string": "not in the file",
            "new_string": f'"{OVERRIDE}": "1"'}
    said = _gate(project, "Edit", edit)
    assert said.get("permissionDecision") == "ask" and "cannot work out" in str(said)


def test_a_move_onto_the_settings_file_is_judged_by_the_file_moved(project):
    staged = project / "staged.json"
    staged.write_text(json.dumps(_with(disableAllHooks=True)))
    move = {"source": str(staged), "destination": str(project / LOCAL)}
    said = _gate(project, "mcp__filesystem__move_file", move)
    assert said.get("permissionDecision") == "ask", said


def test_the_settings_file_in_the_home_folder_is_covered(project):
    """RED BEFORE 0.322.6. It applies to every project, and is outside this one."""
    home = project.parent / "home" / ".claude" / "settings.json"
    write = {"file_path": str(home), "content": json.dumps({"env": {OVERRIDE: "1"}})}
    said = _gate(project, "Write", write)
    assert said.get("permissionDecision") == "ask" and "~/.claude/settings.json" in str(said)


def test_control_another_json_file_that_names_a_switch_is_not_asked_about(project):
    notes = {"file_path": str(project / "docs" / "settings.json"),
             "content": json.dumps({"env": {OVERRIDE: "1"}})}
    assert _gate(project, "Write", notes) == {}


def test_control_the_persons_own_override_still_lifts_the_question(project):
    said = _gate(project, "Write", _write(project, LOCAL, _with(disableAllHooks=True)),
                 **{OVERRIDE: "1"})
    assert said == {}


# ---------------------------------------------------------------- a shell command, afterwards


def _shell(project: Path, half: str, call: str = "call-1", **extra) -> str:
    payload = {"tool_name": "Bash", "tool_use_id": call, "permission_mode": "default",
               "session_id": "s1", "cwd": str(project),
               "tool_input": {"command": "python3 tools/configure.py"}}
    done = subprocess.run(["bash", str(SHELL_GUARD), half], input=json.dumps(payload), text=True,
                          capture_output=True, env=_env(project, **extra), timeout=60, check=False)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def _around(project: Path, act, **extra) -> dict:
    """The hook's before half, then what the command did, then its after half."""
    assert _shell(project, "pre", **extra) == ""
    act()
    out = _shell(project, "post", **extra)
    return json.loads(out) if out else {}


def test_a_switch_a_shell_command_set_is_taken_out_and_said(project):
    """RED BEFORE 0.322.6: the switch stayed and nothing was said."""
    target = project / LOCAL
    left = _with(env={OVERRIDE: "1"}, permissions={"allow": ["Bash(npm test)", "Bash(ls)"]})
    said = _around(project, lambda: target.write_text(json.dumps(left)))
    now = json.loads(target.read_text())
    assert OVERRIDE not in now["env"], "the switch is still set"
    assert now["permissions"]["allow"] == ["Bash(npm test)", "Bash(ls)"], "the rest was not kept"
    assert said["decision"] == "block" and OVERRIDE in said["systemMessage"]
    assert "taken out again" in said["systemMessage"]


def test_a_value_the_command_changed_goes_back_to_what_the_person_had(project):
    target = project / LOCAL
    target.write_text(json.dumps(_with(env={"MYCELIUM_TODAY": "2026-01-01"})))
    _around(project, lambda: target.write_text(json.dumps(_with(env={"MYCELIUM_TODAY": "2020-01-01"}))))
    assert json.loads(target.read_text())["env"]["MYCELIUM_TODAY"] == "2026-01-01"


def test_all_hooks_switched_off_by_a_shell_command_is_undone(project):
    target = project / SHARED
    said = _around(project, lambda: target.write_text(json.dumps({"disableAllHooks": True})))
    assert "disableAllHooks" not in json.loads(target.read_text())
    assert "disableAllHooks=true" in said["systemMessage"]


def test_the_override_set_by_the_command_does_not_switch_its_own_undoing_off(project):
    """Claude Code re-reads the env block while a session runs, so by the time the after half
    runs the override the command just wrote may be in the hook's own environment. What counts is
    whether it was on BEFORE the command."""
    target = project / LOCAL
    assert _shell(project, "pre") == ""
    target.write_text(json.dumps(_with(env={OVERRIDE: "1"})))
    out = _shell(project, "post", **{OVERRIDE: "1"})
    assert OVERRIDE not in json.loads(target.read_text())["env"]
    assert json.loads(out)["decision"] == "block"


def test_control_with_the_persons_override_on_beforehand_nothing_is_undone(project):
    target = project / LOCAL
    said = _around(project, lambda: target.write_text(json.dumps(_with(disableAllHooks=True))),
                   **{OVERRIDE: "1"})
    assert json.loads(target.read_text())["disableAllHooks"] is True and said == {}


def test_the_plugin_switched_off_is_said_and_left_alone(project):
    """Claude Code's own plugin commands write this key; the person may have run one."""
    target = project / LOCAL
    off = _with(enabledPlugins={"mycelium@haabe-mycelium": False})
    said = _around(project, lambda: target.write_text(json.dumps(off)))
    assert json.loads(target.read_text())["enabledPlugins"] == {"mycelium@haabe-mycelium": False}
    assert "has not changed it" in said["systemMessage"]


def test_the_home_folder_file_has_the_one_line_taken_out(project):
    """Maintainer's ruling, 2026-10-12: "Undo that line, tell me"."""
    home = project.parent / "home" / ".claude" / "settings.json"
    home.write_text(json.dumps({"model": "opus", "env": {"EDITOR": "vim"}}, indent=2))
    left = {"model": "opus", "env": {"EDITOR": "vim", OVERRIDE: "1"}, "theme": "dark"}
    said = _around(project, lambda: home.write_text(json.dumps(left)))
    assert json.loads(home.read_text()) == {"model": "opus", "env": {"EDITOR": "vim"},
                                            "theme": "dark"}
    assert "~/.claude/settings.json" in said["systemMessage"]


def test_a_file_that_is_not_json_is_said_and_not_rewritten(project):
    target = project / LOCAL
    broken = '{ "env": { "' + OVERRIDE + '": "1", } }'
    said = _around(project, lambda: target.write_text(broken))
    assert target.read_text() == broken
    assert "COULD NOT BE TAKEN OUT" in said["systemMessage"]


def test_control_an_ordinary_shell_change_to_settings_is_silent_and_kept(project):
    target = project / LOCAL
    more = _with(permissions={"allow": ["Bash(npm test)", "Bash(ls)"]})
    text = json.dumps(more)
    assert _around(project, lambda: target.write_text(text)) == {}
    assert target.read_text() == text, "an ordinary change was rewritten"


def test_control_a_switch_that_was_there_before_the_command_is_left(project):
    target = project / LOCAL
    target.write_text(json.dumps(_with(env={"MYCELIUM_TODAY": "2026-01-01"})))
    before = target.read_text()
    assert _around(project, lambda: None) == {}
    assert target.read_text() == before


def test_the_record_kept_while_a_command_runs_holds_switches_not_the_file(project):
    """PRIVACY.md says so: a settings file can hold keys, and no copy of it is made."""
    (project / LOCAL).write_text(json.dumps(_with(env={"API_TOKEN": "tok-not-a-real-one",
                                                       "MYCELIUM_TODAY": "2026-01-01"})))
    assert _shell(project, "pre") == ""
    kept = "".join(p.read_text(errors="replace")
                   for p in (project / ".claude" / "state" / "bash-guard").rglob("*") if p.is_file())
    assert "MYCELIUM_TODAY" in kept and "tok-not-a-real-one" not in kept


# ---------------------------------------------------------------- the reading itself


@pytest.mark.parametrize(("doc", "keys"), [
    ({}, []),
    ({"env": {"NODE_ENV": "x"}}, []),
    ({"env": {"mycelium_today": "2020-01-01"}}, ["env.mycelium_today"]),
    ({"env": {"CLAUDE_PROJECT_DIR": "/x"}}, ["env.CLAUDE_PROJECT_DIR"]),
    ({"disableAllHooks": False}, []),
    ({"enabledPlugins": {"mycelium@haabe-mycelium": True, "other@x": False}}, []),
    ({"enabledPlugins": {"Mycelium@fork": False}}, ["enabledPlugins.Mycelium@fork"]),
    ({"env": ["MYCELIUM_TODAY=2020-01-01"]}, ["(not valid JSON) MYCELIUM_TODAY"]),
])
def test_what_counts_as_a_switch(doc, keys):
    assert sorted(ss.switches(json.dumps(doc))) == keys


def test_text_that_is_not_json_is_read_by_its_words():
    assert list(ss.switches('{ "disableAllHooks": true, }')) == ["(not valid JSON) disableAllHooks"]
    assert ss.switches("[1, 2]") == {} and ss.switches("   ") == {}


def test_putting_back_touches_only_the_named_keys():
    before = ss.switches(json.dumps({"env": {"MYCELIUM_TODAY": "2026-01-01"}}))
    after = json.dumps({"a": 1, "disableAllHooks": True,
                        "env": {"MYCELIUM_TODAY": "2020-01-01", OVERRIDE: "1", "KEEP": "me"}})
    new = ss.newly_set(before, ss.switches(after))
    assert json.loads(ss.without(after, before, new)) == {
        "a": 1, "env": {"MYCELIUM_TODAY": "2026-01-01", "KEEP": "me"}}
    assert ss.without("[]", before, new) is None
    assert ss.without(after, before, ["(not valid JSON) X"]) is None
    assert ss.without(json.dumps({"env": "text"}), before, ["env.X"]) is None


def test_the_result_of_each_kind_of_write_is_worked_out():
    base = json.dumps(ORDINARY)
    assert ss.proposed_text({"content": "{}"}, base, "file_path", None) == "{}"
    assert ss.proposed_text({"edits": [{"oldText": "test", "newText": "ci"}]}, base, "path",
                            None).count("ci") == 1
    assert ss.proposed_text({"old_string": "test", "new_string": "ci", "replace_all": True}, base,
                            "file_path", None).count("ci") == base.count("test")
    with pytest.raises(ss.CannotTellError):
        ss.proposed_text({"new_source": "x"}, base, "notebook_path", None)

    def gone(_path: str) -> str:
        raise FileNotFoundError

    with pytest.raises(ss.CannotTellError):
        ss.proposed_text({"source": "a"}, base, "destination", gone)


def test_the_home_file_follows_the_config_folder_variable(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    assert ss.user_settings_path() == str(tmp_path / "settings.json")
