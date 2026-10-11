"""A blocking gate that cannot run refuses (v0.322.1; maintainer ruling "Block the write").

WHY. Claude Code lets a tool call through when a hook fails: it cannot start, it reaches its
timeout, it exits with a status other than 0 or 2, or it prints JSON Claude Code cannot read. So
every Mycelium gate let the write through when its process failed, whatever its own script said
about failing closed. `"onFailure": "block"` on a command hook (Claude Code 2.1.295 and later)
turns such a failure into a refusal.

THREE PARTS, and the last two are the ones that would bite a user.
  1. hooks.json carries the setting on every PreToolUse hook that can refuse, and on no hook that
     only advises. Which is which is read from ONE list, hooks/pretooluse-on-failure.txt.
  2. With the setting on, an exit status other than 0 or 2 blocks, and so does stdout that is two
     JSON objects. Any path where a gate MEANT to allow and left that way now refuses work. Three
     were found by reading the scripts (below); each ran red on 0.321.0.
  3. ONLY IN A PROJECT THAT USES MYCELIUM (second ruling, same day: "Block only in Mycelium
     projects"). The script's own "not a Mycelium project" exit needs the script to start, so
     with the setting alone a machine where the hooks cannot start refused every write in every
     project. Each blocking command now begins with one prefix, kept in the same list, that
     leaves with status 0 before bash starts when the project has neither `.claude/canvas/` nor
     `.claude/diamonds/`. A prefix that left where the script would have gone on would switch
     every gate off in that project, so the two are run over one matrix of cases (below).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
HOOKS = PLUGIN / "hooks"
SCRIPTS = PLUGIN / "scripts"
POLICY = HOOKS / "pretooluse-on-failure.txt"
POLICY_REL = "hooks/pretooluse-on-failure.txt"
CLASSES = ("block", "continue", "advisory")
#: How a hook script refuses: its own exit 2, the shared deny and ask helpers, a decision it
#: prints, or a Python helper's verdict it passes on to the denial ledger.
REFUSES = re.compile(r"^[^#\n]*\bexit 2\b|hi_deny|hi_ask|permissionDecision|mycelium_note_refusal",
                     re.MULTILINE)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_scale_locks as tsl  # noqa: E402 - the suite's canvas ladder

# ---------------------------------------------------------------- the one list


def read_policy(text: str) -> tuple[dict[str, tuple[str, str]], list[str]]:
    """script -> (class, reason), and what is wrong with the list itself."""
    policy: dict[str, tuple[str, str]] = {}
    wrong = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split(None, 2)
        if parts[0] == "prefix":
            continue  # read_prefix reads it
        kind, script = parts[0], (parts[1] if len(parts) > 1 else "")
        reason = parts[2] if len(parts) > 2 else ""
        if kind not in CLASSES or not script.endswith(".sh"):
            wrong.append(f"not `<class> <script>.sh`: {raw.strip()}")
        elif script in policy:
            wrong.append(f"{script} is listed twice")
        elif kind == "continue" and not reason:
            wrong.append(f"{script} is `continue` with no reason")
        else:
            policy[script] = (kind, reason)
    return policy, wrong


def read_prefix(text: str) -> str:
    """The one `prefix` line: the text every blocking command starts with. Empty when the list
    has none or more than one, which the manifest test then reports on every blocking entry."""
    found = [raw.split(None, 1)[1].strip() for raw in text.splitlines()
             if raw.split(None, 1)[:1] == ["prefix"] and len(raw.split(None, 1)) > 1]
    return found[0] if len(found) == 1 else ""


def composed(prefix: str, script: str) -> str:
    """What a blocking entry's command must be, to the character."""
    return f'{prefix} bash "${{CLAUDE_PLUGIN_ROOT}}/hooks/{script}"'


def pretooluse_entries(doc: dict) -> list[tuple[str, str, dict]]:
    """(matcher, script, the hook entry) for every command hook registered on PreToolUse."""
    out = []
    for group in doc["hooks"].get("PreToolUse", []):
        for hook in group["hooks"]:
            m = re.search(r"/hooks/([\w.-]+\.sh)", hook.get("command", ""))
            out.append((group.get("matcher", ""), m.group(1) if m else hook.get("command", ""), hook))
    return out


