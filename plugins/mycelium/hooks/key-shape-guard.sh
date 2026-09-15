#!/usr/bin/env bash
# Mycelium key-shape-guard hook (PreToolUse on Write|Edit|MultiEdit)
#
# Warns when a write into .claude/canvas or .claude/diamonds introduces a key
# whose NAME carries a date or an entity id (`promoted_2026_09_02`,
# `ht_010_status`), or a second spelling of a stem the target file already
# holds (`reply-sent` beside `reply_sent`). The write-time half of the
# near-duplicate-keys row; `check_key_shape.py --stems` is the sweep half.
# Rationale, the two regexes it shares with the sweep, and what it cannot see
# are in scripts/key_shape_guard.py.
#
# Contract: exit 0 silent = nothing to say; exit 0 + JSON additionalContext =
# warn. NEVER denies. Fails open: a missing helper is a silent no-op.

if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  _mycelium_self="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." 2>/dev/null && pwd || true)"
  if [ -n "$_mycelium_self" ] && [ -d "$_mycelium_self/scripts" ]; then
    CLAUDE_PLUGIN_ROOT="$_mycelium_self"
    export CLAUDE_PLUGIN_ROOT
  fi
fi

INPUT=$(cat)

HELPER="${CLAUDE_PLUGIN_ROOT}/scripts/key_shape_guard.py"
[ -f "$HELPER" ] || exit 0

printf '%s' "$INPUT" | python3 "$HELPER"
exit 0
