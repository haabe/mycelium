#!/usr/bin/env bash
# Mycelium reflexion-gate shim for OpenAI Codex CLI.
#
# Codex has no native PostToolUseFailure event (verified against
# developers.openai.com/codex/hooks as of 2026-05-26 — events are
# SessionStart, SubagentStart, PreToolUse, PermissionRequest, PostToolUse,
# PreCompact, PostCompact, UserPromptSubmit, SubagentStop, Stop). This shim
# wires reflexion-gate.sh into Codex's PostToolUse and short-circuits when
# the captured tool_response shows no error.
#
# Forwards stdin verbatim to reflexion-gate.sh on failure; exits 0 on success
# without invoking the gate.

set -euo pipefail

INPUT=$(cat)

# Detect failure: Codex stdin payload includes `tool_response` for PostToolUse;
# on error, exit_code != 0, OR `error` is set, OR `success` is false.
# Field shape varies by tool — best-effort parse with python3 fallback to 0.
IS_FAILURE=$(printf '%s' "$INPUT" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    r = d.get("tool_response", {}) or {}
    if isinstance(r, dict):
        if r.get("success") is False: print("1"); sys.exit(0)
        if r.get("error"): print("1"); sys.exit(0)
        if r.get("exit_code") not in (None, 0): print("1"); sys.exit(0)
        if r.get("is_error"): print("1"); sys.exit(0)
    print("0")
except Exception:
    print("0")
' 2>/dev/null || echo "0")

if [ "$IS_FAILURE" != "1" ]; then
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
printf '%s' "$INPUT" | bash "$SCRIPT_DIR/reflexion-gate.sh"
