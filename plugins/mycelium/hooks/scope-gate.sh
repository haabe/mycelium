#!/usr/bin/env bash
. "$(dirname "${BASH_SOURCE[0]}")/../scripts/_hook_prelude.sh" 2>/dev/null || true  # no-op outside a Mycelium project; state ignore file (v0.318.0)
# Mycelium scope hold (PreToolUse on writes, shell commands and the filesystem MCP writes)
#
# Keeps the agent's writes inside the folders a delivery cycle named. Addresses the BDSK
# comparison feedback (Daniel Bentes) about computational scope enforcement.
#
# Since 0.324.0 the folders are read from the delivery cycle's own record: an L4 in
# .claude/diamonds/active.yml carries `in_scope_paths`. The hold is on for a cycle that has
# committed to build and has not closed. A write outside the folders is put to the person; a
# write that names or changes the folders is put to the person too. scripts/scope_check.py says
# why it moved and what each answer is.
#
# Until 0.324.0 the folders were read from .claude/state/active-execution.json, which nothing
# Mycelium ships ever wrote, so this hook did nothing in a plugin install. That file is no longer
# read; while one exists, product writes are refused and the refusal says what to do.
#
# - The helper needs PyYAML to read the record. Without it the helper fails and the write is
#   refused with the reason (fail-closed), as for a record that does not parse.
# - No record, or a record that names no folder: the hook leaves before starting Python.
#
# Exit/output convention (modern Claude Code):
# - exit 0 silent → allow
# - exit 0 + JSON hookSpecificOutput.permissionDecision="ask" → the person is asked
# - exit 0 + JSON hookSpecificOutput.permissionDecision="deny" → refused, with the reason

set -euo pipefail
# SELF-LOCATION, added v0.88.0. This script lives at <plugin_root>/hooks/, so
# its own path resolves the plugin root without anyone setting anything. Needed
# because CLAUDE_PLUGIN_ROOT is a Claude Code variable: Cursor exports
# CLAUDE_PROJECT_DIR instead and Codex exports neither, so every
# "${CLAUDE_PLUGIN_ROOT}/scripts/*.py" lookup below resolved to "/scripts/*.py"
# there, missed, and fell through to a silent no-op. Same class as the
# hardcoded cache path removed from the runtime manifests in this release: an
# artifact asserting a location it cannot know, failing open when wrong.
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  _mycelium_self="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." 2>/dev/null && pwd || true)"
  if [ -n "$_mycelium_self" ] && [ -d "$_mycelium_self/scripts" ]; then
    CLAUDE_PLUGIN_ROOT="$_mycelium_self"
    export CLAUDE_PLUGIN_ROOT
  fi
fi


PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
STATE_FILE="$PROJECT_DIR/.claude/state/active-execution.json"

# Fast path (v0.324.0). The folders a delivery cycle may write to are read from the cycle's own
# record, .claude/diamonds/active.yml (`in_scope_paths` on an L4). Leave before starting Python
# unless one of these is true:
#   - an old state file exists (it is no longer read, and product writes are refused until it is
#     moved and deleted: scope_check.py says how);
#   - this call names the field or a commitment to build, so it may be a write to the record that
#     says where a cycle may write;
#   - the record names at least one folder. `in_scope_paths: []` alone is "no hold", and costs
#     nothing here.
# Until 0.324.0 the fast path was "no state file", and nothing Mycelium ships wrote that file, so
# in a plugin install this hook always left here.
RECORD="$PROJECT_DIR/.claude/diamonds/active.yml"
INPUT=$(cat)
if [ ! -f "$STATE_FILE" ]; then
  case "$INPUT" in
    *in_scope_paths*|*commit_to_build*) ;;
    *)
      # Lines where the field is a KEY (prose that mentions it inside a note does not count),
      # minus the ones whose value is the empty list. Anything left may name a folder, in
      # whatever way YAML allows a list to be written, and Python reads it properly.
      SQ="'"
      KEY="^[[:space:]-]*[\"${SQ}]?in_scope_paths[\"${SQ}]?[[:space:]]*:"
      EMPTY=":[[:space:]]*\[[[:space:]]*\][[:space:]]*(#.*)?\$"
      grep -E "$KEY" "$RECORD" 2>/dev/null | grep -Evq "$EMPTY" || exit 0
      ;;
  esac
fi

# Helper resolution — prefer plugin path (post-0.20.x), fall back to legacy.
# Mirrors framework-guard.sh: plugin installs removed the legacy helper from git,
# so the hardcoded legacy path fell through to the fail-closed deny below for
# anyone running as a plugin — a hard deadlock during active execution.
HELPER=""
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/scripts/scope_check.py" ]; then
  HELPER="${CLAUDE_PLUGIN_ROOT}/scripts/scope_check.py"
elif [ -f "$_MYCELIUM_ROOT/scripts/scope_check.py" ]; then
  HELPER="$_MYCELIUM_ROOT/scripts/scope_check.py"
fi

# (The input was read above, before the fast path.)
# The verdict below is captured so a refusal reaches the denial ledger (0.316.0), then passed
# through unchanged: same stdout, same exit status.
# shellcheck source=/dev/null
. "$(dirname "${BASH_SOURCE[0]}")/../scripts/_hook_fire_log.sh" 2>/dev/null || {
  mycelium_note_refusal() { :; }; mycelium_record_denial() { :; }; }

# Delegate to Python stdlib helper (json module, fnmatch module — all stdlib)
# Helper returns either empty (allow) or a deny JSON on stdout
# A here-string, not a pipe (0.322.1). The helper answers a corrupt state file before it reads
# the tool call. Under `set -eo pipefail` a `printf | python3` pipe then died on any call larger
# than the pipe holds (printf: Broken pipe), and the hook left with printf's status before it
# passed the helper's deny on: a hook error that let the write through. With
# `"onFailure": "block"` in hooks.json that status would refuse the call and give no reason.
if [ -f "$HELPER" ]; then
  OUT=$(python3 "$HELPER" "$STATE_FILE" "$PROJECT_DIR" <<<"$INPUT"); RC=$?
  mycelium_note_refusal "$OUT" "$RC"
  [ -n "$OUT" ] && printf '%s\n' "$OUT"
  exit $RC
fi

# Helper missing in BOTH plugin and legacy paths → fail-closed.
mycelium_record_denial 2>/dev/null || true
python3 -c "
import json, os
plugin_root = os.environ.get('CLAUDE_PLUGIN_ROOT', '<CLAUDE_PLUGIN_ROOT not set>')
print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': f'Mycelium scope-gate: scope_check.py not found at {plugin_root}/scripts/scope_check.py NOR at .claude/scripts/scope_check.py. Reinstall the plugin (/plugin update mycelium). Until then this write is refused, because without that script Mycelium cannot tell whether a delivery cycle holds it.'
    }
}))
"
exit 0
