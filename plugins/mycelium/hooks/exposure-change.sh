#!/bin/bash
. "$(dirname "${BASH_SOURCE[0]}")/../scripts/_state_ignore.sh" 2>/dev/null || true  # .claude/state never lacks its ignore file (v0.318.0)
# Mycelium exposure change (PostToolUse on Write|Edit|MultiEdit), v0.279.0
#
# Tells the agent, right after the write, when that write took the work from "may meet its
# audience" to "nothing may meet real people". The prompt-time exposure line (preflight) speaks only
# at a prompt; E2E rung L4-open on 0.278.0 flipped the state inside one turn (the L3 completed as
# handed to a new L4 still in discover) and the builder then called a public launch post "ready to
# post whenever you are". The state logic lives in scripts/scale_locks.py (exposure_change_line).
#
# Advisory: exit 0 always; the message goes to the agent as additionalContext.

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
INPUT=$(cat)
# Cheap exit: only writes to the diamonds file can move the exposure state.
shopt -s nocasematch
case "$INPUT" in
  *diamonds*active.yml*) ;;
  *) exit 0 ;;
esac
shopt -u nocasematch
LOCKS="$(dirname "${BASH_SOURCE[0]}")/../scripts/scale_locks.py"
[ -f "$LOCKS" ] || LOCKS="${CLAUDE_PLUGIN_ROOT:-}/scripts/scale_locks.py"
python3 "$LOCKS" --project-dir "$PROJECT_DIR" --exposure-change
exit 0
