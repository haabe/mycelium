#!/usr/bin/env bash
# tests/bash/test_check_32.sh
# G-V12 coverage proof for Check 32: Four-Risks levels required on active-diamond opportunities.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_32"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local out
    out=$(check_four_risks_when_active 2>&1)
    cd "$REPO_ROOT"
    echo "$out"
}

test_check_32_flags_missing_levels() {
    local output
    output=$(capture "missing_levels")
    assert_contains "$output" "WARN" "issues a warning"
    assert_contains "$output" "missing" "names the missing risk fields"
    assert_contains "$output" "opp-001" "names at least one affected opportunity"
}

test_check_32_passes_populated() {
    local output
    output=$(capture "populated")
    assert_contains "$output" "PASS" "passes when all four-risks levels are populated"
    assert_not_contains "$output" "missing value" "does not flag value as missing"
    assert_not_contains "$output" "missing viability" "does not flag viability as missing"
}

echo "=== test_check_32: Check 32 (Four-Risks levels on opportunities) ==="
run_test test_check_32_flags_missing_levels
run_test test_check_32_passes_populated
report
