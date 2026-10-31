"""Mycelium on Mistral Vibe: the native manifest, the hook translator and its installer (v0.332.0).

WHY. On Vibe 3.0, as shipped, the plugin loaded nothing: its folder carries both a Claude Code and a
Codex manifest, which Vibe treats as a fatal ambiguity. With the Codex manifest deleted the skills
loaded and no gate ran, because Vibe binds no hook a plugin ships. Measured 2026-10-21 on Vibe 3.0.0
(docs/integrations/vibe.md, 0.328.3). Three changes, each tested here:

  1. A root plugin.json in the Agent Plugins 1.0 format. Vibe reads it in place of both others.
     Codex 0.166 reads it too, and takes hooks from `extensions."com.openai"` or, when that is
     absent, from .codex-plugin/plugin.json as an overlay (codex-rs/core-plugins/src/manifest/
     manifest_cache.rs). So it must carry no com.openai extension, or Codex loses its hooks.
  2. integrations/vibe/vibe_hook.py runs the plugin's own Claude Code tool hooks for Vibe's
     pre_tool and post_tool events, translating the call in and the answer out.
  3. integrations/vibe/install_hooks.py declares it in the project's .vibe/hooks.toml, keeping the
     project's own hooks.
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import _scratch_git
import pytest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
VIBE = PLUGIN / "integrations" / "vibe"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


vh = _load("vibe_hook", VIBE / "vibe_hook.py")
ih = _load("install_hooks", VIBE / "install_hooks.py")

# The AWS documentation's example key, assembled so no line of this file holds it whole.
EXAMPLE_KEY = "AKIA" + "IOSFODNN7" + "EXAMPLE"


# ------------------------------------------------------------------ 1. the native manifest

def test_the_native_manifest_is_agent_plugins_1_0_and_matches_the_claude_manifest():
    n = json.loads((PLUGIN / "plugin.json").read_text())
    c = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    assert n["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    allowed = {"$schema", "name", "version", "description", "author", "homepage", "repository",
               "license", "keywords", "extensions"}
    assert set(n) <= allowed, set(n) - allowed  # the 1.0 schema sets additionalProperties: false
    assert re.fullmatch(r"(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", n["name"])
    for key in ("name", "version", "description"):
        assert n[key] == c[key], key


def test_the_native_manifest_leaves_codex_its_own_hooks():
    """With no com.openai extension Codex overlays .codex-plugin/plugin.json, which names the hooks."""
    n = json.loads((PLUGIN / "plugin.json").read_text())
    assert "com.openai" not in (n.get("extensions") or {})
    codex = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text())
    assert codex.get("hooks"), "the overlay is where Codex finds the hooks"


def test_the_native_manifest_is_a_version_target():
    sd = _load("sync_derived", PLUGIN / "scripts" / "sync_derived.py")
    assert any(rel == sd.NATIVE_PLUGIN for rel, _, _ in sd.VERSION_TARGETS)
    assert (ROOT / sd.NATIVE_PLUGIN).is_file()


# ------------------------------------------------------------------ 2. the translator

@pytest.mark.parametrize(("vibe_name", "args", "tool", "expected"), [
    ("file_system.bash", {"command": "ls"}, "Bash", {"command": "ls"}),
    ("bash", {"command": "ls"}, "Bash", {"command": "ls"}),
    ("process.start", {"command": "npm run dev"}, "Bash", {"command": "npm run dev"}),
    ("file_system.write_file", {"path": "/p/a.txt", "content": "x"}, "Write",
     {"file_path": "/p/a.txt", "content": "x"}),
    ("write_file", {"file_path": "/p/a.txt", "content": "x"}, "Write",
     {"file_path": "/p/a.txt", "content": "x"}),
    ("file_system.edit", {"file_path": "/p/a.txt", "old_string": "a", "new_string": "b"}, "Edit",
     {"file_path": "/p/a.txt", "old_string": "a", "new_string": "b", "replace_all": False}),
    ("file_system.read_file", {"path": "/p/a.txt"}, "Read", {"file_path": "/p/a.txt"}),
])
def test_vibe_calls_translate_to_claude_code_calls(vibe_name, args, tool, expected):
    assert vh.translate(vibe_name, args, "/p") == (tool, expected)


def test_a_relative_path_is_resolved_against_the_calls_folder():
    assert vh.translate("file_system.write_file", {"path": "src/a.py", "content": ""}, "/p")[1]["file_path"] == "/p/src/a.py"


def test_control_a_tool_no_hook_covers_is_not_translated():
    assert vh.translate("file_system.grep", {"pattern": "x"}, "/p") is None
    assert vh.translate("task", {"agent": "reviewer"}, "/p") is None


def test_matchers_are_read_as_claude_code_reads_them():
    doc = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())
    assert vh.hooks_for(doc, "PreToolUse", "Bash")
    assert vh.hooks_for(doc, "PreToolUse", "Write")
    assert not vh.hooks_for(doc, "PreToolUse", "Read")
    assert not vh.hooks_for(doc, "PreToolUse", "Bashful"), "a matcher must match the whole name"


BLOCKING = {"command": "x", "onFailure": "block"}
ADVISORY = {"command": "x"}


@pytest.mark.parametrize(("hook", "result", "kind"), [
    (ADVISORY, {"status": 2, "stdout": "", "stderr": "no"}, "deny"),
    (ADVISORY, {"status": 0, "stdout": json.dumps({"hookSpecificOutput": {"permissionDecision": "deny",
                "permissionDecisionReason": "no"}}), "stderr": ""}, "deny"),
    (ADVISORY, {"status": 0, "stdout": json.dumps({"decision": "block", "reason": "no"}), "stderr": ""}, "deny"),
    (ADVISORY, {"status": 0, "stdout": json.dumps({"hookSpecificOutput": {"permissionDecision": "ask",
                "permissionDecisionReason": "?"}}), "stderr": ""}, "ask"),
    (ADVISORY, {"status": 0, "stdout": json.dumps({"hookSpecificOutput": {"additionalContext": "note"}}),
                "stderr": ""}, "advise"),
    (ADVISORY, {"status": 0, "stdout": "", "stderr": ""}, "none"),
    # A hook that cannot run: a blocking one refuses, an advisory one is ignored (Claude Code since 0.322.1).
    (BLOCKING, {"failed": "timed out after 30 s"}, "deny"),
    (ADVISORY, {"failed": "timed out after 30 s"}, "none"),
    (BLOCKING, {"status": 1, "stdout": "", "stderr": "boom"}, "deny"),
    (ADVISORY, {"status": 1, "stdout": "", "stderr": "boom"}, "none"),
    (BLOCKING, {"status": 0, "stdout": "{} {}", "stderr": ""}, "deny"),
    (ADVISORY, {"status": 0, "stdout": "not json", "stderr": ""}, "none"),
])
def test_hook_answers_are_read_as_claude_code_reads_them(hook, result, kind):
    assert vh.read_answer(hook, result)[0] == kind


@pytest.fixture
def project(tmp_path):
    (tmp_path / ".claude" / "canvas").mkdir(parents=True)
    (tmp_path / ".claude" / "state").mkdir()
    _scratch_git.init(tmp_path)
    return tmp_path


def _run(mode: str, project: Path, tool: str, args: dict, call_id: str = "c1", **extra) -> dict | None:
    event = {"hook_event_name": f"{mode}_tool", "cwd": str(project), "session_id": "s1",
             "tool_name": tool, "tool_call_id": call_id, "tool_input": args, **extra}
    p = subprocess.run([sys.executable, "-I", str(VIBE / "vibe_hook.py"), mode], input=json.dumps(event),
                       text=True, capture_output=True, cwd=project, timeout=120, check=False)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout) if p.stdout.strip() else None


def test_the_secret_check_refuses_a_key_on_a_vibe_command_line(project):
    out = _run("pre", project, "file_system.bash", {"command": f"echo {EXAMPLE_KEY} > leak.txt"})
    assert out and out["decision"] == "deny" and "G-S1" in out["reason"]


def test_control_a_plain_command_passes(project):
    assert _run("pre", project, "file_system.bash", {"command": "ls"}) is None


def test_a_write_that_claude_code_would_ask_about_is_refused_on_vibe(project):
    out = _run("pre", project, "file_system.write_file", {"path": ".claude/state/scale-lock-ack", "content": "x"})
    assert out and out["decision"] == "deny" and "(vibe) cannot ask" in out["reason"]


def test_pre_tool_advice_reaches_the_model_with_the_calls_result(project):
    cmd = {"command": "cat a.txt | head -1; echo $?"}
    assert _run("pre", project, "file_system.bash", cmd, call_id="c-adv") is None
    out = _run("post", project, "file_system.bash", cmd, call_id="c-adv", tool_status="success",
               tool_output={"output": ""})
    assert out and "SHELL-SAFETY" in out["hook_specific_output"]["additional_context"]
    # handed over once
    again = _run("post", project, "file_system.bash", {"command": "true"}, call_id="c-adv",
                 tool_status="success", tool_output={"output": ""})
    assert not again or "SHELL-SAFETY" not in again["hook_specific_output"]["additional_context"]


def test_control_outside_a_mycelium_project_nothing_is_refused(tmp_path):
    _scratch_git.init(tmp_path)
    assert _run("pre", tmp_path, "file_system.write_file", {"path": "src/app.py", "content": "x"}) is None


# In process, with stand-in hooks: what each answer becomes, without the plugin's own hooks.

def _doc(event: str, *commands: str, **extra) -> dict:
    return {"hooks": {event: [{"matcher": "Bash", "hooks": [{"type": "command", "command": c, **extra}
                                                            for c in commands]}]}}


def _ask(reason: str) -> str:
    return "printf '%s' " + json.dumps(json.dumps(
        {"hookSpecificOutput": {"permissionDecision": "ask", "permissionDecisionReason": reason}}))


def _advise(note: str) -> str:
    return "printf '%s' " + json.dumps(json.dumps({"hookSpecificOutput": {"additionalContext": note}}))


def _event(tmp_path: Path, call_id: str = "", **extra) -> dict:
    return {"cwd": str(tmp_path), "tool_name": "file_system.bash", "tool_input": {"command": "ls"},
            "tool_call_id": call_id, **extra}


def test_a_hook_runs_with_the_plugin_root_and_the_runtime_named(tmp_path):
    out = vh.run_hook({"command": 'printf "%s|%s|%s" "$MYCELIUM_RUNTIME" "$CLAUDE_PLUGIN_ROOT" '
                                  '"$CLAUDE_PROJECT_DIR"'}, "{}", str(tmp_path))
    assert out["status"] == 0
    assert out["stdout"] == f"vibe|{vh.PLUGIN_ROOT}|{tmp_path}"


def test_a_hook_that_outruns_its_timeout_is_a_failure_not_an_answer(tmp_path):
    out = vh.run_hook({"command": "sleep 5", "timeout": 0.2}, "{}", str(tmp_path))
    assert out == {"failed": "timed out after 0.2 s"}


def test_a_deny_and_an_ask_are_refused_together_with_both_reasons(tmp_path):
    doc = _doc("PreToolUse", "echo first-no >&2; exit 2", _ask("second, ask the person"))
    out = vh.pre_tool(_event(tmp_path), doc)
    assert out["decision"] == "deny"
    assert "first-no" in out["reason"] and vh.ASK_PREFIX + "second, ask the person" in out["reason"]


def test_control_a_tool_no_hook_matches_runs_nothing(tmp_path):
    doc = _doc("PreToolUse", "exit 2")
    assert vh.pre_tool({**_event(tmp_path), "tool_name": "file_system.read_file",
                        "tool_input": {"path": "a"}}, doc) is None
    assert vh.pre_tool({**_event(tmp_path), "tool_name": "task"}, doc) is None


def test_advice_waits_for_the_result_and_post_hooks_add_theirs(tmp_path):
    call = f"c-{tmp_path.name}"
    assert vh.pre_tool(_event(tmp_path, call), _doc("PreToolUse", _advise("before"))) is None
    out = vh.post_tool(_event(tmp_path, call, tool_status="success", tool_output={"output": ""}),
                       _doc("PostToolUse", _advise("after")))
    assert out["hook_specific_output"]["additional_context"] == "before\n\nafter"
    assert vh.post_tool(_event(tmp_path, call), {"hooks": {}}) is None, "handed over once"


def test_a_failed_call_gets_its_advice_and_no_after_call_checks(tmp_path):
    call = f"f-{tmp_path.name}"
    vh.pre_tool(_event(tmp_path, call), _doc("PreToolUse", _advise("before")))
    out = vh.post_tool(_event(tmp_path, call, tool_status="error"), _doc("PostToolUse", _advise("after")))
    assert out["hook_specific_output"]["additional_context"] == "before"


def test_control_advice_with_no_call_id_is_not_kept(tmp_path):
    assert vh.pre_tool(_event(tmp_path), _doc("PreToolUse", _advise("before"))) is None
    assert vh.post_tool(_event(tmp_path), {"hooks": {}}) is None


def test_main_prints_the_answer_and_refuses_an_unknown_mode(tmp_path, monkeypatch, capsys):
    hooks_file = tmp_path / "hooks.json"
    hooks_file.write_text(json.dumps(_doc("PreToolUse", "echo no >&2; exit 2")))
    monkeypatch.setattr(vh, "HOOKS_FILE", hooks_file)
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO(json.dumps(_event(tmp_path))))
    assert vh.main(["vibe_hook.py", "pre"]) == 0
    assert json.loads(capsys.readouterr().out) == {"decision": "deny", "reason": "no"}
    assert vh.main(["vibe_hook.py", "sideways"]) == 1
    assert "usage" in capsys.readouterr().err


# ------------------------------------------------------------------ 3. the installer

def _hooks(path: Path) -> list[dict]:
    import tomllib
    return tomllib.loads(path.read_text())["hooks"]


def test_install_writes_both_entries_with_this_copys_path(tmp_path):
    target, changed = ih.install(tmp_path)
    assert changed and target == tmp_path / ".vibe" / "hooks.toml"
    hooks = {h["name"]: h for h in _hooks(target)}
    pre, post = hooks["mycelium-pre-tool"], hooks["mycelium-post-tool"]
    assert pre["type"] == "pre_tool" and pre["strict"] is True
    assert post["type"] == "post_tool" and not post.get("strict")
    assert str(VIBE / "vibe_hook.py") in pre["command"] and pre["command"].endswith(" pre")


def test_install_is_idempotent(tmp_path):
    ih.install(tmp_path)
    first = (tmp_path / ".vibe" / "hooks.toml").read_text()
    assert ih.install(tmp_path) == (tmp_path / ".vibe" / "hooks.toml", False)
    assert (tmp_path / ".vibe" / "hooks.toml").read_text() == first


def test_install_keeps_the_projects_own_hooks_and_replaces_a_stale_mycelium_entry(tmp_path):
    (tmp_path / ".vibe").mkdir()
    stale = ih.block(Path("/old/copy/of/mycelium"))
    own = '[[hooks]]\nname = "lint"\ntype = "post_agent"\ncommand = "make lint"\n'
    (tmp_path / ".vibe" / "hooks.toml").write_text(own + "\n" + stale)
    ih.install(tmp_path)
    text = (tmp_path / ".vibe" / "hooks.toml").read_text()
    names = [h["name"] for h in _hooks(tmp_path / ".vibe" / "hooks.toml")]
    assert names == ["lint", "mycelium-pre-tool", "mycelium-post-tool"]
    assert "/old/copy/of/mycelium" not in text


def test_control_an_unreadable_hooks_file_is_left_alone(tmp_path):
    (tmp_path / ".vibe").mkdir()
    broken = "[[hooks]\nname = \n"
    (tmp_path / ".vibe" / "hooks.toml").write_text(broken)
    with pytest.raises(ValueError, match="not valid TOML"):
        ih.install(tmp_path)
    assert (tmp_path / ".vibe" / "hooks.toml").read_text() == broken
