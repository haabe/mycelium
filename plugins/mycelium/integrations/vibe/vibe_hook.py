#!/usr/bin/env python3
"""Run Mycelium's tool hooks on Mistral Vibe (v0.332.0).

Vibe 3.0 runs no hook a plugin ships: its Unified Harness binds hooks from hooks.toml files only
("Tool groups and hook bindings are withheld", vibe/app_server/_plugins.py, 3.0.1 to 3.0.3). So
install_hooks.py declares this script in the project's .vibe/hooks.toml, once for `pre_tool` and
once for `post_tool`, and this script runs the plugin's own Claude Code hooks from hooks/hooks.json:
the same scripts, in the same project, with Vibe's call translated into the input they read and
their answer translated back. Measured 2026-10-21 on Vibe 3.0.0 with gate.sh behind a 40-line
version of this (dogfood landscape comp-038, run 3b): the secret check refused the command and its
message reached the model.

WHAT IS TRANSLATED.
  Vibe (Unified Harness)         Claude Code      input
  file_system.bash, process.start  Bash          command
  file_system.write_file           Write         path -> file_path, content
  file_system.edit                 Edit          file_path, old_string, new_string, replace_all
  file_system.read_file            Read          path -> file_path
A bare name (`bash`, `write_file`, ...) is read the same way, and `file_path` is accepted where
`path` is expected. Any other tool runs no Mycelium hook. A relative path is resolved against the
call's `cwd`, since every Mycelium hook is written for Claude Code's absolute paths.

WHAT THE ANSWERS BECOME.
  - A refusal (exit status 2, `permissionDecision: "deny"`, or `decision: "block"`) is a Vibe deny,
    and its reason is what the model reads.
  - `ask` is a deny too. Vibe has no way for a hook to put a question to the person, and on Codex
    an ask that cannot be asked went through (hooks/README.md, v0.286.0). The hooks already refuse
    instead of asking when MYCELIUM_RUNTIME is a runtime that cannot ask; this is the backstop.
  - A blocking hook (`onFailure: "block"`) that cannot start, times out, or answers in a form this
    script cannot read refuses the call, as it does in Claude Code since 0.322.1. Any other hook's
    failure is ignored, as there.
  - Advice (`additionalContext`) from a pre_tool hook cannot reach the model before the call: a
    Vibe pre_tool answer carries text to the model only as a deny reason. It is kept, keyed by the
    call's id, and handed to the model with the call's result by the post_tool run, with the
    post_tool hooks' own advice.

WHAT IS NOT RUN. SessionStart, UserPromptSubmit, Stop and PostToolUseFailure have no Vibe event
(Vibe's hook types are pre_tool, post_tool and post_agent). docs/integrations/vibe.md says what that
leaves out and how the operating contract reaches the model instead (AGENTS.md).

The plugin root is this file's own location, never CLAUDE_PLUGIN_ROOT: on Vibe that variable is
not set by the runtime, and where a shell profile sets it, it names some other copy (comp-038 run
3b found exactly that). Run with `python3 -I`: a hook's working directory is the project, and the
project's files must not be imported in place of the standard library (hooks/README.md, 0.322.4).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
HOOKS_FILE = PLUGIN_ROOT / "hooks" / "hooks.json"
DEFAULT_TIMEOUT = 60.0
REFUSE_STATUS = 2  # Claude Code's "blocking error" exit status

ASK_PREFIX = ("Mycelium would ask the person here, and Vibe cannot ask from a hook, so the call is "
              "refused. Tell the person what you were about to do and why; if they agree, they "
              "make this change themselves. ")


def _path_arg(args: dict) -> str:
    return str(args.get("path") or args.get("file_path") or "")


def _command(args: dict) -> dict:
    return {"command": str(args.get("command", ""))}


def _write_input(args: dict) -> dict:
    return {"file_path": _path_arg(args), "content": str(args.get("content", ""))}


def _edit_input(args: dict) -> dict:
    return {"file_path": str(args.get("file_path") or args.get("path") or ""),
            "old_string": str(args.get("old_string", "")),
            "new_string": str(args.get("new_string", "")),
            "replace_all": bool(args.get("replace_all", False))}


#: Vibe tool name, prefix stripped -> (Claude Code tool name, input mapper).
TOOLS = {
    "bash": ("Bash", _command),
    "process.start": ("Bash", _command),
    "write_file": ("Write", _write_input),
    "edit": ("Edit", _edit_input),
    "read_file": ("Read", lambda a: {"file_path": _path_arg(a)}),
}


def translate(tool_name: str, tool_input, cwd: str) -> tuple[str, dict] | None:
    """Vibe's tool call as Claude Code's (tool name, input), or None for a tool no hook covers."""
    entry = TOOLS.get(str(tool_name or "").removeprefix("file_system."))
    if entry is None:
        return None
    claude_name, mapper = entry
    mapped = mapper(tool_input if isinstance(tool_input, dict) else {})
    fp = mapped.get("file_path")
    if fp and cwd and not os.path.isabs(fp):
        mapped["file_path"] = os.path.normpath(os.path.join(cwd, fp))
    return claude_name, mapped


def hooks_for(doc: dict, event: str, tool: str) -> list[dict]:
    """The hook entries of `event` whose matcher names `tool`, in file order."""
    out = []
    for group in (doc.get("hooks") or {}).get(event) or []:
        matcher = group.get("matcher") or ""
        if matcher and not re.fullmatch(matcher, tool):
            continue
        out.extend(h for h in group.get("hooks") or [] if h.get("type", "command") == "command")
    return out


def _env(cwd: str) -> dict:
    env = dict(os.environ)
    env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN_ROOT)
    env["CLAUDE_PROJECT_DIR"] = cwd
    env["MYCELIUM_RUNTIME"] = "vibe"
    return env


def run_hook(hook: dict, payload: str, cwd: str) -> dict:
    """Run one hook command. Returns {status, stdout, stderr} or {failed: why}."""
    timeout = float(hook.get("timeout") or DEFAULT_TIMEOUT)
    try:
        p = subprocess.run(["bash", "-c", hook["command"]], input=payload, text=True,
                           capture_output=True, cwd=cwd or None, env=_env(cwd),
                           timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return {"failed": f"timed out after {timeout:g} s"}
    except OSError as e:
        return {"failed": f"could not start ({e})"}
    return {"status": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


def _script(hook: dict) -> str:
    m = re.findall(r"hooks/([\w.-]+\.(?:sh|py))", hook.get("command", ""))
    return m[-1] if m else "a hook"


def _failure(hook: dict, what: str) -> tuple[str, str]:
    """A hook that could not answer: a blocking one refuses, any other is ignored."""
    if hook.get("onFailure") != "block":
        return "none", ""
    return "deny", f"Mycelium hook {_script(hook)} {what}, and it refuses when it cannot run."


def _json_answer(hook: dict, doc: dict) -> tuple[str, str]:
    hso = doc.get("hookSpecificOutput")
    hso = hso if isinstance(hso, dict) else {}
    decision = hso.get("permissionDecision")
    reason = str(hso.get("permissionDecisionReason") or doc.get("reason") or "").strip()
    if decision == "deny" or doc.get("decision") == "block":
        return "deny", reason or f"Mycelium hook {_script(hook)} refused the call."
    if decision == "ask":
        return "ask", reason
    parts = (hso.get("additionalContext"), doc.get("systemMessage"))
    advice = "\n".join(str(x).strip() for x in parts if x)
    return ("advise", advice) if advice else ("none", "")


def read_answer(hook: dict, result: dict) -> tuple[str, str]:
    """One hook's answer as (kind, text): kind is deny, ask, advise, or none."""
    if "failed" in result:
        return _failure(hook, result["failed"])
    status, out, err = result["status"], result["stdout"].strip(), result["stderr"].strip()
    if status == REFUSE_STATUS:
        return "deny", err or out or f"Mycelium hook {_script(hook)} refused the call."
    if status != 0:
        return _failure(hook, f"failed (exit {status}){': ' + err if err else ''}")
    if not out:
        return "none", ""
    try:
        doc = json.loads(out)
    except ValueError:
        doc = None
    if not isinstance(doc, dict):
        return _failure(hook, "answered in a form that could not be read")
    return _json_answer(hook, doc)


