#!/usr/bin/env bash
# Mycelium scope enforcement hook (PreToolUse on Edit|Write|MultiEdit)
#
# When an L4 Delivery diamond has an active execution with declared in_scope_paths,
# block edits to files outside scope. Addresses the BDSK comparison feedback
# (Daniel Bentes) about computational scope enforcement.
#
# Design principles:
# - Runtime state lives in .claude/state/active-execution.json (JSON, not YAML)
# - Hook uses Python stdlib only (no PyYAML, no Ruby, no jq)
# - Zero runtime dependencies beyond Python 3.x (already a Mycelium baseline)
# - Fail-closed on state corruption; fail-open when state file is absent
#
# Exit/output convention (modern Claude Code):
# - exit 0 silent → allow
# - exit 0 + JSON hookSpecificOutput.permissionDecision="deny" → block with UI message
# - exit 2 → reserved for fail-closed on state corruption (rare)

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
STATE_FILE="$PROJECT_DIR/.claude/state/active-execution.json"
HELPER="$PROJECT_DIR/.claude/scripts/scope_check.py"

# Fast path: no state file → no active execution → allow everything
[ ! -f "$STATE_FILE" ] && exit 0

# Read input JSON from stdin
INPUT=$(cat)

# Delegate to Python stdlib helper (json module, fnmatch module — all stdlib)
# Helper returns either empty (allow) or a deny JSON on stdout
if [ -f "$HELPER" ]; then
  printf '%s' "$INPUT" | python3 "$HELPER" "$STATE_FILE" "$PROJECT_DIR"
  exit $?
fi

# If helper script is missing, fail-closed with a clear error
python3 -c "
import json
print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': 'Mycelium scope-gate: .claude/scripts/scope_check.py is missing. Restore the file or delete .claude/state/active-execution.json to disable scope enforcement.'
    }
}))
"
exit 0
