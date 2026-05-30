#!/usr/bin/env bash
# tests/bash/test_check_36.sh
# G-V12 coverage proof for Check 36: CLAUDE.md line-count ceiling (dispatcher-size ratchet).

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_36"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

# Run the check inside a subshell so the temporary cwd + env overrides are
# isolated from the parent shell. The function is inherited by the subshell.
capture() {
    local fixture="$1" max="$2" target="$3"
    (
        cd "$FIXTURES_DIR/$fixture" || exit 1
        export CLAUDEMD_MAX_LINES="$max" CLAUDEMD_TARGET_LINES="$target"
        check_claudemd_size_ceiling 2>&1
    )
}

test_check_36_fails_over_ceiling() {
    local output
    output=$(capture "over_ceiling" 3 2)
    assert_contains "$output" "FAIL: Check 36" "flags CLAUDE.md over the ceiling"
    assert_contains "$output" "ratchets DOWN only" "states the ratchet rule"
}

test_check_36_warns_within_ceiling_over_target() {
    local output
    output=$(capture "within_ceiling_over_target" 5 3)
    assert_contains "$output" "WARN: Check 36" "warns when within ceiling but over target"
    assert_not_contains "$output" "FAIL" "does not fail within the ceiling"
}

test_check_36_passes_under_target() {
    local output
    output=$(capture "under_target" 5 3)
    assert_contains "$output" "PASS: Check 36" "passes at or under the target"
    assert_not_contains "$output" "FAIL" "does not flag"
}

echo "=== test_check_36: Check 36 (CLAUDE.md line-count ceiling) ==="
run_test test_check_36_fails_over_ceiling
run_test test_check_36_warns_within_ceiling_over_target
run_test test_check_36_passes_under_target
report