def run_all(hooks: list[dict], payload: dict, cwd: str) -> list[tuple[str, str]]:
    """Every hook's answer, in file order. The hooks run side by side, as Claude Code runs them."""
    text = json.dumps(payload)
    with ThreadPoolExecutor(max_workers=max(1, min(8, len(hooks)))) as pool:
        results = list(pool.map(lambda h: run_hook(h, text, cwd), hooks))
    return [read_answer(h, r) for h, r in zip(hooks, results, strict=True)]


def _stash(call_id: str) -> Path:
    key = hashlib.sha256(call_id.encode()).hexdigest()[:32]
    uid = os.getuid() if hasattr(os, "getuid") else 0
    return Path(tempfile.gettempdir()) / f"mycelium-vibe-{uid}" / key


def _payload(event: dict, name: str, tool: str, tool_input: dict, cwd: str) -> dict:
    return {"session_id": event.get("session_id") or "", "transcript_path": "", "cwd": cwd,
            "hook_event_name": name, "tool_name": tool, "tool_input": tool_input,
            "tool_use_id": str(event.get("tool_call_id") or "")}


def pre_tool(event: dict, doc: dict) -> dict | None:
    cwd = str(event.get("cwd") or os.getcwd())
    t = translate(event.get("tool_name"), event.get("tool_input"), cwd)
    if t is None:
        return None
    tool, tool_input = t
    hooks = hooks_for(doc, "PreToolUse", tool)
    if not hooks:
        return None
    answers = run_all(hooks, _payload(event, "PreToolUse", tool, tool_input, cwd), cwd)
    refusals = [txt for kind, txt in answers if kind == "deny"]
    refusals += [ASK_PREFIX + txt for kind, txt in answers if kind == "ask"]
    if refusals:
        return {"decision": "deny", "reason": "\n\n".join(r for r in refusals if r)}
    advice = [txt for kind, txt in answers if kind == "advise"]
    call_id = str(event.get("tool_call_id") or "")
    if advice and call_id:
        path = _stash(call_id)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_text("\n\n".join(advice), encoding="utf-8")
    return None


