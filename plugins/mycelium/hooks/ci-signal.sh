#!/usr/bin/env bash
# Mycelium ci-signal hook (Stop, and SessionStart with --session-start)
#
# Reports ONCE when the workflow for the currently checked-out commit has
# failed. Full rationale, the no-push-tracking design, and the fail-open
# contract are in scripts/ci_signal.py.
#
# WHY A HOOK: on 2026-08-03/04 the dogfood workflow was red for thirteen
# consecutive pushes. Every run reported failure; nothing carried the result
# back into the session that caused it, and the harness had five hook points
# none of which looked outward. A pull request forces you to look; `main` does
# not ask.
#
# Contract: exit 0 silent = nothing to say; exit 0 + JSON additionalContext =
# report. NEVER blocks. Fails open on missing gh, auth, network or workflows —
# a session that breaks over a build-status lookup is worse than the gap.

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

HELPER="${CLAUDE_PLUGIN_ROOT}/scripts/ci_signal.py"
if [ ! -f "$HELPER" ]; then
  HELPER=".claude/scripts/ci_signal.py"
  [ -f "$HELPER" ] || exit 0
fi

# FIRE RECORD, added v0.236.0. Logged ONLY when the helper actually produced output.
# Logging on invocation instead would record every matching tool call as a fire, and a
# mechanism that "fires" on every call cannot be told from one that fires on none -- which
# is the opposite of what check_retirement_candidates.py asks this record. Capture, then
# decide, then emit unchanged. The path is a LITERAL because that regex reads the source.
_myc_out=$(printf '%s' "$INPUT" | python3 "$HELPER" "$@")
if [ -n "$_myc_out" ]; then
  . "${CLAUDE_PLUGIN_ROOT:-$(dirname "${BASH_SOURCE[0]}")/..}/scripts/_hook_fire_log.sh" 2>/dev/null || true
  mycelium_log_fire ".claude/state/ci-signal-fires.jsonl" "fired" 2>/dev/null || true
  printf '%s\n' "$_myc_out"
fi
exit 0
