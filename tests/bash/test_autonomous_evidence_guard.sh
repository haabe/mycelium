#!/usr/bin/env bash
# tests/bash/test_autonomous_evidence_guard.sh
# Coverage proof for the autonomous-evidence-guard hook (opp-011 Stage A fix).
# Exercises the Python helper directly with PreToolUse-shaped JSON.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HELPER="$REPO_ROOT/plugins/mycelium/scripts/autonomous_evidence_guard.py"

# run_guard <autonomous:0|1> <project_dir> <json> -> stdout of helper
run_guard() {
    local auton="$1" pdir="$2" json="$3"
    if [ "$auton" = "1" ]; then
        printf '%s' "$json" | MYCELIUM_AUTONOMOUS_RUN=1 python3 "$HELPER" "$pdir"
    else
        printf '%s' "$json" | env -u MYCELIUM_AUTONOMOUS_RUN python3 "$HELPER" "$pdir"
    fi
}

CANVAS_FAB='{"tool_name":"Write","tool_input":{"file_path":"/p/.claude/canvas/purpose.yml","content":"desirability:\n  source_class: external_human\n  validated: true\n"}}'
CANVAS_CLEAN='{"tool_name":"Write","tool_input":{"file_path":"/p/.claude/canvas/purpose.yml","content":"desirability:\n  source_class: internal_simulated\n  evidence_type: speculation\n  validated: false\n"}}'
EDIT_VALIDATED='{"tool_name":"Edit","tool_input":{"file_path":"/p/.claude/canvas/opportunities.yml","new_string":"      validated: true"}}'
EDIT_EVTYPE='{"tool_name":"Edit","tool_input":{"file_path":"/p/.claude/diamonds/active.yml","new_string":"    evidence_type: test-validated"}}'
NONCANVAS_FAB='{"tool_name":"Write","tool_input":{"file_path":"/p/docs/notes.md","content":"source_class: external_human"}}'

test_allows_when_not_autonomous() {
    local out; out=$(run_guard 0 /tmp "$CANVAS_FAB")
    assert_not_contains "$out" "deny" "interactive (no human-absent flag): fabrication-shaped write is allowed — human judgment stands"
}

test_blocks_external_human_in_autonomous() {
    local out; out=$(run_guard 1 /tmp "$CANVAS_FAB")
    assert_contains "$out" "\"permissionDecision\": \"deny\"" "autonomous: blocks external_human canvas write"
    assert_contains "$out" "source_class: external_human" "names the offending token"
}

test_blocks_validated_true_edit() {
    local out; out=$(run_guard 1 /tmp "$EDIT_VALIDATED")
    assert_contains "$out" "deny" "autonomous: blocks validated:true edit"
}

test_blocks_evidence_type_upgrade() {
    local out; out=$(run_guard 1 /tmp "$EDIT_EVTYPE")
    assert_contains "$out" "deny" "autonomous: blocks evidence_type above speculation"
}

test_allows_clean_simulated_write() {
    local out; out=$(run_guard 1 /tmp "$CANVAS_CLEAN")
    assert_not_contains "$out" "deny" "autonomous: internal_simulated/speculation/validated:false is allowed"
}

test_ignores_noncanvas_path() {
    local out; out=$(run_guard 1 /tmp "$NONCANVAS_FAB")
    assert_not_contains "$out" "deny" "autonomous: out-of-scope path (docs/*.md) not enforced"
}

test_activates_via_active_yml_flag() {
    local tmp; tmp=$(mktemp -d)
    mkdir -p "$tmp/.claude/diamonds"
    printf 'autonomous: true\nactive_diamonds: []\n' > "$tmp/.claude/diamonds/active.yml"
    # No env flag set; activation must come from active.yml
    local out; out=$(run_guard 0 "$tmp" "$CANVAS_FAB")
    rm -rf "$tmp"
    assert_contains "$out" "deny" "autonomous via active.yml flag (no env): blocks fabrication"
}

run_test test_allows_when_not_autonomous
run_test test_blocks_external_human_in_autonomous
run_test test_blocks_validated_true_edit
run_test test_blocks_evidence_type_upgrade
run_test test_allows_clean_simulated_write
run_test test_ignores_noncanvas_path
run_test test_activates_via_active_yml_flag

report