def post_tool(event: dict, doc: dict) -> dict | None:
    cwd = str(event.get("cwd") or os.getcwd())
    call_id = str(event.get("tool_call_id") or "")
    notes = []
    if call_id:
        path = _stash(call_id)
        if path.is_file():
            notes.append(path.read_text(encoding="utf-8"))
            path.unlink(missing_ok=True)
    t = translate(event.get("tool_name"), event.get("tool_input"), cwd)
    if t is not None and event.get("tool_status", "success") == "success":
        tool, tool_input = t
        hooks = hooks_for(doc, "PostToolUse", tool)
        if hooks:
            payload = _payload(event, "PostToolUse", tool, tool_input, cwd)
            payload["tool_response"] = event.get("tool_output")
            notes += [txt for kind, txt in run_all(hooks, payload, cwd) if kind != "none" and txt]
    if not notes:
        return None
    return {"hook_specific_output": {"additional_context": "\n\n".join(notes)}}


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else ""
    if mode not in ("pre", "post"):
        print("usage: vibe_hook.py pre|post  (reads Vibe's hook event on stdin)", file=sys.stderr)
        return 1
    event = json.loads(sys.stdin.read() or "{}")
    doc = json.loads(HOOKS_FILE.read_text(encoding="utf-8"))
    answer = (pre_tool if mode == "pre" else post_tool)(event, doc)
    if answer:
        print(json.dumps(answer))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
