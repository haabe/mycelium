#!/bin/bash
. "$(dirname "${BASH_SOURCE[0]}")/../scripts/_hook_prelude.sh" 2>/dev/null || true  # no-op outside a Mycelium project; state ignore file (v0.318.0)
# Mycelium guard-state gate (PreToolUse on Write|Edit|MultiEdit|NotebookEdit, Bash and the
# filesystem MCP writes), v0.281.0
#
# The files that switch a blocking hook off (the ack files, upstream.json, manifest.yml,
# active-execution.json; `_hook_input.GUARD_STATE_REL`) are the user's to write. A write to one asks
# the human in a permission mode where someone is asked, and is refused where nobody would be
# (permissions bypassed, or an automated mode). The three guards that did this before were each
# conditional, so in an ordinary project nothing guarded them; E2E relay on 0.280.0 had the agent
# write its own scale-lock override under bypassed permissions.
#
# Exit 0 always; the decision (ask or deny) is the PreToolUse JSON the helper prints.

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
INPUT=$(cat)
# The verdict below is captured so a refusal reaches the denial ledger (0.316.0), then passed
# through unchanged: same stdout, same exit status.
# shellcheck source=/dev/null
. "$(dirname "${BASH_SOURCE[0]}")/../scripts/_hook_fire_log.sh" 2>/dev/null || {
  mycelium_note_refusal() { :; }; mycelium_record_denial() { :; }; }
# Cheap exit: only a call that names a guard-state file needs python.
case "$INPUT" in
  *-ack*|*upstream.json*|*manifest.yml*|*active-execution.json*) ;;
  *) exit 0 ;;
esac
HELPER="$(dirname "${BASH_SOURCE[0]}")/../scripts/_hook_input.py"
[ -f "$HELPER" ] || HELPER="${CLAUDE_PLUGIN_ROOT:-}/scripts/_hook_input.py"
OUT=$(printf '%s' "$INPUT" | python3 "$HELPER" --project-dir "$PROJECT_DIR" --guard-state guard-state-gate)
mycelium_note_refusal "$OUT" 0
[ -n "$OUT" ] && printf '%s\n' "$OUT"
exit 0
