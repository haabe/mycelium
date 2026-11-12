#!/bin/bash
. "$(dirname "${BASH_SOURCE[0]}")/../scripts/_hook_prelude.sh" 2>/dev/null || true  # no-op outside a Mycelium project; state ignore file (v0.318.0)
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
# FIRE RECORD: a row only when it speaks. Until this it left nothing behind but the one word in
# exposure-last, so whether the warning ever fired in a project could not be read back, and
# check_retirement_candidates.py listed it as "writes no record" (DL-1375, 2026-10-02; again
# 2026-10-11). It speaks on one change only, so the detail is that change. Capture, then decide,
# then emit unchanged; the path is a LITERAL because that check reads it from this source.
_myc_out=$(python3 "$LOCKS" --project-dir "$PROJECT_DIR" --exposure-change)
if [ -n "$_myc_out" ]; then
  . "$(dirname "$LOCKS")/_hook_fire_log.sh" 2>/dev/null || true  # beside the helper that spoke
  mycelium_log_fire ".claude/state/exposure-change-fires.jsonl" "fired" "ready->not-ready" 2>/dev/null || true
  printf '%s\n' "$_myc_out"
fi
exit 0
