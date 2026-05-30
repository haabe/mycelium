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

# Fast path: no state file → no active execution → allow everything
[ ! -f "$STATE_FILE" ] && exit 0

# Helper resolution — prefer plugin path (post-0.20.x), fall back to legacy.
# Mirrors framework-guard.sh: plugin installs removed the legacy helper from git,
# so the hardcoded legacy path fell through to the fail-closed deny below for
# anyone running as a plugin — a hard deadlock during active execution.
HELPER=""
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/scripts/scope_check.py" ]; then
  HELPER="${CLAUDE_PLUGIN_ROOT}/scripts/scope_check.py"
elif [ -f "$PROJECT_DIR/.claude/scripts/scope_check.py" ]; then
  HELPER="$PROJECT_DIR/.claude/scripts/scope_check.py"
fi

# Read input JSON from stdin
INPUT=$(cat)

# Delegate to Python stdlib helper (json module, fnmatch module — all stdlib)
# Helper returns either empty (allow) or a deny JSON on stdout
if [ -f "$HELPER" ]; then
  printf '%s' "$INPUT" | python3 "$HELPER" "$STATE_FILE" "$PROJECT_DIR"
  exit $?
fi

# Helper missing in BOTH plugin and legacy paths → fail-closed.
python3 -c "
import json, os
plugin_root = os.environ.get('CLAUDE_PLUGIN_ROOT', '<CLAUDE_PLUGIN_ROOT not set>')
print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': f'Mycelium scope-gate: scope_check.py not found at {plugin_root}/scripts/scope_check.py NOR at .claude/scripts/scope_check.py. Reinstall the plugin (/plugin update mycelium) OR delete .claude/state/active-execution.json to disable scope enforcement.'
    }
}))
"
exit 0
