#!/usr/bin/env bash
# tests/bash/test_check_30.sh
# G-V12 coverage proof for Check 30: plugin.json#version tracks CLAUDE.md Version line.
#
# This is the worked example for the bash-check fixture-testing convention
# established 2026-05-23. See tests/bash/README.md for convention.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_30"

# Source the validator to load helpers + check_* functions.
# The sourcing guard (added 2026-05-23) prevents the "run all checks" block
# from executing on source. set +e because the validator uses set -euo
# pipefail which would propagate to the test runner; the test functions
# manage their own error state via assert_* helpers.
# shellcheck disable=SC1091  # path is resolved at runtime
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

# Reset the validator's global counters between invocations so each test
# observes only its own check results.
reset_counters() {
    PASS=0
    FAIL=0
    WARN=0
}

# Capture both stdout and the post-check counter state to verify behaviour.
capture_check_30() {
    local fixture_subdir="$1"
    cd "$FIXTURES_DIR/$fixture_subdir"
    reset_counters
    local out
    out=$(check_plugin_json_version_sync 2>&1)
    cd "$REPO_ROOT"
    echo "$out"
}

test_check_30_flags_drift() {
    # Counter assertions intentionally omitted: command substitution runs
    # the check in a subshell, so global counter mutations don't survive.
    # The stdout assertions are sufficient — "FAIL: <message>" only appears
    # if the validator's `fail` helper was called.
    local output
    output=$(capture_check_30 "version_drift")
    assert_contains "$output" "FAIL: Version drift" "flags the drift in the output"
    assert_contains "$output" "CLAUDE.md=0.99.99" "names the CLAUDE.md version"
    assert_contains "$output" "plugin.json=0.0.0" "names the plugin.json version"
}

test_check_30_passes_synced() {
    local output
    output=$(capture_check_30 "version_synced")
    assert_contains "$output" "PASS: plugin.json#version matches CLAUDE.md" "passes when versions match"
    assert_not_contains "$output" "FAIL" "does not flag a failure"
}

echo "=== test_check_30: Check 30 (plugin.json version sync) ==="
run_test test_check_30_flags_drift
run_test test_check_30_passes_synced
report
