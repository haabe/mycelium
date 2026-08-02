#!/usr/bin/env bash
# tests/bash/test_check_50.sh
# G-V12 coverage proof for Check 50: theories.md claims name artifacts that exist.
#
# Fixtured on the 2026-08-02 theory-fidelity audit. docs/theories.md is the file
# that states what the framework claims to implement, and every claim ends in an
# "Implemented as:" line naming gates, skills and files. Nothing verified those
# names, and three were wrong:
#
#   - gate 10 cited as "Delivery Health" — that is a section heading in
#     jit-tooling/definition-of-done.md, not a gate. The gate is "DORA /
#     Delivery Metrics".
#   - gate 4 cited as "Domain Fit" — the gate is "Cynefin Gate". This one the
#     manual audit missed entirely; the check found it on first run.
#   - a Wardley "NUDGE at Develop->Deliver" that exists nowhere in the tree.
#
# A theory claim naming an artifact that does not exist is worse than no claim:
# it reads as evidence the theory was operationalised, and theories.md is the
# first file a skeptical reader opens.
#
# The `quoted_correction` fixture guards the direction that bit during
# authoring: a correction note QUOTES the old wrong citation, and the first
# version of the check flagged the quotation. Documenting a fix must never
# permanently re-trip the check that prompted it, or the only way to stay green
# is to stop recording corrections.
#
# SCOPE, so this is not mistaken for more: it verifies artifacts EXIST. It
# cannot verify they behave as described. The same audit found
# adaptive-thresholds.md documenting a gate removed a month earlier, and a
# fabricated Hoskins element surviving in leaf-lifecycle.md — neither is
# reachable by name-matching, and both needed a human reading the prose.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_50"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1" || return 1
    local out
    out=$(check_theory_claim_artifacts 2>&1)
    cd "$REPO_ROOT" || return 1
    printf '%s' "$out"
}

test_passes_on_correct_claims() {
    local output; output=$(capture good)
    assert_contains "$output" "PASS: Check 50" "correctly-named gates and real paths pass"
}

test_fails_on_wrong_gate_name() {
    local output; output=$(capture wrong_name)
    assert_contains "$output" "FAIL: Check 50" "a gate cited by the wrong name fails"
    assert_contains "$output" "Delivery Health" "the failure names the wrong citation"
}

test_fails_on_nonexistent_gate() {
    local output; output=$(capture missing_gate)
    assert_contains "$output" "FAIL: Check 50" "a gate number with no heading fails"
}

test_fails_on_missing_implemented_as_path() {
    local output; output=$(capture bad_path)
    assert_contains "$output" "FAIL: Check 50" "an Implemented-as path that does not resolve fails"
}

test_quoted_correction_does_not_retrip() {
    local output; output=$(capture quoted_correction)
    assert_contains "$output" "PASS: Check 50" "a correction note quoting the old wrong citation must not fail"
}

run_test test_passes_on_correct_claims
run_test test_fails_on_wrong_gate_name
run_test test_fails_on_nonexistent_gate
run_test test_fails_on_missing_implemented_as_path
run_test test_quoted_correction_does_not_retrip
report
