#!/usr/bin/env bash
# tests/bash/test_check_35.sh
# G-V12 coverage proof for Check 35: tests/bash/fixtures — no empty directories.
# Note: empty dirs cannot themselves be committed (that's the bug under test),
# so the failure-case fixture is materialized at test time via mkdir.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_35"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local out
    out=$(check_no_empty_fixture_dirs 2>&1)
    cd "$REPO_ROOT"
    echo "$out"
}

test_check_35_flags_empty_dir() {
    local target="$FIXTURES_DIR/has_empty_dir/tests/bash/fixtures/check_99"
    mkdir -p "$target"
    local output
    output=$(capture "has_empty_dir")
    rmdir "$target" 2>/dev/null || true
    assert_contains "$output" "FAIL: Check 35" "flags empty directory"
    assert_contains "$output" "check_99" "names the offending directory"
}

test_check_35_passes_when_gitkeep_present() {
    local output
    output=$(capture "clean")
    assert_contains "$output" "PASS: Check 35" "passes when no empty dirs"
    assert_not_contains "$output" "FAIL" "does not flag"
}

test_check_35_na_when_fixtures_dir_absent() {
    local output
    output=$(capture "no_fixtures_dir")
    assert_contains "$output" "N/A" "reports N/A when fixtures dir missing"
}

echo "=== test_check_35: Check 35 (no empty fixture dirs) ==="
run_test test_check_35_flags_empty_dir
run_test test_check_35_passes_when_gitkeep_present
run_test test_check_35_na_when_fixtures_dir_absent
report
