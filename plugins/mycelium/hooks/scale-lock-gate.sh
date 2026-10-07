#!/bin/bash
# Mycelium scale-lock gate (PreToolUse on Write|Edit|MultiEdit and the filesystem MCP writes)
#
# Blocks a write to .claude/diamonds/active.yml that ADDS a diamond whose parent has not yet
# established what the child builds on (v0.245.0). The locks themselves live in one place,
# scripts/scale_locks.py, which the delivery gate and /mycelium:canvas-health read too:
#   L1 on a purpose, L2 on a strategy (an L1 diamond, a North Star, the landscape) and a desired
#   outcome, L3 on its L2's target opportunity with evidence (v0.301.0), L4 on an L3 at medium
#   confidence, L5 on launch data from a shipped L4. Every diamond is born in discover (v0.247.0).
#
# Provenance: the founder's model, restated 2026-09-24, "all scales have a natural lock per se";
# three releases (0.217.0, 0.242.5, 0.243.0) had opened every door "whether or not the parent has
# progressed", so every scale could open at once and nothing stopped building the wrong thing.
#
# Scope is deliberately narrow:
#   - Only writes to .claude/diamonds/active.yml, and only diamonds the write OPENS: a new id, an
#     id rescaled, or one moved back into the active list. A diamond already open at its scale is
#     never re-judged here (its phase is its own speed); `scale_locks.py --check` reports it, and
#     the delivery gate still asks whether its chain holds before it carries new code.
#   - A Bash write to active.yml is not parsed here. It cannot unlock code: the delivery gate
#     re-reads the whole chain before any new source file.
#   - Escape hatch: a line `<id> <scale> <YYYY-MM-DD> <the user's words>` in
#     .claude/state/scale-lock-ack, which is guarded state, so only the user can write it.
#
# Exit 0 = allow, Exit 2 = block (stderr is shown to the agent).

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
INPUT=$(cat)
# Cheap exit, case-insensitive: every other write never starts python. `ACTIVE.yml`,
# `Diamonds/active.yml` and `diamonds/./active.yml` are the same file on a case-insensitive volume,
# and a case-sensitive literal let all three through (adversarial review, 2026-09-24).
shopt -s nocasematch
case "$INPUT" in
  *diamonds*active.yml*) ;;
  *) exit 0 ;;
esac
shopt -u nocasematch
LOCKS="$(dirname "${BASH_SOURCE[0]}")/../scripts/scale_locks.py"
[ -f "$LOCKS" ] || LOCKS="${CLAUDE_PLUGIN_ROOT:-}/scripts/scale_locks.py"
# shellcheck source=../scripts/_python.sh
. "$(dirname "$LOCKS")/_python.sh"  # mycelium_python (v0.292.0)
# stdout is captured (v0.315.0): on an allowed write it may carry the launch-approval JSON and is
# passed through unchanged; on a refusal it carries one `MYCELIUM_BLOCK_KINDS <kinds>` line, which
# goes to the block log so a refusal for a missing upstream record (entry_lock) can be told from one
# for a diamond's own decision gates. A here-string, not a pipe, so $? is the checker's own status.
OUT=$("$(mycelium_python)" "$LOCKS" --project-dir "$PROJECT_DIR" --hook <<<"$INPUT")
rc=$?
# 0 = allowed, 3 = PyYAML missing (hooks/preflight.sh says the locks are unchecked, every prompt).
# Anything else is a refusal, including a crash: its traceback is on stderr, and a lock checker that
# fell over must not read as a lock that held.
if [ "$rc" -ne 0 ] && [ "$rc" -ne 3 ]; then
  KINDS=$(printf '%s\n' "$OUT" | sed -n 's/^MYCELIUM_BLOCK_KINDS //p' | head -n 1)
  . "${CLAUDE_PLUGIN_ROOT:-$(dirname "${BASH_SOURCE[0]}")/..}/scripts/_hook_fire_log.sh" 2>/dev/null || true
  mycelium_log_fire ".claude/state/scale-lock-fires.jsonl" "blocked" "${KINDS:-crashed}" 2>/dev/null || true
  exit 2
fi
# An allowed write can still carry a JSON deny: the launch approval in a runtime or permission mode
# that cannot ask a person (scale_locks.py _launch_approval). It goes to the denial ledger (0.316.0).
case "$OUT" in
  *permissionDecision*)
    # shellcheck source=/dev/null
    . "${CLAUDE_PLUGIN_ROOT:-$(dirname "${BASH_SOURCE[0]}")/..}/scripts/_hook_fire_log.sh" 2>/dev/null \
      && mycelium_note_refusal "$OUT" 0 ;;
esac
[ -n "$OUT" ] && printf '%s\n' "$OUT"
exit 0