def gaps(doc: dict, policy: dict[str, tuple[str, str]], prefix: str) -> list[str]:
    """Where the manifest and the list disagree. Empty means they agree."""
    found = [] if prefix else ["the list has no single `prefix` line"]
    seen = set()
    for matcher, script, hook in pretooluse_entries(doc):
        seen.add(script)
        if script not in policy:
            found.append(f"{script} ({matcher}) is registered on PreToolUse and not in the list")
            continue
        kind = policy[script][0]
        has = hook.get("onFailure")
        if kind == "block" and has != "block":
            found.append(f"{script} ({matcher}) can refuse and does not block when it cannot run")
        if kind != "block" and has is not None:
            found.append(f"{script} ({matcher}) is {kind} and carries onFailure: {has}")
        command = hook.get("command", "")
        if kind == "block" and command != composed(prefix, script):
            found.append(f"{script} ({matcher}) is not the prefix followed by its script")
        if kind != "block" and ("exit 0" in command or (prefix and prefix in command)):
            found.append(f"{script} ({matcher}) is {kind} and leaves before its script starts")
    found += [f"{s} is in the list and not registered on PreToolUse" for s in policy if s not in seen]
    return found


def _manifest() -> dict:
    return json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))


def _policy() -> dict[str, tuple[str, str]]:
    policy, wrong = read_policy(POLICY.read_text(encoding="utf-8"))
    assert wrong == []
    return policy


PREFIX = read_prefix(POLICY.read_text(encoding="utf-8"))


def test_the_manifest_agrees_with_the_one_list():
    """RED ON 0.321.0: no entry in hooks.json carried the setting, and there was no list. RED
    BEFORE THE PREFIX: every blocking command was the bare `bash "<script>"`."""
    assert PREFIX
    assert gaps(_manifest(), _policy(), PREFIX) == []


def test_every_class_is_in_use_so_the_test_is_not_vacuous():
    kinds = [k for k, _ in _policy().values()]
    assert {k: kinds.count(k) for k in CLASSES} == {"block": 9, "continue": 1, "advisory": 5}
    blocking = [h for _, s, h in pretooluse_entries(_manifest()) if h.get("onFailure") == "block"]
    assert len(blocking) == 24
    assert len([h for h in blocking if h["command"].startswith(PREFIX + " bash ")]) == 24
    assert len({h["command"][:len(PREFIX)] for h in blocking}) == 1  # one prefix, not 24 near-copies


def _doc(*hooks: dict) -> dict:
    return {"hooks": {"PreToolUse": [{"matcher": "Write", "hooks": list(hooks)}]}}


P = '[ -d "$CLAUDE_PROJECT_DIR/.claude/canvas" ] || exit 0;'  # a stand-in prefix for the controls


def _hook(script: str, prefix: str = "", **extra) -> dict:
    bare = f'bash "${{CLAUDE_PLUGIN_ROOT}}/hooks/{script}"'
    return {"type": "command", "command": f"{prefix} {bare}" if prefix else bare, **extra}


def test_control_a_gate_without_the_setting_is_caught():
    found = gaps(_doc(_hook("gate.sh", P)), {"gate.sh": ("block", "")}, P)
    assert found == ["gate.sh (Write) can refuse and does not block when it cannot run"]
    wrong_value = gaps(_doc(_hook("gate.sh", P, onFailure="continue")), {"gate.sh": ("block", "")}, P)
    assert wrong_value == found


def test_control_an_advisory_hook_carrying_the_setting_is_caught():
    doc = _doc(_hook("key-shape-guard.sh", onFailure="block"))
    assert gaps(doc, {"key-shape-guard.sh": ("advisory", "")}, P) == [
        "key-shape-guard.sh (Write) is advisory and carries onFailure: block"]
    left_open = _doc(_hook("bash-state-guard.sh", onFailure="block"))
    assert gaps(left_open, {"bash-state-guard.sh": ("continue", "why")}, P) == [
        "bash-state-guard.sh (Write) is continue and carries onFailure: block"]


def test_control_a_hook_nobody_classified_is_caught_both_ways():
    assert gaps(_doc(_hook("new-gate.sh")), {}, P) == [
        "new-gate.sh (Write) is registered on PreToolUse and not in the list"]
    assert gaps(_doc(), {"gone.sh": ("block", "")}, P) == [
        "gone.sh is in the list and not registered on PreToolUse"]


