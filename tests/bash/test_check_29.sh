#!/usr/bin/env bash
# tests/bash/test_check_29.sh
# G-V12 coverage proof for Check 29: stale-state-read pattern scan.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_29"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local out
    out=$(check_stale_state_read_pattern 2>&1)
    cd "$REPO_ROOT"
    echo "$out"
}

test_check_29_flags_stale_reader() {
    local output
    output=$(capture "has_stale_reader")
    assert_contains "$output" "WARN" "issues a warning"
    assert_contains "$output" "stale_reader.py" "names the offending script"
    assert_contains "$output" "stale-state-read heuristic" "explains the pattern"
}

test_check_29_passes_clean() {
    local output
    output=$(capture "clean")
    assert_contains "$output" "PASS: No stale-state-read pattern candidates" "passes when scripts have override mechanisms"
    assert_not_contains "$output" "WARN" "does not warn"
}

echo "=== test_check_29: Check 29 (stale-state-read pattern scan) ==="
run_test test_check_29_flags_stale_reader
run_test test_check_29_passes_clean
report
