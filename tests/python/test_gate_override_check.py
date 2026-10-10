"""A gate refusal that another extension overrules is recorded and said (v0.316.0).

Claude Code 2.1.287 shipped Mods, and a mod's `tool.check` "can also approve a call that a
`PreToolUse` hook outside managed settings blocked". Every Mycelium gate is such a hook, so a
refusal could be overruled while every fire log still said "blocked". The gates now write each
refusal's tool_use_id to a denial ledger, and hooks/gate-override-check.sh (PostToolUse) flags a
call that ran with an id a gate refused.

These tests run the hooks as the runtime does (bash, stdin JSON). They cover both halves and the
structural rule that keeps a future gate from refusing without recording it.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
HOOKS = PLUGIN / "hooks"
LIB = PLUGIN / "scripts" / "_hook_fire_log.sh"
LEDGER = Path(".claude/state/denied-calls.jsonl")
OVERRIDES = Path(".claude/state/gate-override-fires.jsonl")


def _env(project: Path) -> dict:
    env = dict(os.environ)
    env.update(CLAUDE_PROJECT_DIR=str(project), CLAUDE_PLUGIN_ROOT=str(PLUGIN))
    env.pop("MYCELIUM_SESSION_ID", None)
    return env


def _run(hook: str, payload: dict, project: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(HOOKS / hook)], input=json.dumps(payload), text=True,
                          capture_output=True, env=_env(project), timeout=30, check=False)


def _write_call(project: Path, tool_use_id: str, event: str = "PreToolUse",
                content: str = "print(1)\n") -> dict:
    return {"session_id": "s1", "tool_use_id": tool_use_id, "tool_name": "Write",
            "hook_event_name": event, "cwd": str(project),
            "tool_input": {"file_path": str(project / "src" / "app.py"), "content": content}}


def _fresh(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / ".claude" / "canvas").mkdir(parents=True)  # setup ran (v0.318.0 prelude)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    return tmp_path


def _rows(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []


# ---------------------------------------------------------------- the gates record a refusal

def test_a_discovery_gate_refusal_lands_in_the_ledger_with_its_tool_use_id(tmp_path):
    project = _fresh(tmp_path)
    res = _run("discovery-gate.sh", _write_call(project, "toolu_refused01"), project)
    assert res.returncode == 2, res.stderr
    rows = _rows(project / LEDGER)
    assert [(r["tool_use_id"], r["hook"]) for r in rows] == [("toolu_refused01", "discovery-gate.sh")]
    assert set(rows[0]) <= {"ts", "tool_use_id", "hook", "session_id"}, "no tool input in a row"


def test_an_allowed_call_leaves_no_ledger_row(tmp_path):
    project = _fresh(tmp_path)
    (project / ".claude" / "state").mkdir(parents=True)
    (project / ".claude" / "state" / "discovery-skip-ack").write_text("2026-10-07 user: skip\n")
    res = _run("discovery-gate.sh", _write_call(project, "toolu_allowed01"), project)
    assert res.returncode == 0, res.stderr
    assert not (project / LEDGER).exists()


def test_hi_deny_records_the_refusal(tmp_path):
    # A tool input that is not the documented shape is refused through hi_deny.
    project = _fresh(tmp_path)
    payload = _write_call(project, "toolu_badshape1")
    payload["tool_input"] = "not an object"
    res = _run("gate.sh", payload, project)
    assert '"deny"' in res.stdout
    assert [r["tool_use_id"] for r in _rows(project / LEDGER)] == ["toolu_badshape1"]


def _lib(project: Path, script: str, stdin: str = "") -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", f'. "{LIB}"; INPUT="$(cat)"; {script}'], input=stdin,
                          text=True, capture_output=True, env=_env(project), timeout=30,
                          check=False)


def test_note_refusal_records_a_deny_and_an_exit_2_but_never_an_ask(tmp_path):
    call = json.dumps(_write_call(tmp_path, "toolu_x"))
    deny = '{"hookSpecificOutput": {"permissionDecision": "deny"}}'
    ask = '{"hookSpecificOutput": {"permissionDecision": "ask"}}'
    for out, rc, ident in ((deny, 0, "toolu_deny01"), ("", 2, "toolu_exit201"),
                           (ask, 0, "toolu_ask0001"), ("", 0, "toolu_allow01")):
        _lib(tmp_path, f"mycelium_note_refusal '{out}' {rc}", call.replace("toolu_x", ident))
    assert [r["tool_use_id"] for r in _rows(tmp_path / LEDGER)] == ["toolu_deny01", "toolu_exit201"]


def test_a_payload_without_a_tool_use_id_records_nothing(tmp_path):
    _lib(tmp_path, "mycelium_record_denial", json.dumps({"tool_name": "Write"}))
    _lib(tmp_path, "mycelium_record_denial", "not json")
    assert not (tmp_path / LEDGER).exists()


def test_a_pass_through_gate_keeps_its_verdict_byte_for_byte(tmp_path):
    # guard-state-gate prints the helper's ask; capturing it for the ledger must not change it.
    project = _fresh(tmp_path)
    payload = _write_call(project, "toolu_guard001")
    payload["tool_input"]["file_path"] = str(project / ".claude" / "state" / "discovery-skip-ack")
    res = _run("guard-state-gate.sh", payload, project)
    assert res.returncode == 0
    verdict = json.loads(res.stdout)
    assert verdict["hookSpecificOutput"]["permissionDecision"] == "ask"
    assert res.stdout.endswith("}\n")
    assert not (project / LEDGER).exists(), "an ask is not a refusal"


# ---------------------------------------------------------------- the override check

def _ledger(project: Path, *ids: str) -> None:
    path = project / LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    (project / ".claude" / "canvas").mkdir(parents=True, exist_ok=True)  # refusals happen in a Mycelium project (v0.318.0 prelude)
    path.write_text("".join(json.dumps({"ts": "2026-10-07T10:00:00Z", "tool_use_id": i,
                                        "hook": "discovery-gate.sh"}) + "\n" for i in ids))


def test_a_refused_call_that_ran_is_flagged_to_the_person_and_the_agent(tmp_path):
    _ledger(tmp_path, "toolu_ran00001")
    res = _run("gate-override-check.sh", _write_call(tmp_path, "toolu_ran00001", "PostToolUse"),
               tmp_path)
    assert res.returncode == 0
    out = json.loads(res.stdout)
    assert "discovery-gate.sh refused this Write call, and it ran anyway" in out["systemMessage"]
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert out["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "Do not report the refusal as having held" in ctx
    fires = _rows(tmp_path / OVERRIDES)
    assert [(f["outcome"], f["detail"]) for f in fires] == [("overridden", "discovery-gate.sh")]


def test_a_call_no_gate_refused_is_silent(tmp_path):
    _ledger(tmp_path, "toolu_refused9")
    res = _run("gate-override-check.sh", _write_call(tmp_path, "toolu_other0001", "PostToolUse"),
               tmp_path)
    assert (res.returncode, res.stdout) == (0, "")
    assert not (tmp_path / OVERRIDES).exists()


def test_no_ledger_is_silent(tmp_path):
    res = _run("gate-override-check.sh", _write_call(tmp_path, "toolu_any00001", "PostToolUse"),
               tmp_path)
    assert (res.returncode, res.stdout) == (0, "")


def test_a_refused_id_inside_written_content_does_not_count(tmp_path):
    # The prefilter matches id-shaped tokens anywhere; only the top-level tool_use_id decides.
    _ledger(tmp_path, "toolu_inbody001")
    payload = _write_call(tmp_path, "toolu_real00001", "PostToolUse",
                          content='{"tool_use_id": "toolu_inbody001"}\n')
    res = _run("gate-override-check.sh", payload, tmp_path)
    assert (res.returncode, res.stdout) == (0, "")


def test_an_unreadable_input_naming_a_refused_id_says_it_could_not_check(tmp_path):
    # Fail-open review (anti-pattern #9): the prefilter found a refused id, the JSON will not parse.
    _ledger(tmp_path, "toolu_refused9")
    res = subprocess.run(["bash", str(HOOKS / "gate-override-check.sh")],
                         input='{"tool_use_id": "toolu_refused9", broken', text=True,
                         capture_output=True, env=_env(tmp_path), timeout=30, check=False)
    assert res.returncode == 0
    ctx = json.loads(res.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "could not be parsed" in ctx
    assert [f["outcome"] for f in _rows(tmp_path / OVERRIDES)] == ["unreadable"]


def test_end_to_end_refusal_then_run_is_flagged(tmp_path):
    project = _fresh(tmp_path)
    assert _run("discovery-gate.sh", _write_call(project, "toolu_e2e00001"), project).returncode == 2
    res = _run("gate-override-check.sh", _write_call(project, "toolu_e2e00001", "PostToolUse"),
               project)
    assert "ran anyway" in json.loads(res.stdout)["systemMessage"]


# ---------------------------------------------------------------- the structural rule

RECORDERS = ("mycelium_record_denial", "mycelium_note_refusal", "hi_deny", "_gate_block_log")
BLOCKED_LOG = re.compile(r'mycelium_log_fire\s+\S+\s+"blocked|_log blocked')
DENY_JSON = re.compile(r"""permissionDecision["']?\s*:\s*["']?deny""")


def _pretool_hooks() -> set[str]:
    reg = json.loads((HOOKS / "hooks.json").read_text())["hooks"]["PreToolUse"]
    names = set()
    for group in reg:
        for h in group["hooks"]:
            m = re.search(r"hooks/([\w.-]+\.sh)", h.get("command", ""))
            if m:
                names.add(m.group(1))
    return names


def _records(window: str) -> bool:
    return any(r in window for r in RECORDERS) or bool(BLOCKED_LOG.search(window))


def _helpers_can_refuse(hook_source: str) -> bool:
    """Does any scripts/*.py this hook names emit a deny or exit 2? The advisory guards'
    helpers (absence-claim, key-shape, shell-safety, ...) only warn or ask, so passing their
    output through needs no recorder."""
    for name in set(re.findall(r"scripts/([a-z_0-9]+\.py)", hook_source)):
        src = (PLUGIN / "scripts" / name).read_text()
        if DENY_JSON.search(src) or re.search(r"[\"']deny[\"']|exit\(2\)|return 2\b", src):
            return True
    return False


def test_every_refusal_site_in_a_pretooluse_hook_records_the_refusal():
    """Every `exit 2`, every inline deny JSON and every pass-through of a helper's verdict in a
    registered PreToolUse hook has a recorder just above it. A new gate that refuses without
    recording would make its refusals invisible to the override check."""
    missing = []
    for name in sorted(_pretool_hooks()):
        missing += _unrecorded(name, (HOOKS / name).read_text())
    assert not missing, "refusal sites with no recorder:\n" + "\n".join(missing)


def _unrecorded(name: str, source: str) -> list[str]:
    lines, out = source.splitlines(), []
    for i, line in enumerate(lines):
        code = line.split("#", 1)[0]
        site = (re.search(r"\bexit 2\b", code) or DENY_JSON.search(code)
                or (re.search(r'\|\s*python3 "\$HELPER"', code) and _helpers_can_refuse(source)))
        if site and not _records("\n".join(lines[max(0, i - 12):i + 3])):
            out.append(f"{name}:{i + 1}: {line.strip()}")
    return out


def test_the_structural_rule_catches_a_gate_that_refuses_without_recording():
    # Positive control (G-V12): each refusal shape, planted with no recorder, is caught; the same
    # shapes with a recorder above them pass.
    planted = {
        "exit2": 'INPUT=$(cat)\necho "no" >&2\nexit 2\n',
        "deny": 'INPUT=$(cat)\ncat <<EOF\n{"permissionDecision": "deny"}\nEOF\n',
        "passthrough": ('HELPER=scripts/framework_guard.py\n'
                        'printf "%s" "$INPUT" | python3 "$HELPER" a b\n'),
    }
    for kind, src in planted.items():
        assert _unrecorded(kind, src), f"{kind}: an unrecorded refusal went unnoticed"
        fixed = "mycelium_record_denial\n" + src
        assert not _unrecorded(kind, fixed), f"{kind}: a recorded refusal was flagged"


def test_the_override_check_is_registered_after_every_gated_tool():
    post = json.loads((HOOKS / "hooks.json").read_text())["hooks"]["PostToolUse"]
    matchers = [g["matcher"] for g in post
                if any("gate-override-check.sh" in h["command"] for h in g["hooks"])]
    assert len(matchers) == 1
    pre = json.loads((HOOKS / "hooks.json").read_text())["hooks"]["PreToolUse"]
    for group in pre:
        if group["matcher"].startswith(("WebSearch",)):
            continue  # read-before-research-guard advises; it never refuses
        for tool in re.findall(r"[A-Za-z_]+(?:\([^)]*\))?", group["matcher"]):
            assert tool in matchers[0], f"{tool} is gated but its calls are never checked"