def test_control_a_blocking_command_that_is_not_exactly_the_prefix_is_caught():
    """The setting with no prefix, a prefix one character off, and something after the script."""
    policy = {"gate.sh": ("block", "")}
    wrong = "gate.sh (Write) is not the prefix followed by its script"
    assert gaps(_doc(_hook("gate.sh", onFailure="block")), policy, P) == [wrong]
    assert gaps(_doc(_hook("gate.sh", P.replace("canvas", "Canvas"), onFailure="block")), policy, P) == [wrong]
    trailing = _hook("gate.sh", P, onFailure="block")
    trailing["command"] += " || true"
    assert gaps(_doc(trailing), policy, P) == [wrong]
    assert gaps(_doc(_hook("gate.sh", P, onFailure="block")), policy, P) == []


def test_control_a_hook_that_is_not_blocking_and_leaves_early_is_caught():
    doc = _doc(_hook("key-shape-guard.sh", P), _hook("bash-state-guard.sh", P))
    policy = {"key-shape-guard.sh": ("advisory", ""), "bash-state-guard.sh": ("continue", "why")}
    assert gaps(doc, policy, P) == [
        "key-shape-guard.sh (Write) is advisory and leaves before its script starts",
        "bash-state-guard.sh (Write) is continue and leaves before its script starts"]


def test_control_a_list_with_no_prefix_or_two_is_caught():
    assert read_prefix("block gate.sh\n") == ""
    assert read_prefix("prefix a;\nprefix b;\n") == ""
    assert read_prefix("# prefix in a comment\nprefix   a b;  \n") == "a b;"
    assert gaps(_doc(), {}, "") == ["the list has no single `prefix` line"]


def test_control_a_malformed_list_is_caught():
    _, wrong = read_policy("blocks gate.sh\nblock gate\ncontinue a.sh\nblock b.sh\nblock b.sh\n")
    assert wrong == ["not `<class> <script>.sh`: blocks gate.sh", "not `<class> <script>.sh`: block gate",
                     "a.sh is `continue` with no reason", "b.sh is listed twice"]


def test_the_list_agrees_with_what_each_script_does():
    """A hook listed as advisory has no way to refuse in its own text or its helper's; one listed
    as refusing has one. Catches a new gate filed as advisory to keep it off the setting."""
    for script, (kind, _) in _policy().items():
        text = (HOOKS / script).read_text(encoding="utf-8")
        helper = SCRIPTS / (script[:-3].replace("-", "_") + ".py")
        helper_text = helper.read_text(encoding="utf-8") if helper.is_file() else ""
        refuses = bool(REFUSES.search(text)) or "permissionDecision" in helper_text
        assert refuses == (kind != "advisory"), f"{script} is listed as {kind}"


def test_the_one_left_open_says_so_in_its_own_header():
    for script, (kind, reason) in _policy().items():
        if kind == "continue":
            assert reason
            assert "FAILS OPEN" in (HOOKS / script).read_text(encoding="utf-8"), script


def test_the_docs_name_the_list_instead_of_keeping_their_own():
    readme = (HOOKS / "README.md").read_text(encoding="utf-8")
    card = (ROOT / "docs" / "ai-system-card.md").read_text(encoding="utf-8")
    assert POLICY_REL in readme and POLICY_REL in card
    for doc in (readme, card):
        assert '"onFailure": "block"' in doc and "2.1.295" in doc
        # where it bites, and the limit that is left (no POSIX shell to read the command)
        assert ".claude/canvas/" in doc and ".claude/diamonds/" in doc
        assert "Git Bash" in doc and "PowerShell" in doc


