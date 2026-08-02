#!/usr/bin/env bash
# tests/bash/test_check_51.sh
# G-V12 coverage proof for Check 51: shipped-delivery evidence has a delivery diamond.
#
# THE DRIFT (dogfood 2026-08-02). The dogfood repo's dora-metrics.yml was fully
# populated and classified ELITE — roughly four deploys a day, lead time in
# minutes, 0% strict change-failure rate, 5-10 minute restore — alongside 11
# launched cycles and 71 plugin releases. Its active.yml held two diamonds: L0
# and L1. No L2, no L3, no L4.
#
# So the canvas reported a project stuck in discovery while the product shipped
# continuously at the top DORA band. "Stuck since May" was true of the canvas and
# false of the work. It went unnoticed for months because nothing compared the
# two records, and the founder read the canvas as the state of his product.
#
# WHY THIS IS NOT A DOGFOOD CURIOSITY: every brownfield adoption produces the
# same shape. `/mycelium:adopt` exists precisely for "the code came first" — a
# repo with years of delivery history, tests and CI gets a fresh canvas that can
# only speak about L0/L1. Without this check the framework tells a shipping team
# it has not started, which is both wrong and the fastest way to lose them.
#
# DIRECTION MATTERS, and the `early_delivery` fixture guards it: delivery
# evidence WITHOUT a delivery diamond is the defect. A delivery diamond without
# metrics yet is simply early and must pass, or the check would punish spawning
# the diamond first — the exact behaviour it wants to encourage.
#
# Scenario-per-guardpost:
#   good                 — elite DORA + an L4 diamond            -> pass
#   missing_diamond      — elite DORA, only L0/L1                -> FAIL (the real drift)
#   launched_no_diamond  — launched cycles, only L0/L1           -> FAIL (second evidence path)
#   greenfield           — no delivery evidence at all           -> pass (nothing to reconcile)
#   early_delivery       — L4 diamond, no metrics yet            -> pass (early, not wrong)

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_51"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1" || return 1
    local out
    out=$(check_delivery_diamond_reconciliation 2>&1)
    cd "$REPO_ROOT" || return 1
    printf '%s' "$out"
}

test_passes_when_reconciled() {
    local output; output=$(capture good)
    assert_contains "$output" "PASS: Check 51" "elite DORA with an L4 diamond reconciles"
}

test_fails_on_dora_without_delivery_diamond() {
    local output; output=$(capture missing_diamond)
    assert_contains "$output" "FAIL: Check 51" "elite DORA with only L0/L1 fails"
    assert_contains "$output" "overall_classification" "the failure names the evidence it found"
}

test_fails_on_launched_cycles_without_delivery_diamond() {
    local output; output=$(capture launched_no_diamond)
    assert_contains "$output" "FAIL: Check 51" "launched cycles with only L0/L1 fails"
}

test_greenfield_has_nothing_to_reconcile() {
    local output; output=$(capture greenfield)
    assert_contains "$output" "PASS: Check 51" "a project with no delivery evidence passes"
}

test_delivery_diamond_without_metrics_is_early_not_wrong() {
    local output; output=$(capture early_delivery)
    assert_contains "$output" "PASS: Check 51" "an L4 diamond with no metrics yet must not fail"
}

run_test test_passes_when_reconciled
run_test test_fails_on_dora_without_delivery_diamond
run_test test_fails_on_launched_cycles_without_delivery_diamond
run_test test_greenfield_has_nothing_to_reconcile
run_test test_delivery_diamond_without_metrics_is_early_not_wrong
report
