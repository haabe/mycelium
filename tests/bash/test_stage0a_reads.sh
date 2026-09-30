#!/usr/bin/env bash
# tests/bash/test_stage0a_reads.sh
# Two reads fixed in v0.289.0 (phase migration, stage 0a), each with a control:
#   - stop-check's "an L4 is building or delivering" came from the substrings "L4" and "deliver"
#     anywhere in active.yml, so a note mentioning them fired the G-S2 threat-model warning. It now
#     reads the YAML.
#   - session-start CHECK 10 (a shipped diamond's outcome check) read only active_diamonds with
#     phase: complete, and never saw diamonds kept in completed_diamonds, where the dogfood project
#     keeps them.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLUGIN_ROOT="$REPO_ROOT/plugins/mycelium"
STOP="$PLUGIN_ROOT/hooks/stop-check.sh"
START="$PLUGIN_ROOT/hooks/session-start.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

stop_project() {  # <name> <active.yml body>
    local p="$TMP/$1"
    mkdir -p "$p/.claude/diamonds" "$p/.claude/canvas" "$p/.claude/state"
    printf '%s' "$2" > "$p/.claude/diamonds/active.yml"
    printf 'components: []\n' > "$p/.claude/canvas/threat-model.yml"
    echo "$p"
}
run_stop() { printf '{"hook_event_name":"Stop"}' | CLAUDE_PROJECT_DIR="$1" bash "$STOP" 2>/dev/null; }

test_an_l4_delivering_gets_the_threat_model_warning() {
    local p; p=$(stop_project l4 $'active_diamonds:\n  - id: l4-a\n    scale: L4\n    phase: deliver\n')
    assert_contains "$(run_stop "$p")" "G-S2" "an L4 in deliver with no threat model assessed -> G-S2"
}

test_a_note_mentioning_l4_and_deliver_does_not() {
    local body=$'active_diamonds:\n  - id: l3-a\n    scale: L3\n    phase: define\n    notes: "an L4 will deliver this later"\n'
    local p; p=$(stop_project note "$body")
    assert_not_contains "$(run_stop "$p")" "G-S2" "an L3 whose note mentions L4 and deliver -> no G-S2 (fails on 0.288.1)"
}

test_an_archived_l4_does_not() {
    local body=$'active_diamonds:\n  - id: l4-a\n    scale: L4\n    phase: deliver\n    state: archived\n'
    local p; p=$(stop_project archived "$body")
    assert_not_contains "$(run_stop "$p")" "G-S2" "an L4 archived in place is not building -> no G-S2"
}

run_start() {
    printf '{"hook_event_name":"SessionStart","source":"startup","session_id":"s1"}' \
      | MYCELIUM_CROSS_REPO_WATCH="" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" CLAUDE_PROJECT_DIR="$1" \
        bash "$START" 2>/dev/null
}

test_a_completed_diamond_in_completed_diamonds_is_outcome_checked() {
    local p="$TMP/done"
    mkdir -p "$p/.claude/diamonds" "$p/.claude/canvas"
    printf 'active_diamonds: []\ncompleted_diamonds:\n  - id: l2-done\n    scale: L2\n    definition_of_done:\n      signal: "a verdict on the riskiest assumption"\n' \
        > "$p/.claude/diamonds/active.yml"
    assert_contains "$(run_start "$p")" "signal but no measure (l2-done)" \
        "a diamond kept in completed_diamonds reaches the outcome check (fails on 0.288.1)"
}

test_control_the_active_list_form_still_works() {
    local p="$TMP/done-active"
    mkdir -p "$p/.claude/diamonds" "$p/.claude/canvas"
    printf 'active_diamonds:\n  - id: l3-done\n    scale: L3\n    phase: complete\n    definition_of_done:\n      signal: "pilot validated"\n' \
        > "$p/.claude/diamonds/active.yml"
    assert_contains "$(run_start "$p")" "signal but no measure (l3-done)" "phase: complete in active_diamonds still counts"
}

run_test test_an_l4_delivering_gets_the_threat_model_warning
run_test test_a_note_mentioning_l4_and_deliver_does_not
run_test test_an_archived_l4_does_not
run_test test_a_completed_diamond_in_completed_diamonds_is_outcome_checked
run_test test_control_the_active_list_form_still_works
report
