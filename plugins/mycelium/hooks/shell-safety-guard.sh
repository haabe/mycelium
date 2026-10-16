#!/usr/bin/env bash
. "$(dirname "${BASH_SOURCE[0]}")/../scripts/_hook_prelude.sh" 2>/dev/null || true  # no-op outside a Mycelium project; state ignore file (v0.318.0)
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
# warn; exit 0 + JSON permissionDecision "deny" = refused, for two shapes only
# (v0.326.0: a multi-file edit that can half-apply, and a pipeline gating a commit
# or push). FAILS OPEN ON A CRASH, AND SAYS SO HERE: a guard that breaks the Bash
# tool is worse than the traps it catches, and this one runs before every shell
# command; listed `continue` in pretooluse-on-failure.txt.

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

INPUT=$(cat)

HELPER="${CLAUDE_PLUGIN_ROOT}/scripts/shell_safety_guard.py"
if [ ! -f "$HELPER" ]; then
  # Legacy layout fallback, then silent no-op. Fail OPEN: this hook runs before every
  # shell command, so a missing helper must not block or nag.
  HELPER="$_MYCELIUM_ROOT/scripts/shell_safety_guard.py"  # beside this hook, never the project's folder (v0.322.3)
  [ -f "$HELPER" ] || exit 0
fi

# FIRE RECORD, added v0.236.0. Logged ONLY when the helper actually produced output.
# Logging on invocation instead would record every matching tool call as a fire, and a
# mechanism that "fires" on every call cannot be told from one that fires on none -- which
# is the opposite of what check_retirement_candidates.py asks this record. Capture, then
# decide, then emit unchanged. The path is a LITERAL because that regex reads the source.
# v0.326.0: rules 5 and 6 refuse. A refusal goes in the denial ledger, so gate-override-check
# can say when a refused command ran anyway (another extension approved it).
. "${CLAUDE_PLUGIN_ROOT:-$(dirname "${BASH_SOURCE[0]}")/..}/scripts/_hook_fire_log.sh" 2>/dev/null || {
  mycelium_log_fire() { :; }; mycelium_note_refusal() { :; }; }
_myc_out=$(printf '%s' "$INPUT" | python3 "$HELPER")
mycelium_note_refusal "$_myc_out" 0 2>/dev/null || true
if [ -n "$_myc_out" ]; then
  mycelium_log_fire ".claude/state/shell-safety-guard-fires.jsonl" "fired" 2>/dev/null || true
  printf '%s\n' "$_myc_out"
fi
exit 0
