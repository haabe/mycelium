#!/usr/bin/env bash
# tests/bash/test_scale_lock_gate.sh
# Coverage proof for hooks/scale-lock-gate.sh (v0.245.0): a write to diamonds/active.yml that ADDS
# a diamond whose parent has not established what it builds on is refused, naming what is missing.
# Founder model, 2026-09-24: "all scales have a natural lock per se ... There's a dependency tree."
# Scenario-per-guardpost: a locked addition blocks, a held one passes, an edit to an existing
# diamond passes, other files never start python, and the user's ack overrides.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GATE="$REPO_ROOT/plugins/mycelium/hooks/scale-lock-gate.sh"
ERR="$(mktemp)"
trap 'rm -f "$ERR"' EXIT

run_gate() {  # <project_dir> <json> -> exit code; stderr in $ERR
    printf '%s' "$2" | CLAUDE_PROJECT_DIR="$1" bash "$GATE" 2>"$ERR"
    echo $?
}

make_project() {  # purpose stated, nothing below it: the state /mycelium:start leaves
    local p; p=$(mktemp -d)
    mkdir -p "$p/.claude/diamonds" "$p/.claude/canvas" "$p/.claude/state"
    printf 'why: "Swaps are approved in one place so nobody relays them"\nwho:\n  description: "Shift leads"\n' \
        > "$p/.claude/canvas/purpose.yml"
    printf 'active_diamonds:\n  - id: l0\n    scale: L0\n    phase: discover\n' > "$p/.claude/diamonds/active.yml"
    echo "$p"
}

write_active() {  # <project_dir> <yaml body>
    python3 -c 'import json,sys; print(json.dumps({"tool_name":"Write","tool_input":{"file_path":sys.argv[1]+"/.claude/diamonds/active.yml","content":sys.argv[2]}}))' "$1" "$2"
}

L0='active_diamonds:\n  - id: l0\n    scale: L0\n    phase: discover\n'

test_l3_straight_after_start_blocks() {
    local p; p=$(make_project)
    local code; code=$(run_gate "$p" "$(write_active "$p" "$(printf "$L0"'  - id: l3-a\n    scale: L3\n    phase: discover\n')")")
    assert_eq "$code" "2" "an L3 with only a purpose above it -> blocked"
    assert_contains "$(cat "$ERR")" "desired outcome" "names the missing desired outcome"
    assert_contains "$(cat "$ERR")" "scale-lock-ack" "names the user-only override"
    assert_contains "$(cat "$p/.claude/state/scale-lock-fires.jsonl" 2>/dev/null)" "blocked" "the block is logged"
    rm -rf "$p"
}

test_l1_on_a_stated_purpose_passes() {
    local p; p=$(make_project)
    local code; code=$(run_gate "$p" "$(write_active "$p" "$(printf "$L0"'  - id: l1-a\n    scale: L1\n    phase: discover\n')")")
    assert_eq "$code" "0" "an L1 on a stated purpose -> allowed"
    rm -rf "$p"
}

test_l1_without_a_purpose_blocks() {
    local p; p=$(make_project)
    rm "$p/.claude/canvas/purpose.yml"
    local code; code=$(run_gate "$p" "$(write_active "$p" "$(printf "$L0"'  - id: l1-a\n    scale: L1\n    phase: discover\n')")")
    assert_eq "$code" "2" "an L1 with no purpose -> blocked"
    rm -rf "$p"
}

test_edit_adding_l2_without_outcome_blocks() {
    local p; p=$(make_project)
    local json; json=$(python3 -c 'import json,sys; print(json.dumps({"tool_name":"Edit","tool_input":{"file_path":sys.argv[1]+"/.claude/diamonds/active.yml","old_string":"    phase: discover\n","new_string":"    phase: discover\n  - id: l2-a\n    scale: L2\n    phase: discover\n"}}))' "$p")
    local code; code=$(run_gate "$p" "$json")
    assert_eq "$code" "2" "an Edit that adds an L2 with no desired outcome -> blocked"
    rm -rf "$p"
}

test_existing_diamond_edit_never_blocks() {
    local p; p=$(make_project)
    printf "$L0"'  - id: l4-old\n    scale: L4\n    phase: develop\n' > "$p/.claude/diamonds/active.yml"
    local code; code=$(run_gate "$p" "$(write_active "$p" "$(printf "$L0"'  - id: l4-old\n    scale: L4\n    phase: deliver\n')")")
    assert_eq "$code" "0" "moving an existing (pre-lock) L4 -> allowed; --check reports it"
    rm -rf "$p"
}

test_users_ack_overrides() {
    local p; p=$(make_project)
    printf 'l3-a L3 2026-09-24 user: "prototype first, I will fill the tree after"\n' > "$p/.claude/state/scale-lock-ack"
    local code; code=$(run_gate "$p" "$(write_active "$p" "$(printf "$L0"'  - id: l3-a\n    scale: L3\n    phase: discover\n')")")
    assert_eq "$code" "0" "the diamond id in the user's ack -> allowed"
    rm -rf "$p"
}

test_other_files_pass_without_python() {
    local p; p=$(make_project)
    local bin; bin=$(mktemp -d); ln -s "$(command -v cat)" "$bin/cat"   # cat, and no python3
    local code
    code=$(printf '%s' '{"tool_name":"Write","tool_input":{"file_path":"src/app.py","content":"x"}}' \
        | PATH="$bin" CLAUDE_PROJECT_DIR="$p" "$BASH" "$GATE" 2>"$ERR"; echo $?)
    assert_eq "$code" "0" "a write to any other file exits before python"
    rm -rf "$p" "$bin"
}

run_test test_l3_straight_after_start_blocks
run_test test_l1_on_a_stated_purpose_passes
run_test test_l1_without_a_purpose_blocks
run_test test_edit_adding_l2_without_outcome_blocks
run_test test_existing_diamond_edit_never_blocks
run_test test_users_ack_overrides
run_test test_other_files_pass_without_python

report
