#!/usr/bin/env bash
# Mycelium absence-claim-guard hook (PreToolUse on Write|Edit|MultiEdit)
#
# Warns when an assertive absence — "no need covers X", "nothing checks Y",
# "was never routed", "nowhere to go" — is written into a durable evidence
# surface (.claude/canvas, memory, harness, evals, diamonds) without naming the
# search that grounds it. Full rationale, the calibration behind each pattern,
# and what it deliberately cannot do are in scripts/absence_claim_guard.py.
#
# WHY A HOOK: on 2026-08-04 the dogfood project made five claims of this shape in
# one session and pushed two of them to the canvas before catching them. An
# auto-memory rule against exactly this already existed and did not fire, because
# notes are read at session start and decay. This fires at the write.
#
# Contract: exit 0 silent = nothing to say; exit 0 + JSON additionalContext =
# warn. NEVER denies — absence findings are frequently correct and valuable, and
# a guard that blocks real work gets disabled. Fails open.

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

HELPER="${CLAUDE_PLUGIN_ROOT}/scripts/absence_claim_guard.py"
if [ ! -f "$HELPER" ]; then
  # Legacy layout fallback, then silent no-op. Fail OPEN: this hook only
  # advises, so a missing helper must not block or nag.
  HELPER=".claude/scripts/absence_claim_guard.py"
  [ -f "$HELPER" ] || exit 0
fi

printf '%s' "$INPUT" | python3 "$HELPER"
exit 0
