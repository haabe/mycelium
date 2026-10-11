"""A blocking gate that cannot run refuses (v0.321.1; maintainer ruling "Block the write").

WHY. Claude Code lets a tool call through when a hook fails: it cannot start, it reaches its
timeout, it exits with a status other than 0 or 2, or it prints JSON Claude Code cannot read. So
every Mycelium gate let the write through when its process failed, whatever its own script said
about failing closed. `"onFailure": "block"` on a command hook (Claude Code 2.1.295 and later)
turns such a failure into a refusal.

TWO HALVES, and the second is the one that would bite a user.
  1. hooks.json carries the setting on every PreToolUse hook that can refuse, and on no hook that
     only advises. Which is which is read from ONE list, hooks/pretooluse-on-failure.txt.
  2. With the setting on, an exit status other than 0 or 2 blocks, and so does stdout that is two
     JSON objects. Any path where a gate MEANT to allow and left that way now refuses work. Three
     were found by reading the scripts (below); each ran red on 0.321.0.
"""

from __future__ import annotations

import json
import re
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


def pretooluse_entries(doc: dict) -> list[tuple[str, str, dict]]:
    """(matcher, script, the hook entry) for every command hook registered on PreToolUse."""
    out = []
    for group in doc["hooks"].get("PreToolUse", []):
        for hook in group["hooks"]:
            m = re.search(r"/hooks/([\w.-]+\.sh)", hook.get("command", ""))
            out.append((group.get("matcher", ""), m.group(1) if m else hook.get("command", ""), hook))
    return out


def gaps(doc: dict, policy: dict[str, tuple[str, str]]) -> list[str]:
    """Where the manifest and the list disagree. Empty means they agree."""
    found = []
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
    found += [f"{s} is in the list and not registered on PreToolUse" for s in policy if s not in seen]
    return found


def _manifest() -> dict:
    return json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))


def _policy() -> dict[str, tuple[str, str]]:
    policy, wrong = read_policy(POLICY.read_text(encoding="utf-8"))
    assert wrong == []
    return policy


def test_the_manifest_agrees_with_the_one_list():
    """RED ON 0.321.0: no entry in hooks.json carried the setting, and there was no list."""
    assert gaps(_manifest(), _policy()) == []


def test_every_class_is_in_use_so_the_test_is_not_vacuous():
    kinds = [k for k, _ in _policy().values()]
    assert {k: kinds.count(k) for k in CLASSES} == {"block": 9, "continue": 1, "advisory": 5}
    blocking = [h for _, s, h in pretooluse_entries(_manifest()) if h.get("onFailure") == "block"]
    assert len(blocking) == 24


def _doc(*hooks: dict) -> dict:
    return {"hooks": {"PreToolUse": [{"matcher": "Write", "hooks": list(hooks)}]}}


def _hook(script: str, **extra) -> dict:
    return {"type": "command", "command": f'bash "${{CLAUDE_PLUGIN_ROOT}}/hooks/{script}"', **extra}


def test_control_a_gate_without_the_setting_is_caught():
    found = gaps(_doc(_hook("gate.sh")), {"gate.sh": ("block", "")})
    assert found == ["gate.sh (Write) can refuse and does not block when it cannot run"]
    wrong_value = gaps(_doc(_hook("gate.sh", onFailure="continue")), {"gate.sh": ("block", "")})
    assert wrong_value == found


def test_control_an_advisory_hook_carrying_the_setting_is_caught():
    doc = _doc(_hook("key-shape-guard.sh", onFailure="block"))
    assert gaps(doc, {"key-shape-guard.sh": ("advisory", "")}) == [
        "key-shape-guard.sh (Write) is advisory and carries onFailure: block"]
    left_open = _doc(_hook("bash-state-guard.sh", onFailure="block"))
    assert gaps(left_open, {"bash-state-guard.sh": ("continue", "why")}) == [
        "bash-state-guard.sh (Write) is continue and carries onFailure: block"]


def test_control_a_hook_nobody_classified_is_caught_both_ways():
    assert gaps(_doc(_hook("new-gate.sh")), {}) == [
        "new-gate.sh (Write) is registered on PreToolUse and not in the list"]
    assert gaps(_doc(), {"gone.sh": ("block", "")}) == [
        "gone.sh is in the list and not registered on PreToolUse"]


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
    """The hooks need python3 (hooks/README.md, Dependencies). When it cannot run, the gates that
    print their refusal THROUGH it (`hi_deny`) print nothing and exit 0, which is an allow. The
    call is still refused, because at least one gate registered for the tool leaves with python's
    own status, and with the setting on that blocks. This test holds the outcome, not which gate
    produces it: if it fails, a gate was changed to exit 0 without python and `hi_deny` needs a
    way to refuse that does not go through python3."""
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
