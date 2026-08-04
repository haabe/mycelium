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

INPUT=$(cat)

HELPER="${CLAUDE_PLUGIN_ROOT}/scripts/ci_signal.py"
if [ ! -f "$HELPER" ]; then
  HELPER=".claude/scripts/ci_signal.py"
  [ -f "$HELPER" ] || exit 0
fi

printf '%s' "$INPUT" | python3 "$HELPER" "$@"
exit 0
