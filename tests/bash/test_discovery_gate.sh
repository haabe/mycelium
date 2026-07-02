#!/usr/bin/env bash
# tests/bash/test_discovery_gate.sh
# Coverage proof for hooks/discovery-gate.sh (deliver-framed routing gap,
# mechanically reproduced by roadmap auto-dogfood 2026-07-02).
# Scenario-per-guardpost: bad path blocks, happy/guard paths allow,
# escape hatch allows, edit-shaped work never touched.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GATE="$REPO_ROOT/plugins/mycelium/hooks/discovery-gate.sh"

# run_gate <project_dir> <json> -> prints exit code; stderr lands in
# $GATE_ERR_FILE (a file, not a variable — run_gate is called inside $(),
# so variable assignments would die with the subshell).
GATE_ERR_FILE="$(mktemp)"
trap 'rm -f "$GATE_ERR_FILE"' EXIT
run_gate() {
    local pdir="$1" json="$2"
    printf '%s' "$json" | CLAUDE_PROJECT_DIR="$pdir" bash "$GATE" 2>"$GATE_ERR_FILE"
    echo $?
}
gate_err() { cat "$GATE_ERR_FILE"; }

# Fresh project dir with a template-only active.yml (setup ran, discovery didn't).
make_cold_project() {
    local tmp; tmp=$(mktemp -d)
    mkdir -p "$tmp/.claude/diamonds" "$tmp/.claude/canvas" "$tmp/.claude/state"
    printf 'project_type: ""\ndogfood: false\nactive_diamonds: []\nlast_updated: null\n' \
        > "$tmp/.claude/diamonds/active.yml"
    echo "$tmp"
}

write_json() { # <path>
    printf '{"tool_name":"Write","tool_input":{"file_path":"%s","content":"x"}}' "$1"
}

test_bad_path_blocks_new_source_on_cold_project() {
    local p; p=$(make_cold_project)
    local code; code=$(run_gate "$p" "$(write_json "$p/app/main.py")")
    assert_eq "$code" "2" "cold project + new .py -> blocked"
    assert_contains "$(gate_err)" "/mycelium:start" "block message routes to discovery"
    assert_contains "$(gate_err)" "discovery-skip-ack" "block message names the escape hatch"
    code=$(run_gate "$p" "$(write_json "$p/docker-compose.yml")")
    assert_eq "$code" "2" "cold project + new docker-compose.yml -> blocked (basename list)"
    rm -rf "$p"
}

test_happy_path_diamond_present_allows() {
    local p; p=$(make_cold_project)
    printf 'active_diamonds:\n  - id: d-001\n    scale: L3\n    phase: deliver\n' \
        > "$p/.claude/diamonds/active.yml"
    local code; code=$(run_gate "$p" "$(write_json "$p/app/export.py")")
    assert_eq "$code" "0" "diamond present (any phase) -> new source allowed"
    rm -rf "$p"
}

test_populated_purpose_allows() {
    local p; p=$(make_cold_project)
    printf 'purpose:\n  statement: "Hikers decide with past knowledge instead of guessing on trail conditions"\n' \
        > "$p/.claude/canvas/purpose.yml"
    local code; code=$(run_gate "$p" "$(write_json "$p/src/index.ts")")
    assert_eq "$code" "0" "populated purpose.yml -> allowed (discovery engaged mid-flow)"
    rm -rf "$p"
}

test_ack_file_allows() {
    local p; p=$(make_cold_project)
    printf '2026-07-02: user said "just build it, no discovery"\n' \
        > "$p/.claude/state/discovery-skip-ack"
    local code; code=$(run_gate "$p" "$(write_json "$p/main.go")")
    assert_eq "$code" "0" "discovery-skip-ack present -> allowed (user decided, on record)"
    rm -rf "$p"
}

test_edit_tool_never_blocked() {
    local p; p=$(make_cold_project)
    local json='{"tool_name":"Edit","tool_input":{"file_path":"'"$p"'/app/main.py","new_string":"x"}}'
    local code; code=$(run_gate "$p" "$json")
    assert_eq "$code" "0" "Edit tool -> never gated (brownfield work untouched)"
    rm -rf "$p"
}

test_existing_file_write_allowed() {
    local p; p=$(make_cold_project)
    mkdir -p "$p/app"; echo "pass" > "$p/app/main.py"
    local code; code=$(run_gate "$p" "$(write_json "$p/app/main.py")")
    assert_eq "$code" "0" "Write to EXISTING file -> allowed (brownfield full-replace)"
    rm -rf "$p"
}

test_non_source_files_allowed() {
    local p; p=$(make_cold_project)
    local code
    code=$(run_gate "$p" "$(write_json "$p/notes.md")")
    assert_eq "$code" "0" "new .md -> not gated"
    code=$(run_gate "$p" "$(write_json "$p/.claude/canvas/purpose.yml")")
    assert_eq "$code" "0" ".claude/ paths -> never gated"
    code=$(run_gate "$p" "$(write_json "$p/config.yml")")
    assert_eq "$code" "0" "generic .yml -> not gated (canvas/config territory)"
    rm -rf "$p"
}

test_missing_active_yml_still_blocks() {
    # Plugin installed but /setup never ran: the coldest workspace.
    local tmp; tmp=$(mktemp -d)
    local code; code=$(run_gate "$tmp" "$(write_json "$tmp/server.js")")
    assert_eq "$code" "2" "no .claude state at all -> still blocked"
    rm -rf "$tmp"
}

run_test test_bad_path_blocks_new_source_on_cold_project
run_test test_happy_path_diamond_present_allows
run_test test_populated_purpose_allows
run_test test_ack_file_allows
run_test test_edit_tool_never_blocked
run_test test_existing_file_write_allowed
run_test test_non_source_files_allowed
run_test test_missing_active_yml_still_blocks

report
