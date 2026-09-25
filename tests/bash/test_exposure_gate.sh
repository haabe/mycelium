#!/usr/bin/env bash
# tests/bash/test_exposure_gate.sh
# Coverage proof for hooks/exposure-gate.sh (v0.246.0): a deploy or publish waits for a delivery
# cycle in Deliver with Security, Privacy and Service Quality passed. E2E run 10 put an SMS app
# holding phone numbers and link tokens live under an L3 in define with every gate pending.
# Scenario-per-guardpost: an unready deploy blocks, a ready one passes, ordinary commands never
# start python, an unengaged project is not judged, and the user's delivery skip overrides.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"
source "$SCRIPT_DIR/_ladder.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GATE="$REPO_ROOT/plugins/mycelium/hooks/exposure-gate.sh"
ERR="$(mktemp)"
trap 'rm -f "$ERR"' EXIT

bash_json() { python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$1"; }
run_gate() {  # <project_dir> <command> -> exit code; stderr in $ERR
    printf '%s' "$(bash_json "$2")" | CLAUDE_PROJECT_DIR="$1" bash "$GATE" 2>"$ERR"
    echo $?
}

# The L3's learning delivery is dated (v0.257.0); pin the day so the fixture never expires.
export MYCELIUM_TODAY=2026-09-25
LEARNING='    learning_delivery:\n      audience: "Harbour staff, opted in"\n      until: "2026-10-25"\n      means: "infrastructure as code, torn down after"\n'

make_project() {  # <phase> <gates yaml flow map> [extra L3 yaml lines]
    local p; p=$(mktemp -d)
    mkdir -p "$p/.claude/diamonds" "$p/.claude/canvas" "$p/.claude/state"
    write_ladder "$p"
    printf 'why: "Swaps are approved in one place so nobody relays them"\nwho:\n  description: "Shift leads"\n' \
        > "$p/.claude/canvas/purpose.yml"
    printf 'desired_outcome:\n  metric: "swaps recorded in the app"\n%s\nopportunities:\n  - id: opp-001\n    name: "Approver away"\n    provenance:\n      evidence_type: anecdotal\n      evidence_sources: [research/pilot.md]\n    solutions:\n      - id: sol-001\n' "$OUTCOME_LINK" \
        > "$p/.claude/canvas/opportunities.yml"
    { printf 'active_diamonds:\n'; ladder_diamonds opp-001
      printf '  - id: l3-a\n    scale: L3\n    phase: %s\n    object_ref: sol-001\n    theory_gates_status: %s\n' "$1" "$2"
      printf "${3:-}"
    } > "$p/.claude/diamonds/active.yml"
    echo "$p"
}

READY="$EXPOSE_GATES"

test_deploy_under_define_blocks() {
    local p; p=$(make_project define '{evidence: pending}')
    local code; code=$(run_gate "$p" "ssh app@host 'cd app && git pull && systemctl restart cadence'")
    assert_eq "$code" "2" "a remote pull-and-restart under an L3 in define -> blocked"
    assert_contains "$(cat "$ERR")" "in Deliver" "names the phase the work belongs in"
    assert_contains "$(cat "$ERR")" "security gate passed" "names the missing Security gate"
    assert_contains "$(cat "$p/.claude/state/exposure-gate-fires.jsonl" 2>/dev/null)" "blocked" "the block is logged"
    rm -rf "$p"
}

test_ready_cycle_deploys() {
    local p; p=$(make_project deliver "$READY" "$LEARNING")
    assert_eq "$(run_gate "$p" "fly deploy")" "0" "Deliver with its gates passed -> the deploy runs"
    rm -rf "$p"
}

test_l3_without_a_learning_delivery_blocks() {
    local p; p=$(make_project deliver "$READY")
    assert_eq "$(run_gate "$p" "fly deploy")" "2" "an L3 names its audience before it deploys"
    rm -rf "$p"
}

test_ordinary_commands_pass() {
    local p; p=$(make_project define '{evidence: pending}')
    assert_eq "$(run_gate "$p" "git push origin main")" "0" "a push to origin is not a deploy"
    assert_eq "$(run_gate "$p" "python -m pytest")" "0" "tests are not a deploy"
    rm -rf "$p"
}

test_unengaged_project_not_judged() {
    local p; p=$(mktemp -d)
    assert_eq "$(run_gate "$p" "fly deploy")" "0" "no diamonds at all -> not this gate's business"
    rm -rf "$p"
}

test_delivery_skip_overrides() {
    local p; p=$(make_project define '{evidence: pending}')
    printf '2026-09-24 user: this is my own test box, not tracked\n' > "$p/.claude/state/delivery-skip-ack"
    assert_eq "$(run_gate "$p" "fly deploy")" "0" "the user's delivery skip -> allowed"
    rm -rf "$p"
}

run_test test_deploy_under_define_blocks
run_test test_ready_cycle_deploys
run_test test_l3_without_a_learning_delivery_blocks
run_test test_ordinary_commands_pass
run_test test_unengaged_project_not_judged
run_test test_delivery_skip_overrides

report
