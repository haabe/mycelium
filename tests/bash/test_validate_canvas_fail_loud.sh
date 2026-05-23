#!/usr/bin/env bash
# tests/bash/test_validate_canvas_fail_loud.sh
# G-V12 coverage proof for validate_canvas.py fail-loud refactor (2026-05-23).
#
# Closes cluster instance 14 of documented-rule-diverges-from-enforcement
# (validator-tolerance-vs-parser-strictness): validate_canvas.py previously
# returned PASS on canvas files with YAML parse errors when those files had
# no schema (silent-skip at schema layer + warn-then-continue at trace walk).
# Refactor adds validate_all_yaml_parses() at top of main(); this test
# asserts the new behavior.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/validate_canvas_fail_loud"
VALIDATOR="$REPO_ROOT/plugins/mycelium/scripts/validate_canvas.py"

# Invoke the validator against a fixture canvas dir, capture exit code + output.
run_validator() {
    local fixture="$1"
    python3 "$VALIDATOR" "$FIXTURES_DIR/$fixture/canvas" 2>&1
}

test_fails_loud_on_broken_yaml() {
    local output
    output=$(run_validator "broken_yaml")
    local exit_code=$?
    assert_contains "$output" "YAML parse error in broken.yml" "names the failing file"
    assert_contains "$output" "Canvas validation failed" "reports validation failure"
    # Exit code captured via $? — direct comparison
    if [ "$exit_code" -eq 1 ]; then
        _ASSERT_PASSED=$((_ASSERT_PASSED + 1))
        echo "    ✓ ${_ASSERT_CURRENT}: exits 1 on broken YAML"
    else
        _ASSERT_FAILED=$((_ASSERT_FAILED + 1))
        echo "    ✗ ${_ASSERT_CURRENT}: expected exit 1, got $exit_code"
    fi
}

test_passes_on_clean_yaml() {
    local output
    output=$(run_validator "clean")
    local exit_code=$?
    assert_contains "$output" "Canvas validation: PASS" "reports PASS on clean fixture"
    assert_not_contains "$output" "YAML parse error" "does not flag clean YAML"
    if [ "$exit_code" -eq 0 ]; then
        _ASSERT_PASSED=$((_ASSERT_PASSED + 1))
        echo "    ✓ ${_ASSERT_CURRENT}: exits 0 on clean YAML"
    else
        _ASSERT_FAILED=$((_ASSERT_FAILED + 1))
        echo "    ✗ ${_ASSERT_CURRENT}: expected exit 0, got $exit_code"
    fi
}

echo "=== test_validate_canvas_fail_loud: instance 14 fix coverage ==="
run_test test_fails_loud_on_broken_yaml
run_test test_passes_on_clean_yaml
report
