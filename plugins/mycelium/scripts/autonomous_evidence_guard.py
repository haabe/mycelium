#!/usr/bin/env python3
"""Autonomous-mode evidence-integrity guard (PreToolUse helper).

Enforces, as MECHANISM, the boundary that engine/autonomous-mode.md states as
prose: inside a DECLARED autonomous run, the running model must not write
fabricated or elevated evidence into the structured canvas. Motivated by opp-011
Stage A (2026-06-11): Haiku 4.5 fabricated `external_human` interview results,
flipped `validated`, and built a confidence delta on it -- without knowing it
had crossed the boundary. Prose did not transfer below Fable 5; this is the
enforcement.

Activation -- autonomous mode declared, on a hook-visible surface:
  - env MYCELIUM_AUTONOMOUS_RUN in {1,true,yes,on} (case-insensitive), OR
  - .claude/diamonds/active.yml has a top-level `autonomous: true`.
If neither -> not autonomous -> allow (a present human's judgment stands;
"a present human always outranks the flag").

Enforced files: .claude/canvas/*.yml, .claude/diamonds/*.yml and the
mycelium-state/ mirror equivalents -- the structured evidence ledger where these
tokens are schema assignments, not prose.

Forbidden assignments in the written content (an autonomous run cannot
legitimately produce any of these -- no human or world answered, only the
persona simulated):
  - source_class: external_human | external_data
  - validated: true
  - evidence_type: anecdotal | data-supported | test-validated | launch-validated
Permitted: internal_simulated / speculation / validated: false.

I/O contract (Claude Code PreToolUse):
  stdin: tool input JSON; argv[1]: project dir
  exit 0 silent                                  -> allow
  exit 0 + JSON permissionDecision=deny          -> block with UI message
Fail-open on unparseable input (a guard bug must never brick all writes).
"""
import json
import os
import re
import sys

FORBIDDEN = [
    (re.compile(r'(?m)^\s*source_class:\s*["\']?external_human\b'),
     "source_class: external_human"),
    (re.compile(r'(?m)^\s*source_class:\s*["\']?external_data\b'),
     "source_class: external_data"),
    (re.compile(r"(?m)^\s*validated:\s*true\b"),
     "validated: true"),
    (re.compile(r'(?m)^\s*evidence_type:\s*["\']?'
                r'(anecdotal|data-supported|test-validated|launch-validated)\b'),
     "evidence_type above speculation"),
]

ENFORCED_PATH = re.compile(
    r"(^|/)(\.claude|mycelium-state)/(canvas|diamonds)/[^/]+\.ya?ml$")


def truthy(value):
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def autonomous_active(project_dir):
    if truthy(os.environ.get("MYCELIUM_AUTONOMOUS_RUN", "")):
        return True
    active = os.path.join(project_dir, ".claude", "diamonds", "active.yml")
    try:
        with open(active, encoding="utf-8") as handle:
            for line in handle:
                if re.match(r"^\s*autonomous:\s*true\b", line):
                    return True
    except OSError:
        pass
    return False


def extract(tool_input, tool_name):
    """Return (path, content_to_scan)."""
    path = tool_input.get("file_path") or tool_input.get("path")
    if tool_name in ("Write", "mcp__filesystem__write_file"):
        return path, tool_input.get("content", "") or ""
    if tool_name == "Edit":
        return path, tool_input.get("new_string", "") or ""
    if tool_name == "MultiEdit":
        edits = tool_input.get("edits") or []
        return path, "\n".join(str(e.get("new_string", "")) for e in edits)
    if tool_name == "mcp__filesystem__edit_file":
        edits = tool_input.get("edits") or []
        return path, "\n".join(str(e.get("newText", "")) for e in edits)
    return path, (tool_input.get("content", "")
                  or tool_input.get("new_string", "") or "")


def deny(hits):
    reason = (
        "Mycelium autonomous-evidence-guard: BLOCKED -- a declared autonomous "
        "run cannot write " + ", ".join(hits) + " to the canvas. No human or "
        "external source answered in this run, so this evidence would be "
        "fabricated (opp-011 Stage A 2026-06-11: a sub-Fable-5 model fabricated "
        "external_human results and did not know it). Permitted: source_class: "
        "internal_simulated, evidence_type: speculation, validated: false. If a "
        "HUMAN is actually present, this run is NOT autonomous -- unset "
        "MYCELIUM_AUTONOMOUS_RUN and remove `autonomous: true` from "
        "diamonds/active.yml, then retry."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def main():
    project_dir = (sys.argv[1] if len(sys.argv) > 1
                   else os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
    try:
        data = json.loads(sys.stdin.read())
    except (ValueError, OSError):
        sys.exit(0)  # fail-open on unparseable/unreadable input

    if not autonomous_active(project_dir):
        sys.exit(0)  # not autonomous -> allow

    tool_input = data.get("tool_input") or {}
    path, content = extract(tool_input, data.get("tool_name") or "")
    if not path or not content:
        sys.exit(0)
    if not ENFORCED_PATH.search(path):
        sys.exit(0)

    hits = [label for rx, label in FORBIDDEN if rx.search(content)]
    if hits:
        deny(hits)
    sys.exit(0)


if __name__ == "__main__":
    main()
