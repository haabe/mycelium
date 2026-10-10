#!/usr/bin/env bash
# tests/bash/test_session_start_reflexion_debt.sh
#
# The carried-over reflexion warning reaches the session (v0.310.18).
#
# THE GAP: from v0.64.0 to v0.310.17 the block that reports reflexions left unreconciled by an
# earlier session sat after session-start.sh's final `exit 0`, so it never ran; and it printed
# plain text that would have broken the hook's JSON. Found by a review against the plugin reference.
#
#   sad   — one unreconciled reflexion on record: the warning is in the additionalContext
#   happy — no reflexion log: no warning

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$REPO_ROOT/plugins/mycelium/hooks/session-start.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

context_of() {  # $1 project dir
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT/plugins/mycelium" CLAUDE_PROJECT_DIR="$1" HOME="$TMP/home" \
      MYCELIUM_ADVISORY_LEDGER=off bash "$HOOK" < /dev/null 2>/dev/null | python3 -c "
import json, sys
t = sys.stdin.read()
print(json.loads(t)['hookSpecificOutput']['additionalContext'] if t.strip() else '')
"
}

# Both projects use Mycelium, so each carries an EMPTY .claude/canvas/ (the state right after
# /mycelium:setup): 0.318.0 hooks do nothing outside a Mycelium project (founder ruling 2026-10-10),
# and without the marker the happy case below would pass for that reason alone.

# --- sad: one reflexion fired in an earlier session, never reconciled -------------
P="$TMP/debt"; mkdir -p "$P/.claude/state" "$P/.claude/canvas"
printf '{"ts":"2026-09-01T10:00:00Z","tool":"Bash","command_head":"false","exit_code":"1","stderr_head":null}\n' \
  > "$P/.claude/state/reflexion-log.jsonl"
OUT=$(context_of "$P")
assert_contains "$OUT" "UNRECONCILED REFLEXIONS: 1" "a carried-over reflexion is reported at session start"

# --- happy: nothing on record --------------------------------------------------------
Q="$TMP/clean"; mkdir -p "$Q/.claude/canvas"
OUT2=$(context_of "$Q")
assert_not_contains "$OUT2" "UNRECONCILED REFLEXIONS" "no warning when nothing is outstanding"

report
