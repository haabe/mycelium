#!/usr/bin/env bash
# tests/bash/test_session_start_advisory_ledger.sh
#
# Coverage proof that hooks/session-start.sh records its advisories in the ledger (v0.184.0).
#
# THE GAP (dogfood 2026-09-09, opp-006 sol-006d): the hook computed twenty advisories
# and nothing recorded whether any was ever followed. Two had fired daily for 32 and
# 101 days; BVSSH rated Measurement amber for the third time on exactly that.
#
# Scenario-per-guardpost:
#   happy — two starts, two sessions: a `seen` event each, and a `settled` event on the second
#   sad   — MYCELIUM_ADVISORY_LEDGER=off: no ledger file is written
#   bad   — a corrupt ledger line: the hook still emits its advisories, and says so
#
# Discovered + run by tests/bash/run.sh, so it executes in CI and pre-push.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLUGIN_ROOT="$REPO_ROOT/plugins/mycelium"
HOOK="$PLUGIN_ROOT/hooks/session-start.sh"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mk_project() {
    local proj="$TMP/$1"
    mkdir -p "$proj/.claude/canvas"
    # An open task that is stale by weeks: guarantees the OPEN-human-task advisory fires.
    cat > "$proj/.claude/canvas/human-tasks.yml" <<'YAML'
schema_version: 1
pending_tasks:
  - id: ht-1
    type: outreach
    objective: an open task
    status: pending
    created_at: "2026-01-01"
YAML
    echo "$proj"
}

run_hook() {  # $1 project, $2 session id
    printf '{"hook_event_name":"SessionStart","source":"startup","session_id":"%s"}' "$2" \
      | MYCELIUM_CROSS_REPO_WATCH="" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" CLAUDE_PROJECT_DIR="$1" \
        bash "$HOOK" 2>/dev/null | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin)['hookSpecificOutput']['additionalContext'])
except Exception:
    print('')
"
}

# --- happy: two sessions -> seen, seen, settled --------------------------
P=$(mk_project happy)
OUT1=$(run_hook "$P" sess-1)
assert_contains "$OUT1" "OPEN human task" "the advisory fires on the fixture"
LEDGER="$P/.claude/state/advisory-ledger.jsonl"
assert_eq "1" "$(grep -c '"kind": "seen"' "$LEDGER")" "first start writes one seen event"
OUT2=$(run_hook "$P" sess-2)
assert_eq "2" "$(grep -c '"kind": "seen"' "$LEDGER")" "second start writes a second seen event"
assert_eq "1" "$(grep -c '"kind": "settled"' "$LEDGER")" "second start settles the first"
assert_contains "$(cat "$LEDGER")" '"open-human-tasks": "still_firing"' "the unchanged advisory settles as still_firing"
assert_contains "$OUT2" "OPEN human task" "the advisory is still emitted (not yet at the mute threshold)"

# --- sad: override off -> nothing written --------------------------------
P2=$(mk_project off)
printf '{"session_id":"x"}' | MYCELIUM_ADVISORY_LEDGER=off MYCELIUM_CROSS_REPO_WATCH="" \
  CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" CLAUDE_PROJECT_DIR="$P2" bash "$HOOK" >/dev/null 2>&1
if [ -f "$P2/.claude/state/advisory-ledger.jsonl" ]; then
    assert_eq "absent" "present" "override off must not write a ledger"
else
    assert_eq "absent" "absent" "override off writes no ledger"
fi

# --- bad: corrupt ledger line -> advisories still emitted, and it says so --
P3=$(mk_project corrupt)
mkdir -p "$P3/.claude/state"
printf '{not json\n' > "$P3/.claude/state/advisory-ledger.jsonl"
OUT3=$(run_hook "$P3" sess-9)
assert_contains "$OUT3" "OPEN human task" "a corrupt ledger does not silence the advisories"
assert_contains "$OUT3" "advisory ledger: line 1" "the corrupt line is named, not swallowed"

report
