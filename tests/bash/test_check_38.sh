#!/usr/bin/env bash
# tests/bash/test_check_38.sh
# G-V12 coverage proof for Check 38: cycle_class discipline — product-leaf cycles must carry non-zero ICE.

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
run_test test_check_38_warns_on_unclassed_cycles
run_test test_check_38_passes_on_meta_only_history
report
