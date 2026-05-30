#!/usr/bin/env bash
# G-V12 coverage proof for Check 12: theory-gates.md defines gates.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_12"
# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local out
    out=$(check_gate_count 2>&1)
    cd "$REPO_ROOT"
    echo "$out"
}

test_passes_with_gates() {
    local output; output=$(capture "valid")
    assert_contains "$output" "PASS" "passes when gates defined"
    assert_contains "$output" "3 gates" "reports gate count"
}
test_flags_empty() {
    local output; output=$(capture "empty")
    assert_contains "$output" "FAIL" "flags zero gates"
    assert_contains "$output" "no gates" "explains the gap"
}
test_flags_missing() {
    local output; output=$(capture "missing")
    assert_contains "$output" "FAIL" "flags missing file"
    assert_contains "$output" "not found" "names the gap"
}
# Regression: the count must ignore "## Gate Structure"/"## Gate Definitions"
# section headings (the historical source of the phantom 15) and agree with the
# headline surfaces (plugin.json, marketplace.json, CLAUDE.md roster).
test_aligned_surfaces_pass() {
    local output; output=$(capture "aligned")
    assert_contains "$output" "PASS" "passes when surfaces agree"
    assert_contains "$output" "3 gates" "counts definitions only, not section headings"
}
test_flags_surface_mismatch() {
    local output; output=$(capture "mismatch")
    assert_contains "$output" "FAIL" "flags a surface that disagrees with the canonical count"
    assert_contains "$output" "states 5 gates but" "names the drifting surface and number"
}

echo "=== test_check_12: Check 12 (theory gate count) ==="
run_test test_passes_with_gates
run_test test_flags_empty
run_test test_flags_missing
run_test test_aligned_surfaces_pass
run_test test_flags_surface_mismatch
report
