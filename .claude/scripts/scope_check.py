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

import fnmatch
import json
import sys


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


def main():
    if len(sys.argv) < 3:
        emit_deny(
            "Mycelium scope-gate: scope_check.py invoked without required arguments. "
            "This is a bug in the hook wrapper."
        )

    state_file = sys.argv[1]
    project_dir = sys.argv[2]

    # Parse state file — fail closed on corruption
    try:
        with open(state_file) as f:
            state = json.load(f)
    except FileNotFoundError:
        # No active execution → allow (fast path should have caught this)
        emit_allow()
    except json.JSONDecodeError as exc:
        emit_deny(
            f"Mycelium scope-gate: active-execution.json is corrupt: {exc}. "
            "Delete the file or run /diamond-progress to recreate it."
        )
    except Exception as exc:
        emit_deny(
            f"Mycelium scope-gate: unexpected error reading state: {exc}. "
            "Delete .claude/state/active-execution.json to disable scope enforcement."
        )

    if not isinstance(state, dict):
        emit_deny(
            "Mycelium scope-gate: active-execution.json has wrong shape (expected object). "
            "Run /diamond-progress to recreate."
        )

    # Parse stdin for tool_input.file_path
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        # Can't read hook input → allow (shouldn't happen in practice)
        emit_allow()

    tool_input = hook_input.get("tool_input", {}) if isinstance(hook_input, dict) else {}
    file_path = tool_input.get("file_path", "") if isinstance(tool_input, dict) else ""

    if not file_path:
        emit_allow()

    # Normalize to relative path for glob matching
    rel_path = file_path
    if file_path.startswith(project_dir):
        rel_path = file_path[len(project_dir):].lstrip("/")

    # Always allow .claude/** edits (framework self-modification, canvas updates,
    # state file writes by other hooks). Scope enforcement is for SOURCE CODE
    # in L4 delivery, not for framework internals.
    if rel_path.startswith(".claude/") or file_path.startswith(f"{project_dir}/.claude/"):
        emit_allow()

    # Extract scope lists — support both top-level and spec-nested
    spec = state.get("spec", {}) if isinstance(state.get("spec"), dict) else {}
    in_scope = spec.get("in_scope_paths") or state.get("in_scope_paths") or []
    out_of_scope = spec.get("out_of_scope_paths") or state.get("out_of_scope_paths") or []

    if not isinstance(in_scope, list):
        in_scope = []
    if not isinstance(out_of_scope, list):
        out_of_scope = []

    diamond_id = state.get("diamond_id", "unknown")

    # out_of_scope takes precedence
    for pattern in out_of_scope:
        if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(file_path, pattern):
            emit_deny(
                f"GUARDRAIL SCOPE VIOLATION: File path '{rel_path}' matches out_of_scope_paths "
                f"in active execution plan for diamond {diamond_id} (pattern: {pattern}). "
                f"Review .claude/state/active-execution.json or run /diamond-progress to update scope."
            )

    # If in_scope is empty, no scope declared → allow
    if not in_scope:
        emit_allow()

    # Check in_scope match
    for pattern in in_scope:
        if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(file_path, pattern):
            emit_allow()

    # Did not match any in_scope pattern → deny
    emit_deny(
        f"GUARDRAIL SCOPE VIOLATION: File path '{rel_path}' is not in in_scope_paths "
        f"for active execution plan (diamond {diamond_id}). "
        f"Review .claude/state/active-execution.json or run /diamond-progress to update scope."
    )


if __name__ == "__main__":
    main()
