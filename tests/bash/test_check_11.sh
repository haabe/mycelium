#!/usr/bin/env bash
# G-V12 coverage proof for Check 11: anti-pattern count CLAUDE.md/README vs disk.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_11"
# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local out
    out=$(check_antipattern_count 2>&1)
    cd "$REPO_ROOT"
    echo "$out"
}

test_passes_on_match() {
    local output; output=$(capture "match")
    assert_contains "$output" "PASS" "passes when counts match"
    assert_not_contains "$output" "FAIL" "no failure"
}
test_flags_mismatch() {
    local output; output=$(capture "mismatch")
    assert_contains "$output" "FAIL" "flags count mismatch"
}
test_handles_omitted_count() {
    local output; output=$(capture "no_readme_count")
    assert_contains "$output" "not in README" "treats omitted README count as acceptable"
    assert_contains "$output" "3" "still reports disk count"
}

echo "=== test_check_11: Check 11 (anti-pattern count) ==="
run_test test_passes_on_match
run_test test_flags_mismatch
run_test test_handles_omitted_count
report
