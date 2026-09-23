#!/usr/bin/env bash
# tests/bash/test_session_start_unfinished_discovery.sh
# Coverage proof for the UNFINISHED DISCOVERY nudge in hooks/session-start.sh (v0.244.0).
#
# Found in an end-to-end dogfood run on the installed plugin: the founder left /mycelium:start
# after question 3; later sessions opened an L3 diamond and built code on a project with no
# purpose, and nothing offered to finish the interview. Scenario-per-guardpost: the two states
# that must nudge, and the two that must stay silent.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$REPO_ROOT/plugins/mycelium/hooks/session-start.sh"

run_hook() {  # <project_dir> -> hook stdout
    printf '{"source":"startup"}' \
      | CLAUDE_PROJECT_DIR="$1" CLAUDE_PLUGIN_ROOT="$REPO_ROOT/plugins/mycelium" \
        MYCELIUM_CROSS_REPO_WATCH="" MYCELIUM_ADVISORY_LEDGER=off bash "$HOOK" 2>/dev/null
}

make_project() {  # set up as /mycelium:setup leaves it; no purpose, no diamonds
    local p; p=$(mktemp -d)
    mkdir -p "$p/.claude/diamonds" "$p/.claude/canvas" "$p/.claude/state"
    printf 'active_diamonds: []\n' > "$p/.claude/diamonds/active.yml"
    echo "$p"
}

test_fresh_setup_is_silent() {
    local p; p=$(make_project)
    assert_not_contains "$(run_hook "$p")" "UNFINISHED DISCOVERY" "setup ran, nothing started: no nudge"
    rm -rf "$p"
}

test_interview_in_progress_nudges() {
    local p; p=$(make_project)
    printf 'Q1: What are you trying to change, and for whom?\nA: ...\n' \
        > "$p/.claude/state/interview-in-progress.md"
    local out; out=$(run_hook "$p")
    assert_contains "$out" "UNFINISHED DISCOVERY" "a saved half-interview nudges"
    assert_contains "$out" "interview-in-progress.md" "the nudge points at the saved answers"
    rm -rf "$p"
}

test_diamond_without_purpose_nudges() {
    local p; p=$(make_project)
    printf 'active_diamonds:\n  - id: harbour\n    scale: L3\n    phase: develop\n' \
        > "$p/.claude/diamonds/active.yml"
    assert_contains "$(run_hook "$p")" "UNFINISHED DISCOVERY" "a diamond on a purpose-less project nudges"
    rm -rf "$p"
}

test_purpose_present_is_silent() {
    local p; p=$(make_project)
    printf 'active_diamonds:\n  - id: harbour\n    scale: L3\n    phase: develop\n' \
        > "$p/.claude/diamonds/active.yml"
    printf 'why: "Swaps are approved in one place so nobody relays them by hand"\n' \
        > "$p/.claude/canvas/purpose.yml"
    assert_not_contains "$(run_hook "$p")" "UNFINISHED DISCOVERY" "a real purpose: no nudge"
    rm -rf "$p"
}

run_test test_fresh_setup_is_silent
run_test test_interview_in_progress_nudges
run_test test_diamond_without_purpose_nudges
run_test test_purpose_present_is_silent

report
