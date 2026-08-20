#!/usr/bin/env bash
# Mycelium discovery-trigger guard (UserPromptSubmit)
#
# Advises when the AUTHOR states something whose truth depends on other people's
# wants or behaviour — "users want X", "people won't bother", "they'd pay for
# it". Full rationale, the calibration behind each pattern, the suppressors, and
# what it deliberately cannot do are in scripts/discovery_trigger_guard.py.
#
# WHY A HOOK, AND WHY THIS EVENT: every other route into discovery in this
# framework is INVOKED — /assumption-test, /user-interview, /handoff all wait to
# be called. The founder's own report (dogfood, 2026-08-20) is that the moment
# needing discovery is precisely the moment nobody recognises it: "the user
# might not be aware that this requires discovery in the post." A skill cannot
# fire on a case the author did not notice. A prompt hook can.
#
# NOT A GATE. It never blocks and never proposes a study — the first response to
# an unvalidated claim is to TYPE it, which costs seconds and cannot become a
# nag. See opp-051 sol-051h risk (b) in the dogfood canvas.
#
# Contract: exit 0 silent = nothing to say; exit 0 + JSON additionalContext =
# advise. Fails open on every path.

# SELF-LOCATION: this script lives at <plugin_root>/hooks/, so its own path
# resolves the plugin root without anyone setting anything. CLAUDE_PLUGIN_ROOT
# is a Claude Code variable — Cursor exports CLAUDE_PROJECT_DIR instead and
# Codex exports neither, so a bare "${CLAUDE_PLUGIN_ROOT}/scripts/*.py" lookup
# resolves to "/scripts/*.py" there and silently no-ops. Same fix as
# absence-claim-guard.sh (v0.88.0).
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  _mycelium_self="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." 2>/dev/null && pwd || true)"
  if [ -n "$_mycelium_self" ] && [ -d "$_mycelium_self/scripts" ]; then
    CLAUDE_PLUGIN_ROOT="$_mycelium_self"
    export CLAUDE_PLUGIN_ROOT
  fi
fi

INPUT=$(cat)

HELPER="${CLAUDE_PLUGIN_ROOT}/scripts/discovery_trigger_guard.py"
if [ ! -f "$HELPER" ]; then
  # Legacy layout fallback, then silent no-op. Fail OPEN: this hook only
  # advises, so a missing helper must not block or nag.
  HELPER=".claude/scripts/discovery_trigger_guard.py"
  [ -f "$HELPER" ] || exit 0
fi

printf '%s' "$INPUT" | python3 "$HELPER"
exit 0
