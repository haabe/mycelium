#!/usr/bin/env bash
# Mycelium autonomous-evidence-guard hook
# (PreToolUse on Write|Edit|MultiEdit + MCP filesystem write/edit)
#
# Enforces the engine/autonomous-mode.md evidence-integrity boundary as
# MECHANISM, not prose. In a DECLARED autonomous run (env
# MYCELIUM_AUTONOMOUS_RUN or diamonds/active.yml `autonomous: true`), blocks
# canvas writes that introduce source_class: external_* / validated: true /
# evidence_type above speculation -- the fabrication a sub-Fable-5 model
# committed in opp-011 Stage A (2026-06-11) without knowing it.
#
# No-op for every interactive (human-present) session: the helper's first act
# is the autonomous-mode check, and a present human is never autonomous.
#
# Contract: exit 0 silent = allow; exit 0 + JSON permissionDecision=deny = block.
# Fail-OPEN on a missing helper (unlike framework-guard's fail-closed): the
# helper is what decides autonomous-ness, so without it we cannot tell, and the
# model-tier doc restriction remains the backstop. Never brick writes.
set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

HELPER=""
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/scripts/autonomous_evidence_guard.py" ]; then
  HELPER="${CLAUDE_PLUGIN_ROOT}/scripts/autonomous_evidence_guard.py"
elif [ -f "$PROJECT_DIR/.claude/scripts/autonomous_evidence_guard.py" ]; then
  HELPER="$PROJECT_DIR/.claude/scripts/autonomous_evidence_guard.py"
fi

INPUT=$(cat)

if [ -n "$HELPER" ]; then
  printf '%s' "$INPUT" | python3 "$HELPER" "$PROJECT_DIR"
  exit $?
fi

# Helper missing in both plugin and legacy paths -> fail-open (allow).
exit 0
