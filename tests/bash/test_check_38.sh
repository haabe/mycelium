#!/usr/bin/env bash
# tests/bash/test_check_38.sh
# G-V12 coverage proof for Check 38: cycle_class discipline — product-leaf cycles must carry a recorded ICE.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_38"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    local fixture="$1"
    (
        cd "$FIXTURES_DIR/$fixture" || exit 1
        check_cycle_class_ice_required 2>&1
    )
}

test_check_38_fails_on_product_leaf_zero_ice() {
    local output
    output=$(capture "violation")
    assert_contains "$output" "FAIL: Check 38" "flags product-leaf with zero ICE"
    assert_contains "$output" "cycle-001" "names the offending cycle"
    assert_contains "$output" "reconstructed_post_hoc" "points at the backfill escape hatch"
}

test_check_38_passes_when_product_leaf_carries_ice() {
    local output
    output=$(capture "ok")
    assert_contains "$output" "PASS: Check 38" "passes when product-leaf has non-zero ICE"
    assert_not_contains "$output" "FAIL" "does not flag meta-dogfood cycles with zero ICE"
}

test_check_38_reads_a_total_under_one_and_a_zero_impact_total_as_recorded() {
    # 0.319.0. With ICE as Gilad's product and his Confidence Meter, 3 x 0.1 x 2 = 0.6 is an
    # ordinary early score, and an Impact of 0 totals 0. Until 0.318.x both were truncated or
    # read as "zero ICE" and failed.
    local output
    output=$(capture "scored_low")
    assert_contains "$output" "PASS: Check 38" "a total under 1 and a zero-Impact total are scores"
    assert_not_contains "$output" "FAIL" "neither is reported as an unscored cycle"
}

test_check_38_still_fails_factors_without_a_total() {
    # The 0.319.0 definition is narrow on purpose: a block with no `total` key was
    # not a recorded score before it and is not one after it.
    local output
    output=$(capture "no_total")
    assert_contains "$output" "FAIL: Check 38" "factors with no total are not a recorded score"
    assert_contains "$output" "cycle-001" "names the offending cycle"
}

test_check_38_warns_on_unclassed_cycles() {
    local output
    output=$(capture "unclassed")
    assert_contains "$output" "WARN: Check 38" "warns when cycle_class is missing"
    assert_contains "$output" "cycle-001" "names the unclassed cycle"
    assert_not_contains "$output" "FAIL" "missing class is WARN not FAIL (legacy data)"
}

test_check_38_passes_on_meta_only_history() {
    local output
    output=$(capture "meta_only")
    assert_contains "$output" "PASS: Check 38" "passes when all cycles are meta-dogfood/observation"
    assert_not_contains "$output" "FAIL" "does not require ICE for non-product-leaf classes"
}

echo "=== test_check_38: Check 38 (cycle_class ICE discipline) ==="
run_test test_check_38_fails_on_product_leaf_zero_ice
run_test test_check_38_passes_when_product_leaf_carries_ice
run_test test_check_38_reads_a_total_under_one_and_a_zero_impact_total_as_recorded
run_test test_check_38_still_fails_factors_without_a_total
run_test test_check_38_warns_on_unclassed_cycles
run_test test_check_38_passes_on_meta_only_history
report
