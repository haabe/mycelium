#!/usr/bin/env bash
# tests/bash/test_check_34.sh
# G-V12 coverage proof for Check 34: CLAUDE.md contains at most one version entry.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_34"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local out
    out=$(check_claudemd_single_version_entry 2>&1)
    cd "$REPO_ROOT"
    echo "$out"
}

test_check_34_flags_two_versions() {
    local output
    output=$(capture "two_versions")
    assert_contains "$output" "FAIL: Check 34" "flags multiple version entries"
    assert_contains "$output" "2 version entries" "names the count"
}

test_check_34_passes_one_version() {
    local output
    output=$(capture "one_version")
    assert_contains "$output" "PASS: Check 34" "passes when ≤1 version entry"
    assert_not_contains "$output" "FAIL" "does not flag"
}

echo "=== test_check_34: Check 34 (CLAUDE.md single version entry) ==="
run_test test_check_34_flags_two_versions
run_test test_check_34_passes_one_version
report
