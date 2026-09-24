#!/usr/bin/env bash
# tests/bash/test_preflight_discovery_prewarning.sh
# Locks the v0.222.0 discovery pre-warning in hooks/preflight.sh: one line on
# UserPromptSubmit that tells the model the discovery gate WILL refuse new source
# files, emitted under exactly the condition the gate itself uses.
#
# What this protects is the CONDITION, not the wording. The behavioural claim (the
# line moves a build-framed opening from "drafts the schema" to "asks who, problem,
# evidence") was tested once against a frozen prediction, 3 of 3 and 3 of 3 on the
# negative control; a bash test cannot re-run that and does not pretend to.
#
# The two ways this goes wrong, one test each:
#   - it goes SILENT while the gate still blocks (the model is back to meeting the
#     gate after the work is done), or
#   - it keeps TALKING after discovery state or the user's skip-ack exists (a
#     standing nag on every prompt of an initialized project).

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLUGIN_ROOT="$REPO_ROOT/plugins/mycelium"
HOOK="$PLUGIN_ROOT/hooks/preflight.sh"
PROMPT_JSON='{"hook_event_name":"UserPromptSubmit","prompt":"hello","session_id":"prewarning-test"}'
MARK="MYCELIUM DISCOVERY STATE"

_run() {  # $1 project dir
    printf '%s' "$PROMPT_JSON" | CLAUDE_PROJECT_DIR="$1" CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" bash "$HOOK" 2>/dev/null
}

test_empty_project_is_warned() {
    local tmp; tmp=$(mktemp -d)
    local out; out=$(_run "$tmp")
    rm -rf "$tmp"
    assert_contains "$out" "$MARK" "no discovery state: the pre-warning is emitted"
    assert_contains "$out" "WILL BE REFUSED" "it states the gate's verdict, which is the part that binds"
    assert_contains "$out" "If the prompt is not a build request, ignore this line" "it releases non-build prompts explicitly"
    assert_contains "$out" "Mycelium preflight complete" "the ordinary preflight line still follows"
    assert_stdout_json_or_text "$out" "stdout stays plain text"
}

test_skip_ack_silences_it() {
    local tmp; tmp=$(mktemp -d)
    mkdir -p "$tmp/.claude/state"
    printf '2026-09-17 user: "skip discovery, just build"\n' > "$tmp/.claude/state/discovery-skip-ack"
    local out; out=$(_run "$tmp")
    rm -rf "$tmp"
    assert_not_contains "$out" "$MARK" "the user's recorded skip silences it, as it silences the gate"
    assert_contains "$out" "Mycelium preflight complete" "the ordinary preflight line is unaffected"
}

test_populated_purpose_silences_it() {
    local tmp; tmp=$(mktemp -d)
    mkdir -p "$tmp/.claude/canvas"
    printf 'why: "Freelancers lose track of unpaid invoices and chase them by hand."\n' > "$tmp/.claude/canvas/purpose.yml"
    local out; out=$(_run "$tmp")
    rm -rf "$tmp"
    assert_not_contains "$out" "$MARK" "a populated purpose.yml silences it"
}

test_active_diamond_silences_it() {
    local tmp; tmp=$(mktemp -d)
    mkdir -p "$tmp/.claude/diamonds"
    printf 'active_diamonds:\n  - id: l0-purpose\n    phase: discover\n' > "$tmp/.claude/diamonds/active.yml"
    local out; out=$(_run "$tmp")
    rm -rf "$tmp"
    assert_not_contains "$out" "$MARK" "an active diamond silences it"
}

test_blank_purpose_does_not_silence_it() {
    # The gate treats a whitespace-only purpose.yml as no discovery state (2026-09-11).
    # The pre-warning reads the same function, so it must agree.
    local tmp; tmp=$(mktemp -d)
    mkdir -p "$tmp/.claude/canvas"
    printf '                    \n' > "$tmp/.claude/canvas/purpose.yml"
    local out; out=$(_run "$tmp")
    rm -rf "$tmp"
    assert_contains "$out" "$MARK" "a blank purpose.yml is not discovery state, here as at the gate"
}

DMARK="MYCELIUM DELIVERY STATE"

# v0.245.0: the discovery gate's second stage refuses new source files while no L3/L4/L5 is open,
# so the same prompt hook warns once discovery is engaged and no delivery diamond exists.
test_engaged_without_delivery_diamond_is_warned() {
    local tmp; tmp=$(mktemp -d)
    mkdir -p "$tmp/.claude/diamonds"
    printf 'active_diamonds:\n  - id: dia-001\n    scale: L0\n    phase: discover\n' > "$tmp/.claude/diamonds/active.yml"
    local out; out=$(_run "$tmp")
    rm -rf "$tmp"
    assert_contains "$out" "$DMARK" "L0 only: the delivery pre-warning is emitted"
    assert_not_contains "$out" "$MARK" "and not the discovery one, which is satisfied"
}

test_open_l3_silences_delivery_warning() {
    local tmp; tmp=$(mktemp -d)
    mkdir -p "$tmp/.claude/diamonds"
    printf 'active_diamonds:\n  - id: dia-001\n    scale: L0\n    phase: discover\n  - id: d-003\n    scale: L3\n    phase: discover\n' > "$tmp/.claude/diamonds/active.yml"
    local out; out=$(_run "$tmp")
    rm -rf "$tmp"
    assert_not_contains "$out" "$DMARK" "an L3 silences the delivery pre-warning"
}

test_delivery_ack_silences_delivery_warning() {
    local tmp; tmp=$(mktemp -d)
    mkdir -p "$tmp/.claude/diamonds" "$tmp/.claude/state"
    printf 'active_diamonds:\n  - id: dia-001\n    scale: L0\n    phase: discover\n' > "$tmp/.claude/diamonds/active.yml"
    printf '2026-09-24 user: "do not track this"\n' > "$tmp/.claude/state/delivery-skip-ack"
    local out; out=$(_run "$tmp")
    rm -rf "$tmp"
    assert_not_contains "$out" "$DMARK" "the user's recorded delivery skip silences it"
}

run_test test_empty_project_is_warned
run_test test_skip_ack_silences_it
run_test test_populated_purpose_silences_it
run_test test_active_diamond_silences_it
run_test test_blank_purpose_does_not_silence_it
run_test test_engaged_without_delivery_diamond_is_warned
run_test test_open_l3_silences_delivery_warning
run_test test_delivery_ack_silences_delivery_warning

report
