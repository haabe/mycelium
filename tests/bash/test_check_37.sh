#!/usr/bin/env bash
# G-V12 self-application: Check 37 verifies every declared check has a fixture
# test. This proof drives the meta-check over two fixture trees — one where
# every declared check is covered (PASS) and one with a deliberate gap (FAIL
# naming the uncovered check).

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_37"
# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local out
    out=$(check_gv12_test_coverage 2>&1)
    cd "$REPO_ROOT"
    echo "$out"
}

test_full_coverage_passes() {
    local output; output=$(capture "covered")
    assert_contains "$output" "all 2 declared checks have a tests/bash fixture test" "fully-covered tree passes"
    assert_not_contains "$output" "FAIL:" "no FAIL when coverage is complete"
}

test_gap_fails_naming_check() {
    local output; output=$(capture "gap")
    assert_contains "$output" "missing a tests/bash/test_check_<N>.sh: 2" "names the uncovered check"
}

echo "=== test_check_37: Check 37 (G-V12 meta-coverage) ==="
run_test test_full_coverage_passes
run_test test_gap_fails_naming_check
report