@pytest.mark.parametrize("name", ["hooks.codex.json", "hooks.codex-plugin.json", "hooks.cursor.json"])
def test_the_other_runtimes_manifests_do_not_carry_claude_codes_key(name):
    """Codex CLI documents no such key (developers.openai.com/codex/hooks) and Cursor's is
    `failClosed` (cursor.com/docs/hooks). A key a runtime does not know is not a gate there."""
    assert "onFailure" not in (HOOKS / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------- an allow must leave as one
#
# With the setting on, "exit status other than 0 or 2" and "stdout that is not one JSON object"
# are failures, and a failure blocks. So a gate that means to allow has to leave with status 0
# and at most one JSON object.

BIG = "x" * 400_000  # more than a pipe holds: the writer is still writing when the reader leaves


def _run(script: str, project: Path, payload: dict, **env_extra) -> subprocess.CompletedProcess:
    tmp = project / "tmp"
    tmp.mkdir(exist_ok=True)
    env = {"CLAUDE_PROJECT_DIR": str(project), "CLAUDE_PLUGIN_ROOT": str(PLUGIN),
           "TMPDIR": str(tmp), "PATH": str(Path(sys.executable).parent) + ":/usr/bin:/bin",
           **env_extra}
    return subprocess.run(["bash", str(HOOKS / script)], input=json.dumps(payload),
                          capture_output=True, text=True, env=env, check=False)


def _mycelium_project(tmp_path: Path) -> Path:
    for sub in ("canvas", "diamonds", "state"):
        (tmp_path / ".claude" / sub).mkdir(parents=True, exist_ok=True)
    return tmp_path


def _write(content: str, path: str = "notes/plan.md") -> dict:
    return {"tool_name": "Write", "tool_use_id": "toolu_1", "session_id": "s1",
            "permission_mode": "default", "tool_input": {"file_path": path, "content": content}}


def _one_json_object_or_text(stdout: str) -> bool:
    """What Claude Code reads without calling it a failure: nothing, plain text, or ONE object.
    Two lines that each parse as an object are a parse failure (hooks reference, Exit code 0)."""
    lines = [ln for ln in stdout.splitlines() if ln.strip()]
    objects = 0
    for ln in lines:
        try:
            objects += isinstance(json.loads(ln), dict)
        except ValueError:
            continue
    return objects <= 1


def test_framework_guard_switched_off_allows_a_large_write_with_status_0(tmp_path):
    """RED ON 0.321.0 (exit 1, "printf: write error: Broken pipe"; 141 where SIGPIPE is not
    ignored). `"active": false` is the documented way to switch the guard off, and the helper
    answers it before reading the tool call. The wrapper fed the call through a pipe under
    `set -eo pipefail`, so on a write larger than the pipe the writer failed and the hook left
    with ITS status: a hook error that let the write through, and with the setting on, a refusal
    of every large write in a project that had switched the guard off."""
    project = _mycelium_project(tmp_path)
    (project / ".claude" / "state" / "upstream.json").write_text('{"active": false}')
    done = _run("framework-guard.sh", project, _write(BIG))
    assert (done.returncode, done.stdout) == (0, ""), done.stderr[:300]


def test_control_framework_guard_switched_off_allows_a_small_write(tmp_path):
    project = _mycelium_project(tmp_path)
    (project / ".claude" / "state" / "upstream.json").write_text('{"active": false}')
    done = _run("framework-guard.sh", project, _write("short"))
    assert (done.returncode, done.stdout) == (0, "")


def test_scope_gate_says_why_it_refuses_a_large_write_over_broken_state(tmp_path):
    """RED ON 0.321.0 (exit 1, no stdout). The same pipe: the helper printed its deny for a
    corrupt active-execution.json, the wrapper left before passing it on, and the write went
    through. With the setting on it would be refused with no reason given."""
    project = _mycelium_project(tmp_path)
    (project / ".claude" / "state" / "active-execution.json").write_text("{not json")
    done = _run("scope-gate.sh", project, _write(BIG))
    assert done.returncode == 0, done.stderr[:300]
    said = json.loads(done.stdout)["hookSpecificOutput"]
    assert said["permissionDecision"] == "deny" and "corrupt" in said["permissionDecisionReason"]


def test_control_scope_gate_refuses_a_small_write_over_broken_state(tmp_path):
    project = _mycelium_project(tmp_path)
    (project / ".claude" / "state" / "active-execution.json").write_text("{not json")
    done = _run("scope-gate.sh", project, _write("short"))
    assert done.returncode == 0
    assert json.loads(done.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


RELEASED = [{"decision": d, "on": "2026-09-20"}
            for d in ("set_target", "start_experiment", "commit_to_build")] + [
                {"decision": "release", "on": "2026-09-22"}]
EXPIRED_ACK = 'recorded_at: 2026-08-01\ncovers: [prototypes/]\nwhy: "the founder\'s own words"\n'


def _released(tmp_path: Path, ack: str | None) -> Path:
    l3 = {"id": "l3-a", "scale": "L3", "object_ref": "sol-001", "evidence_type": "anecdotal",
          "theory_gates_status": dict(tsl.EXPOSE_PASSED), "decisions": list(RELEASED),
          "exposures": [dict(tsl.RECORD)]}
    project = Path(tsl._project(tmp_path, purpose=tsl.PURPOSE, opps=tsl._full_opps(), diamonds=[l3]))
    if ack is not None:
        (project / ".claude" / "state" / "delivery-skip-ack").write_text(ack)
    return project


def _deploy() -> dict:
    return {**tsl._bash("fly deploy"), "permission_mode": "default", "tool_use_id": "toolu_2"}


def test_an_allowed_release_with_an_expired_ack_prints_one_json_object(tmp_path):
    """RED ON 0.321.0 (two objects). The expired ack's warning was printed as one JSON object and
    the gate's own advice as a second. Claude Code reads two objects as output it cannot parse:
    until now a hook error that let the release through without the advice, and with the setting
    on, a refusal of a release the gate allowed."""
    project = _released(tmp_path, EXPIRED_ACK)
    done = _run("exposure-gate.sh", project, _deploy(), MYCELIUM_TODAY="2026-09-25")
    assert done.returncode == 0, done.stderr[:300]
    said = json.loads(done.stdout)
    assert "expired on 2026-08-31" in said["systemMessage"]           # the ack's warning
    assert "/mycelium:harms-check" in said["hookSpecificOutput"]["additionalContext"]  # the gate's
    assert "permissionDecision" not in said["hookSpecificOutput"]


def test_control_an_allowed_release_with_no_ack_is_unchanged(tmp_path):
    project = _released(tmp_path, None)
    done = _run("exposure-gate.sh", project, _deploy(), MYCELIUM_TODAY="2026-09-25")
    said = json.loads(done.stdout)
    assert done.returncode == 0 and set(said) == {"hookSpecificOutput"}
    assert "/mycelium:harms-check" in said["hookSpecificOutput"]["additionalContext"]


def test_control_a_refused_release_still_exits_2_and_keeps_the_acks_warning(tmp_path):
    project = _released(tmp_path, EXPIRED_ACK)
    active = project / ".claude" / "diamonds" / "active.yml"
    doc = yaml.safe_load(active.read_text())
    for d in doc["active_diamonds"]:
        if d["id"] == "l3-a":
            d["exposures"][0]["gates"] = {}
    active.write_text(yaml.safe_dump(doc))
    done = _run("exposure-gate.sh", project, _deploy(), MYCELIUM_TODAY="2026-09-25")
    assert done.returncode == 2
    assert "Mycelium exposure gate" in done.stderr
    assert "expired on 2026-08-31" in json.loads(done.stdout)["systemMessage"]


def test_a_lifting_ack_still_lifts_the_release_and_says_what_it_said(tmp_path):
    project = _released(tmp_path, "the user said skip it, 2026-08-01\n")  # an old bare ack
    done = _run("exposure-gate.sh", project, _deploy(), MYCELIUM_TODAY="2026-09-25")
    assert done.returncode == 0
    assert "honoured until" in json.loads(done.stdout)["systemMessage"]


def _blocking_gates() -> list[str]:
    return sorted(s for s, (kind, _) in read_policy(POLICY.read_text(encoding="utf-8"))[0].items()
                  if kind == "block")


CALLS = {
    "a small write": _write("short"),
    "a large write": _write(BIG),
    "a new source file": _write("print('hi')\n", "app/main.py"),
    "a shell command": {**tsl._bash("ls -la"), "permission_mode": "default"},
    "a release": _deploy(),
    "not a tool call": {"tool_name": "Write", "tool_input": "a string, not an object"},
}


@pytest.mark.parametrize("script", _blocking_gates())
@pytest.mark.parametrize("call", sorted(CALLS))
def test_every_blocking_gate_leaves_with_0_or_2_and_one_object(tmp_path, script, call):
    """In an ordinary project, and in one whose state files are present, no gate that carries the
    setting leaves with a status Claude Code would read as "could not run"."""
    project = _released(tmp_path, EXPIRED_ACK)
    for state in (None, "upstream.json", "active-execution.json"):
        if state == "upstream.json":
            (project / ".claude" / "state" / state).write_text('{"active": false}')
        elif state:
            (project / ".claude" / "state" / state).write_text('{"diamond_id": "l3-a"}')
        done = _run(script, project, CALLS[call], MYCELIUM_TODAY="2026-09-25")
        assert done.returncode in (0, 2), (state, done.returncode, done.stderr[:300])
        assert _one_json_object_or_text(done.stdout), (state, done.stdout[:300])


# ---------------------------------------------------------------- python3 that cannot run


def _registered_for(tool: str) -> list[str]:
    """The `block` gates hooks.json runs before this tool, in order."""
    policy = _policy()
    out = []
    for group in _manifest()["hooks"]["PreToolUse"]:
        if re.fullmatch(group.get("matcher", ""), tool):
            out += [s for _, s, _ in pretooluse_entries({"hooks": {"PreToolUse": [group]}})
                    if policy[s][0] == "block"]
    return out


@pytest.mark.parametrize(("tool", "call"), [("Write", "a new source file"), ("Bash", "a shell command")])
def test_with_a_python3_that_cannot_run_the_call_is_refused(tmp_path, tool, call):
    """The hooks need python3 (hooks/README.md, Dependencies). When it cannot run, the call is
    refused: at least one gate registered for the tool leaves with a status other than 0. This
    test holds the outcome, not which gate produces it. Which gates refuse by their own decision
    in that state, and how, is tests/python/test_refusal_without_python.py."""
    project = _mycelium_project(tmp_path)
    fake = tmp_path / "fakebin"
    fake.mkdir()
    (fake / "python3").write_text("#!/bin/sh\nexit 127\n")
    (fake / "python3").chmod(0o755)
    statuses = {}
    for script in _registered_for(tool):
        done = _run(script, project, CALLS[call], PATH=f"{fake}:/usr/bin:/bin")
        statuses[script] = done.returncode
    assert len(statuses) >= 7, statuses
    assert any(code != 0 for code in statuses.values()), statuses


# ---------------------------------------------------------------- the prefix and the prelude
#
# The prefix in front of every blocking command decides, in the shell Claude Code hands the
# command to, whether to start the hook at all. scripts/_hook_prelude.sh decides the same thing
# on line 2 of every hook. If the prefix said "not a Mycelium project" where the prelude says "it
# is", that project would lose every gate and nothing would say so. So: the prefix may go on
# where the prelude leaves (the script then leaves by itself), never the other way round.

PRELUDE = SCRIPTS / "_hook_prelude.sh"
SHELLS = [s for s in ("sh", "bash", "dash") if shutil.which(s)]
#: name: (what `.claude/` holds, the folder's name, CLAUDE_PROJECT_DIR, the working directory,
#:        extra environment, does the prefix go on, does the prelude go on)
#: CLAUDE_PROJECT_DIR: "project", "project/", "elsewhere", "." , "" (set and empty) or None (unset).
#: Working directory: "project", "inside" (two folders down in it) or "elsewhere".
MATRIX = {
    "both folders": (("canvas", "diamonds"), "p", "project", "elsewhere", {}, True, True),
    "only .claude/canvas": (("canvas",), "p", "project", "elsewhere", {}, True, True),
    "only .claude/diamonds": (("diamonds",), "p", "project", "elsewhere", {}, True, True),
    "neither folder": ((), "p", "project", "elsewhere", {}, False, False),
    "only .claude/state": (("state",), "p", "project", "elsewhere", {}, False, False),
    "canvas is a file, not a folder": (("canvas-file",), "p", "project", "elsewhere", {}, False, False),
    "a path with a space, a project": (("canvas",), "my project", "project", "elsewhere", {}, True, True),
    "a path with a space, not a project": ((), "my project", "project", "elsewhere", {}, False, False),
    "a path with a quote, a dollar and a semicolon, a project":
        (("diamonds",), 'od"d $HOME;x', "project", "elsewhere", {}, True, True),
    "a path with a quote, a dollar and a semicolon, not a project":
        ((), 'od"d $HOME;x', "project", "elsewhere", {}, False, False),
    "a trailing slash on CLAUDE_PROJECT_DIR": (("canvas",), "p", "project/", "elsewhere", {}, True, True),
    "CLAUDE_PROJECT_DIR is `.`, in the project": (("canvas",), "p", ".", "project", {}, True, True),
    "CLAUDE_PROJECT_DIR is `.`, not in a project": ((), "p", ".", "project", {}, False, False),
    "CLAUDE_PROJECT_DIR elsewhere, working directory inside a project":
        (("canvas",), "p", "elsewhere", "inside", {}, False, False),
    "CLAUDE_PROJECT_DIR unset, working directory is the project":
        (("canvas",), "p", None, "project", {}, True, True),
    "CLAUDE_PROJECT_DIR unset, working directory two folders inside a project":
        (("diamonds",), "p", None, "inside", {}, True, True),
    "CLAUDE_PROJECT_DIR unset, no project above the working directory":
        ((), "p", None, "inside", {}, True, False),
    "CLAUDE_PROJECT_DIR empty, working directory inside a project":
        (("canvas",), "p", "", "inside", {}, True, True),
    "CLAUDE_PROJECT_DIR empty, no project above the working directory":
        ((), "p", "", "inside", {}, True, False),
    "MYCELIUM_PRELUDE_ANY_PROJECT=1, neither folder":
        ((), "p", "project", "elsewhere", {"MYCELIUM_PRELUDE_ANY_PROJECT": "1"}, True, True),
    "MYCELIUM_PRELUDE_ANY_PROJECT=0, neither folder":
        ((), "p", "project", "elsewhere", {"MYCELIUM_PRELUDE_ANY_PROJECT": "0"}, False, False),
}


def _matrix_case(tmp_path: Path, name: str) -> tuple[Path, dict]:
    holds, folder, project_dir, where, extra, _, _ = MATRIX[name]
    project = tmp_path / folder
    (project / "src" / "deep").mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    for item in holds:
        if item.endswith("-file"):
            (project / ".claude").mkdir(exist_ok=True)
            (project / ".claude" / item[:-5]).write_text("not a folder\n")
        else:
            (project / ".claude" / item).mkdir(parents=True)
    env = {"PATH": "/usr/bin:/bin", "TMPDIR": str(tmp_path), "HOME": str(tmp_path), **extra}
    if project_dir is not None:
        env["CLAUDE_PROJECT_DIR"] = {"project": str(project), "project/": str(project) + "/",
                                     "elsewhere": str(elsewhere)}.get(project_dir, project_dir)
    cwd = {"project": project, "inside": project / "src" / "deep", "elsewhere": elsewhere}[where]
    return cwd, env


def _went_on(argv: list[str], cwd: Path, env: dict) -> bool:
    done = subprocess.run(argv, input="", cwd=cwd, env=env, capture_output=True, text=True,
                          check=False, timeout=30)
    assert (done.returncode, done.stderr) == (0, ""), done
    assert done.stdout in ("", "WENT-ON\n"), done.stdout
    return done.stdout == "WENT-ON\n"


@pytest.mark.parametrize("shell", SHELLS)
@pytest.mark.parametrize("case", sorted(MATRIX))
def test_the_prefix_never_leaves_where_the_prelude_goes_on(tmp_path, shell, case):
    """The prefix through each POSIX shell on this machine, the prelude through bash as every
    hook sources it, same folder, same environment. RED BEFORE THE PREFIX (there was none)."""
    cwd, env = _matrix_case(tmp_path, case)
    prefix_on = _went_on([shell, "-c", PREFIX + " echo WENT-ON"], cwd, env)
    prelude_on = _went_on(["bash", "-c", '. "$1"; echo WENT-ON', "prelude", str(PRELUDE)], cwd, env)
    assert not (prelude_on and not prefix_on), "the prefix would switch the gates off here"
    assert (prefix_on, prelude_on) == MATRIX[case][5:]
    if env.get("CLAUDE_PROJECT_DIR"):
        assert prefix_on == prelude_on  # wherever the variable is set, it is the same rule


def test_the_matrix_says_where_the_prefix_is_wider_and_only_there():
    """Wider in exactly one situation: CLAUDE_PROJECT_DIR not set and no project above the
    working directory. The prefix does not repeat the prelude's walk up; it starts the script,
    which walks and leaves. Claude Code always sets the variable."""
    wider = sorted(n for n, row in MATRIX.items() if row[5] and not row[6])
    assert wider == ["CLAUDE_PROJECT_DIR empty, no project above the working directory",
                     "CLAUDE_PROJECT_DIR unset, no project above the working directory"]
    assert not [n for n, row in MATRIX.items() if row[6] and not row[5]]
    assert "sh" in SHELLS and "bash" in SHELLS


def test_the_prefix_is_plain_posix_sh():
    """Claude Code hands a command to `sh -c` on macOS and Linux and to Git Bash on Windows
    (hooks reference, "Exec form and shell form"). No bash-only syntax, and nothing Claude Code
    could mistake for a `${CLAUDE_PROJECT_DIR}` path placeholder to substitute as text."""
    assert "[[" not in PREFIX and "==" not in PREFIX and "function" not in PREFIX
    assert "${CLAUDE_PROJECT_DIR}" not in PREFIX and "${CLAUDE_PLUGIN_ROOT}" not in PREFIX
    assert PREFIX.endswith("|| exit 0;") and "hooks/" not in PREFIX


def test_the_prefix_tests_every_folder_the_prelude_tests():
    """A marker folder added to the prelude and not to the prefix would make the prefix narrower
    for exactly the projects the new marker brings in. Read from the prelude's own function."""
    body = re.search(r"^_mycelium_is_project\(\) \{(.*)\}$", PRELUDE.read_text(encoding="utf-8"),
                     re.MULTILINE).group(1)
    markers = re.findall(r'\[ -d "\$1/\.claude/([\w-]+)" \]', body)
    assert markers == ["canvas", "diamonds"]
    assert body.count("[") == len(markers)  # nothing in the function this test does not read
    for marker in markers:
        assert f'[ -d "$d/.claude/{marker}" ]' in PREFIX
    assert "MYCELIUM_PRELUDE_ANY_PROJECT" in PREFIX


def _blocking_commands() -> list[str]:
    return sorted({h["command"] for _, _, h in pretooluse_entries(_manifest())
                   if h.get("onFailure") == "block"})


def _shell_run(argv: list[str], cwd: Path, payload: dict, **env) -> subprocess.CompletedProcess:
    return subprocess.run(argv, input=json.dumps(payload), cwd=cwd, env=env, capture_output=True,
                          text=True, check=False, timeout=60)


NOT_FOUND = 127  # what a shell returns for a command or a script file that is not there


@pytest.mark.parametrize("shell", ["sh", "bash"])
def test_with_the_hook_script_missing_only_a_mycelium_project_is_refused(tmp_path, shell):
    """A broken install: CLAUDE_PLUGIN_ROOT names a folder with no hooks in it. In a Mycelium
    project the registered command fails (a status that is neither 0 nor 2, which the setting
    turns into a refusal). In any other project it leaves with 0 and says nothing. RED BEFORE
    THE PREFIX: 127 in both."""
    broken = tmp_path / "plugin with no hooks"
    plain = tmp_path / "plain"
    project = _mycelium_project(tmp_path / "project")
    broken.mkdir()
    plain.mkdir()
    commands = _blocking_commands()
    assert len(commands) == 9
    for command in commands:
        for where, refused in ((plain, False), (project, True)):
            done = _shell_run([shell, "-c", command], where, _write("short"), PATH="/usr/bin:/bin",
                              CLAUDE_PROJECT_DIR=str(where), CLAUDE_PLUGIN_ROOT=str(broken),
                              TMPDIR=str(tmp_path))
            if refused:
                assert done.returncode == NOT_FOUND and "No such file" in done.stderr, command
            else:
                assert (done.returncode, done.stdout, done.stderr) == (0, "", ""), command


def test_with_no_bash_on_the_path_only_a_mycelium_project_is_refused(tmp_path):
    """Outside a Mycelium project bash is never started, so its absence costs nothing there.
    RED BEFORE THE PREFIX: 127 in both."""
    empty = tmp_path / "bin"
    plain = tmp_path / "plain"
    project = _mycelium_project(tmp_path / "project")
    empty.mkdir()
    plain.mkdir()
    sh = shutil.which("sh")
    commands = _blocking_commands()
    assert len(commands) == 9  # an empty list would pass every assertion it never made
    for command in commands:
        for where, refused in ((plain, False), (project, True)):
            done = _shell_run([sh, "-c", command], where, _write("short"), PATH=str(empty),
                              CLAUDE_PROJECT_DIR=str(where), CLAUDE_PLUGIN_ROOT=str(PLUGIN))
            if refused:
                assert done.returncode == NOT_FOUND and "bash" in done.stderr, command
            else:
                assert (done.returncode, done.stdout, done.stderr) == (0, "", ""), command


@pytest.mark.parametrize("script", ["gate.sh", "discovery-gate.sh", "exposure-gate.sh"])
@pytest.mark.parametrize("call", ["a small write", "a new source file", "a release"])
def test_control_in_a_mycelium_project_the_prefix_changes_nothing(tmp_path, script, call):
    """The registered command through `sh -c`, and the script run directly as before the prefix,
    each in its own copy of one project: same status, same stdout, same stderr, to the byte."""
    command = composed(PREFIX, script)
    assert command in _blocking_commands()
    seen = []
    for name, argv in (("direct", ["bash", str(HOOKS / script)]), ("composed", ["sh", "-c", command])):
        project = _released(tmp_path / name, EXPIRED_ACK)
        (project / "tmp").mkdir()
        done = _shell_run(argv, project, CALLS[call], CLAUDE_PROJECT_DIR=str(project),
                          CLAUDE_PLUGIN_ROOT=str(PLUGIN), TMPDIR=str(project / "tmp"),
                          MYCELIUM_TODAY="2026-09-25",
                          PATH=str(Path(sys.executable).parent) + ":/usr/bin:/bin")
        seen.append((done.returncode, done.stdout.replace(str(project), "<project>"),
                     done.stderr.replace(str(project), "<project>")))
    assert seen[0] == seen[1]
    assert seen[0][0] in (0, 2)
