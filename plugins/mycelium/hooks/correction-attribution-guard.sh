#!/usr/bin/env bash
# Mycelium correction-attribution-guard hook (PreToolUse on Write|Edit|MultiEdit|Bash)
#
# Warns when a NEW entry is written to `.claude/memory/corrections.md` without
# naming who caught the mistake. Full rationale, the measurement that motivated
# it, and what it deliberately cannot do are in
# scripts/correction_attribution_guard.py.
#
# WHY A HOOK: the rule has been HARD in engine/agent-operating-contract.md since
# 2026-08-03 and compliance since then is 15 of 91 entries. It is obeyed on the
# days the agent is working on the attribution machinery and ignored on every
# other day — a timing failure, not a comprehension one. The contract is read at
# session start; the write happens hundreds of turns later. This fires at the
# write.
#
# WHY IT ALSO MATCHES Bash: corrections.md is appended with a heredoc, not with
# Write. A guard registered on Write|Edit|MultiEdit alone would have shipped
# green against the exact corpus that motivated it.
#
# Contract: exit 0 silent = nothing to say; exit 0 + JSON additionalContext =
# warn. NEVER denies. Fails open.

if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  _mycelium_self="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." 2>/dev/null && pwd || true)"
  if [ -n "$_mycelium_self" ] && [ -d "$_mycelium_self/scripts" ]; then
    CLAUDE_PLUGIN_ROOT="$_mycelium_self"
    export CLAUDE_PLUGIN_ROOT
  fi
fi

INPUT=$(cat)

HELPER="${CLAUDE_PLUGIN_ROOT}/scripts/correction_attribution_guard.py"
if [ ! -f "$HELPER" ]; then
  HELPER=".claude/scripts/correction_attribution_guard.py"
  [ -f "$HELPER" ] || exit 0
fi

printf '%s' "$INPUT" | python3 "$HELPER"
exit 0
