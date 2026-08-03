#!/usr/bin/env bash
# Mycelium shell-safety-guard hook (PreToolUse on Bash)
#
# Warns on shell constructs whose exit status or quoting silently misleads:
# `$?` after a pipeline, backticks, and grep gating an && chain. Full rationale,
# the documented contract behind each check, and what it deliberately does NOT
# cover are in scripts/shell_safety_guard.py.
#
# WHY A HOOK: three of these traps have their own memory files in the dogfood
# project, written after earlier incidents, and all three were walked into anyway
# in one session — eight times, once producing a wrong answer to the operator.
# A note is read at session start and decays; this fires on the command.
#
# Contract: exit 0 silent = nothing to say; exit 0 + JSON additionalContext =
# warn. NEVER denies. Fails open — a guard that breaks the Bash tool is worse
# than the traps it catches.

INPUT=$(cat)

HELPER="${CLAUDE_PLUGIN_ROOT}/scripts/shell_safety_guard.py"
if [ ! -f "$HELPER" ]; then
  # Legacy layout fallback, then silent no-op. Fail OPEN: unlike framework-guard
  # this hook only advises, so a missing helper must not block or nag.
  HELPER=".claude/scripts/shell_safety_guard.py"
  [ -f "$HELPER" ] || exit 0
fi

printf '%s' "$INPUT" | python3 "$HELPER"
exit 0
