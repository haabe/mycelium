#!/bin/bash
# Mycelium shell-state guard (v0.253.2). PreToolUse Bash: refuse a command that visibly writes
# .claude/diamonds/active.yml (the scale-lock gate only judges the Edit and Write tools), and
# snapshot that file. PostToolUse Bash: schema-check any canvas or diamonds file the command
# changed, and judge a changed diamonds file against the snapshot. Logic and the full reasoning:
# scripts/bash_state_guard.py. E2E run 24 wrote the privacy canvas through a shell command and the
# schema check never saw it.
#
# FAILS OPEN ON A CRASH, AND SAYS SO: this runs before EVERY shell command, so failing closed on a
# broken script would lock the agent out of the shell. A crash prints a line naming the guard.

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
MODE="${1:-pre}"
INPUT=$(cat)
_log() {
  # shellcheck source=/dev/null
  . "$PLUGIN_ROOT/scripts/_hook_fire_log.sh" 2>/dev/null || true
  mycelium_log_fire ".claude/state/bash-state-guard-fires.jsonl" "$1" 2>/dev/null || true
}

if [ "$MODE" = "post" ]; then
  # The verdict, if any, is JSON on stdout; it goes to the agent as is.
  VERDICT=$(printf '%s' "$INPUT" | python3 "$PLUGIN_ROOT/scripts/bash_state_guard.py" post 2>/dev/null)
  if [ -n "$VERDICT" ]; then
    printf '%s\n' "$VERDICT"
    _log fired
  fi
  exit 0
fi

ERR=$(printf '%s' "$INPUT" | python3 "$PLUGIN_ROOT/scripts/bash_state_guard.py" pre 2>&1 >/dev/null)
RC=$?
if [ "$RC" -eq 2 ]; then
  printf '%s\n' "$ERR" >&2
  _log blocked
  exit 2
fi
if [ "$RC" -ne 0 ]; then
  echo "Mycelium shell-state guard could not run (exit $RC); this command was not checked." >&2
fi
exit 0
