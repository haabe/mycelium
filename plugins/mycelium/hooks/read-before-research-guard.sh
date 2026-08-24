#!/usr/bin/env bash
# Mycelium read-before-research-guard hook (PreToolUse on web search / fetch)
#
# WARNS when an agent is about to search externally for an entity the canvas
# already records. Full rationale, the two dogfood failures behind it, and what
# it deliberately cannot do are in scripts/read_before_research_guard.py.
#
# WHY A HOOK: the sibling failure happened MINUTES after the prose rule was
# written, in the same turn, by the same agent. "Add a line to the skills" is
# already falsified. Same reason check_reply_owed.py was extracted from prose.
#
# Contract: exit 0 silent = nothing to say; exit 0 + JSON additionalContext =
# warn. NEVER denies — searching for something the canvas mentions is frequently
# correct, and a guard that blocks real work gets disabled. Fails open.

# SELF-LOCATION. CLAUDE_PLUGIN_ROOT is a Claude Code variable: Cursor exports
# CLAUDE_PROJECT_DIR instead and Codex exports neither, so a bare
# "${CLAUDE_PLUGIN_ROOT}/scripts/*.py" resolves to "/scripts/*.py" there and
# silently no-ops. Same defect class this hook exists to catch: an artifact
# asserting a location it cannot know, failing open when wrong.
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  _mycelium_self="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." 2>/dev/null && pwd || true)"
  if [ -n "$_mycelium_self" ] && [ -d "$_mycelium_self/scripts" ]; then
    CLAUDE_PLUGIN_ROOT="$_mycelium_self"
    export CLAUDE_PLUGIN_ROOT
  fi
fi

INPUT=$(cat)

HELPER="${CLAUDE_PLUGIN_ROOT}/scripts/read_before_research_guard.py"
if [ ! -f "$HELPER" ]; then
  HELPER=".claude/scripts/read_before_research_guard.py"
  [ -f "$HELPER" ] || exit 0
fi

printf '%s' "$INPUT" | python3 "$HELPER"
exit 0
