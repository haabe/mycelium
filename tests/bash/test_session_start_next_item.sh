#!/usr/bin/env bash
# tests/bash/test_session_start_next_item.sh
#
# Coverage proof for the one-item surface (v0.188.0, opp-006 sol-006f).
#
# Scenario-per-guardpost:
#   happy — startup: NEXT ITEM line prepended to the agent block, no systemMessage (startup is
#           not a re-entry moment), state file written
#   happy — resume: the same line ALSO as a systemMessage, the channel a human sees
#   happy — Stop: the repeat hook says it once ("Still open from session start"), then never again
#   sad   — a ruling recorded after emission: the repeat hook stays silent
#   sad   — MYCELIUM_NEXT_ITEM=off: no line, no state, no repeat
#   edge  — a canvas with nothing qualifying: no line at all
#
# Discovered + run by tests/bash/run.sh, so it executes in CI and pre-push.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLUGIN_ROOT="$REPO_ROOT/plugins/mycelium"
HOOK="$PLUGIN_ROOT/hooks/session-start.sh"
REPEAT="$PLUGIN_ROOT/hooks/next-item-repeat.sh"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mk_project() {
    local proj="$TMP/$1"
    mkdir -p "$proj/.claude/canvas"
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

run_hook() {  # $1 project, $2 source, $3 session id; prints "<systemMessage>|||<context>"
    printf '{"hook_event_name":"SessionStart","source":"%s","session_id":"%s"}' "$2" "$3" \
      | MYCELIUM_CROSS_REPO_WATCH="" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" CLAUDE_PROJECT_DIR="$1" \
        bash "$HOOK" 2>/dev/null | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print((d.get('systemMessage') or '') + '|||' + d['hookSpecificOutput']['additionalContext'])
except Exception:
    print('|||')
"
}
run_repeat() {  # $1 project
    printf '{"hook_event_name":"Stop","session_id":"x"}' \
      | CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" CLAUDE_PROJECT_DIR="$1" bash "$REPEAT" 2>/dev/null
}

# --- startup: line in context, no systemMessage, state written ----------------
P=$(mk_project a)
OUT=$(run_hook "$P" startup s1)
CTX="${OUT#*|||}"; MSG="${OUT%%|||*}"
assert_contains "$CTX" "NEXT ITEM: Open human tasks are waiting on a read." "the one item is prepended to the agent block"
assert_contains "$CTX" "run \`/mycelium:log-evidence\`" "the item carries the exact command"
assert_eq "$MSG" "" "startup sends no systemMessage"
assert_eq "$(python3 -c "import json;print(json.load(open('$P/.claude/state/next-item.json'))['id'])")" "open-human-tasks" "state file records the item"

# --- resume: also a systemMessage ---------------------------------------------
OUT=$(run_hook "$P" resume s2)
MSG="${OUT%%|||*}"
assert_contains "$MSG" "NEXT ITEM: Open human tasks are waiting on a read." "resume sends the item as a systemMessage"

# --- Stop: repeat once, then silent ----------------------------------------------
R1=$(run_repeat "$P")
assert_contains "$R1" "Still open from session start. NEXT ITEM:" "first Stop repeats the item once"
R2=$(run_repeat "$P")
assert_eq "$R2" "" "second Stop is silent"

# --- a ruling after emission silences the repeat --------------------------------
P2=$(mk_project b)
run_hook "$P2" startup s3 >/dev/null
python3 "$PLUGIN_ROOT/scripts/advisory_ledger.py" rule --project-dir "$P2" --id open-human-tasks --ruling snooze --until 2099-01-01 >/dev/null
R3=$(run_repeat "$P2")
assert_eq "$R3" "" "a ruling recorded after emission silences the repeat"

# --- override off ----------------------------------------------------------------
P3=$(mk_project c)
OUT=$(printf '{"hook_event_name":"SessionStart","source":"resume","session_id":"s4"}' \
      | MYCELIUM_NEXT_ITEM=off MYCELIUM_CROSS_REPO_WATCH="" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" CLAUDE_PROJECT_DIR="$P3" \
        bash "$HOOK" 2>/dev/null)
assert_not_contains "$OUT" "NEXT ITEM" "override off emits no item"
if [ -f "$P3/.claude/state/next-item.json" ]; then
    assert_eq "present" "absent" "override off writes no state"
else
    assert_eq "absent" "absent" "override off writes no state"
fi

# --- nothing qualifying -----------------------------------------------------------
P4="$TMP/d"; mkdir -p "$P4/.claude/canvas"
printf 'schema_version: 1\npending_tasks: []\n' > "$P4/.claude/canvas/human-tasks.yml"
OUT=$(run_hook "$P4" startup s5)
assert_not_contains "$OUT" "NEXT ITEM" "a canvas with nothing qualifying gets no item"

report
