#!/usr/bin/env python3
"""
Mycelium scope enforcement helper — Python stdlib only.

Reads a Claude Code PreToolUse hook JSON from stdin, reads the active execution
plan JSON from the first argument, and decides whether the tool_input.file_path
is within the declared in_scope_paths. Emits hook output JSON on stdout.

Called by .claude/hooks/scope-gate.sh.

Usage:
    python3 scope_check.py <state_file_path> <project_dir>

Input (stdin): Claude Code hook JSON:
    {
        "tool_input": {"file_path": "..."},
        ...
    }

State file (first arg): active-execution.json with schema:
    {
        "schema_version": 1,
        "diamond_id": "L4-feature-xyz",
        "phase": "deliver",
        "in_scope_paths": ["src/xyz/**", "tests/xyz/**"],
        "out_of_scope_paths": ["src/xyz/legacy/**"]
    }

Decision logic:
- If in_scope_paths is empty → allow (no scope declared)
- If path matches out_of_scope_paths → deny (precedence)
- If path matches in_scope_paths → allow
- Otherwise → deny
- If state file is malformed → deny (fail-closed)
"""

import functools
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hook_input as hi  # sibling module, after the path insert


@functools.lru_cache(maxsize=256)
def _compile_glob(pattern: str) -> "re.Pattern[str]":
    """Compile a path glob to a regex with path-segment semantics.

    Unlike fnmatch (where ``*`` matches ``/`` too — letting ``src/xyz/*`` leak
    into ``src/xyz/legacy/...``), here:
      - ``*``   matches within a single path segment (no ``/``)
      - ``?``   matches a single non-``/`` char
      - ``**``  matches across segments (any depth)
      - ``**/`` matches zero-or-more leading segments, so ``**/foo`` hits both
                top-level ``foo`` and nested ``a/b/foo``
    """
    out = []
    i = 0
    n = len(pattern)
    while i < n:
        c = pattern[i]
        if c == "*":
            if pattern[i + 1 : i + 2] == "*":
                if pattern[i + 2 : i + 3] == "/":
                    out.append("(?:.*/)?")  # **/  → zero-or-more dirs
                    i += 3
                else:
                    out.append(".*")  # **   → any depth
                    i += 2
            else:
                out.append("[^/]*")  # *    → single segment
                i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def _glob_match(path: str, pattern: str) -> bool:
    return bool(_compile_glob(pattern).match(path))


def emit_allow():
    """Silent allow — just exit 0."""
    sys.exit(0)


def emit_deny(reason: str):
    """Emit a deny decision with a reason and exit 0."""
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(output))
    sys.exit(0)


REQUIRED_ARG_COUNT = 3  # script name + state_file + project_dir


def _load_state_or_exit(state_file: str) -> dict:
    try:
        with open(state_file) as f:
            state = json.load(f)
    except FileNotFoundError:
        emit_allow()  # no active execution
    except json.JSONDecodeError as exc:
        emit_deny(f"Mycelium scope-gate: active-execution.json is corrupt: {exc}. "
                  "Delete the file or run /diamond-progress to recreate it.")
    except OSError as exc:
        emit_deny(f"Mycelium scope-gate: unexpected error reading state: {exc}. "
                  "Delete .claude/state/active-execution.json to disable scope enforcement.")
    if not isinstance(state, dict):
        emit_deny("Mycelium scope-gate: active-execution.json has wrong shape "
                  "(expected object). Run /diamond-progress to recreate.")
    return state


def _scope_lists(state: dict) -> tuple[list, list, str]:
    spec = state.get("spec", {}) if isinstance(state.get("spec"), dict) else {}
    in_scope = spec.get("in_scope_paths") or state.get("in_scope_paths") or []
    out_of_scope = spec.get("out_of_scope_paths") or state.get("out_of_scope_paths") or []
    if not isinstance(in_scope, list):
        in_scope = []
    if not isinstance(out_of_scope, list):
        out_of_scope = []
    return in_scope, out_of_scope, str(state.get("diamond_id", "unknown"))


def _judge(rel: str, in_scope: list, out_of_scope: list, diamond_id: str, via: str) -> None:
    """Deny when `rel` (already resolved, inside the project) is out of scope."""
    for pattern in out_of_scope:
        if _glob_match(rel, pattern):
            emit_deny(f"GUARDRAIL SCOPE VIOLATION: File path '{rel}' ({via}) matches "
                      f"out_of_scope_paths in active execution plan for diamond {diamond_id} "
                      f"(pattern: {pattern}). Review .claude/state/active-execution.json "
                      "or run /diamond-progress.")
    if not in_scope:
        return
    if any(_glob_match(rel, pattern) for pattern in in_scope):
        return
    emit_deny(f"GUARDRAIL SCOPE VIOLATION: File path '{rel}' ({via}) is not in in_scope_paths "
              f"for active execution plan (diamond {diamond_id}). Review "
              ".claude/state/active-execution.json or run /diamond-progress.")


@hi.fail_closed("scope-gate")
def main():
    """Entry point. Paths are resolved to their REAL location (`..`, symlinks, case) before any
    glob is consulted; every path key is read; Bash write targets are judged too; guard-state
    writes ask the human; a crash denies. Each of those was a demonstrated bypass on
    2026-09-11 (dogfood evals/security)."""
    if len(sys.argv) < REQUIRED_ARG_COUNT:
        emit_deny("Mycelium scope-gate: scope_check.py invoked without required arguments. "
                  "This is a bug in the hook wrapper.")
    state_file, project_dir = sys.argv[1], sys.argv[2]
    state = _load_state_or_exit(state_file)
    hook_input = hi.read_input()
    tool_name = str(hook_input.get("tool_name") or "")
    tool_input = hook_input.get("tool_input") or {}
    hi.guard_state_check("scope-gate", tool_name, tool_input, project_dir)
    in_scope, out_of_scope, diamond_id = _scope_lists(state)
    if tool_name == "Bash":
        scan = hi.bash_write_targets(str(tool_input.get("command", "") or ""), project_dir)
        targets = scan.targets
        if scan.opaque and in_scope:
            emit_deny("GUARDRAIL SCOPE VIOLATION: this Bash command writes to a target the "
                      f"gate cannot read ({'; '.join(scan.opaque[:3])}) while an execution "
                      f"plan for diamond {diamond_id} declares in_scope_paths. Name the file "
                      "literally, or use the Write/Edit tool.")
    else:
        targets = [hi.resolve(pth, project_dir, key=k) for k, pth in hi.target_paths(tool_input)]
    for r in targets:
        if not r.inside:
            emit_deny(f"GUARDRAIL SCOPE VIOLATION: '{r.given}' resolves to {r.real}, outside "
                      f"the project, while an execution plan for diamond {diamond_id} is active.")
        rel = r.rel or ""
        if rel.startswith(".claude/") or rel == ".claude":
            continue  # canvas, state, memory: not source code
        _judge(rel, in_scope, out_of_scope, diamond_id, r.key)
    emit_allow()


if __name__ == "__main__":
    main()
