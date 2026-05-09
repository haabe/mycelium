#!/usr/bin/env bash
# Mycelium framework-guard hook (PreToolUse on Write|Edit|MultiEdit)
#
# Blocks edits to FRAMEWORK-classified files in projects that are dogfood
# instances of an upstream Mycelium framework repo. Activated by the
# presence of .claude/state/upstream.json declaring the upstream repo.
#
# WHY THIS EXISTS:
# Recurring failure (≥3 incidents documented in mycelium-roadmap
# corrections.md as of 2026-05-03): agent edits framework files directly
# in the dogfood project instead of porting upstream first via the
# two-repo discipline (mycelium → push → upgrade.sh in dogfood). Recovery
# from the wrong-repo edits is multi-step (stash → patch → extract →
# upstream commit → upgrade), wasting conversation budget on a failure
# that's preventable with one upfront classification check at edit time.
# Single-loop behavioral discipline has not held; this hook is the
# double-loop harness fix per Lopopolo ("every interaction is a failure
# of the harness to provide enough context").
#
# DESIGN:
# - Fast no-op path when .claude/state/upstream.json is absent (most
#   Mycelium-using projects don't have a separate upstream — they ARE
#   the project).
# - Activates only when upstream.json exists and active=true.
# - Classifies the target file against .claude/manifest.yml framework lists.
# - If the file is framework: deny with a clear message naming the upstream
#   repo and the bypass instruction.
# - Helper script does the YAML parsing in Python stdlib (no PyYAML).
# - Fail-open on input parse errors; fail-closed on missing helper.
#
# Exit/output convention (modern Claude Code):
# - exit 0 silent → allow
# - exit 0 + JSON hookSpecificOutput.permissionDecision="deny" → block with UI message

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
STATE_FILE="$PROJECT_DIR/.claude/state/upstream.json"

# Fast path: no state file → not a dogfood instance → allow everything
[ ! -f "$STATE_FILE" ] && exit 0

# Helper resolution — prefer plugin path (post-0.20.x), fall back to legacy.
# F6 fix (2026-05-09 team-topologies dogfood): plugin migration removed the
# legacy helper from git but the hook still hardcoded the legacy path,
# producing a hard deadlock for anyone pulling main without a local copy.
HELPER=""
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/scripts/framework_guard.py" ]; then
  HELPER="${CLAUDE_PLUGIN_ROOT}/scripts/framework_guard.py"
elif [ -f "$PROJECT_DIR/.claude/scripts/framework_guard.py" ]; then
  HELPER="$PROJECT_DIR/.claude/scripts/framework_guard.py"
fi

# Read input JSON from stdin
INPUT=$(cat)

# Delegate to Python stdlib helper
if [ -n "$HELPER" ]; then
  printf '%s' "$INPUT" | python3 "$HELPER" "$STATE_FILE" "$PROJECT_DIR"
  exit $?
fi

# Helper missing in BOTH plugin and legacy paths → fail-closed.
# Updated bypass instruction names both paths so the user can diagnose.
python3 -c "
import json, os
plugin_root = os.environ.get('CLAUDE_PLUGIN_ROOT', '<CLAUDE_PLUGIN_ROOT not set>')
print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': f'Mycelium framework-guard: framework_guard.py not found at {plugin_root}/scripts/framework_guard.py NOR at .claude/scripts/framework_guard.py. Reinstall the plugin (/plugin update mycelium) OR delete .claude/state/upstream.json to disable framework-edit enforcement.'
    }
}))
"
exit 0
