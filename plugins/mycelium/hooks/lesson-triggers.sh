#!/usr/bin/env bash
. "$(dirname "${BASH_SOURCE[0]}")/../scripts/_hook_prelude.sh" 2>/dev/null || true  # no-op outside a Mycelium project; state ignore file (v0.318.0)
# Mycelium lesson-triggers hook (PreToolUse on Bash, Write/Edit/MultiEdit, WebFetch/WebSearch)
#
# Shows a lesson already on record (its rule line, from .claude/memory/lesson-triggers.yml)
# at the tool call it is about, and refuses the call where the entry says the match is the
# mistake itself. OFF unless MYCELIUM_LESSON_TRIGGERS=on: the person switches it on, the
# agent never does. Matching, privacy and the reasons are in scripts/lesson_triggers.py.
#
# WHY A HOOK: lessons written to a file are read when the agent chooses to read them, and
# on the dogfood project 86 of 96 corrections in a month repeated one already written down.
# This puts the lesson in front of the agent at the call, without it choosing.
#
# Contract: exit 0 silent = nothing to say; exit 0 + JSON additionalContext = the rule line
# shown, the call runs; exit 0 + JSON permissionDecision "deny" = refused with the rule line
# as the reason. FAILS OPEN ON A CRASH: it runs before every matching call, so a broken
# script must not stop the agent's work; listed `continue` in pretooluse-on-failure.txt.

if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  _mycelium_self="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." 2>/dev/null && pwd || true)"
  if [ -n "$_mycelium_self" ] && [ -d "$_mycelium_self/scripts" ]; then
    CLAUDE_PLUGIN_ROOT="$_mycelium_self"
    export CLAUDE_PLUGIN_ROOT
  fi
fi

# Off unless switched on: no work at all, before even reading the payload.
case "${MYCELIUM_LESSON_TRIGGERS:-}" in on|ON|On) ;; *) exit 0 ;; esac

INPUT=$(cat)

HELPER="${CLAUDE_PLUGIN_ROOT}/scripts/lesson_triggers.py"
if [ ! -f "$HELPER" ]; then
  HELPER="$_MYCELIUM_ROOT/scripts/lesson_triggers.py"  # beside this hook, never the project's folder
  [ -f "$HELPER" ] || exit 0
fi

# FIRE RECORD: logged only when the helper produced output. A refusal goes in the denial
# ledger, so gate-override-check can say when a refused call ran anyway.
. "${CLAUDE_PLUGIN_ROOT:-$(dirname "${BASH_SOURCE[0]}")/..}/scripts/_hook_fire_log.sh" 2>/dev/null || {
  mycelium_log_fire() { :; }; mycelium_note_refusal() { :; }; }
_myc_out=$(printf '%s' "$INPUT" | python3 "$HELPER")
mycelium_note_refusal "$_myc_out" 0 2>/dev/null || true
if [ -n "$_myc_out" ]; then
  mycelium_log_fire ".claude/state/lesson-triggers-fires.jsonl" "fired" 2>/dev/null || true
  printf '%s\n' "$_myc_out"
fi
exit 0
