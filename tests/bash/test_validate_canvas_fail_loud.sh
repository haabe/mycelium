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

# RESOLVE AN INTERPRETER THAT CAN ACTUALLY RUN THE VALIDATOR, AND SKIP HONESTLY IF NONE CAN.
#
# These tests asserted validator BEHAVIOUR while invoking a bare `python3`. Measured
# 2026-08-31: a background `mise` upgrade replaced Python 3.12 with 3.14.7 and deleted the
# old install, so `python3` lost `jsonschema`. validate_canvas.py then exited 2 with
# "jsonschema not installed", and these tests reported "needle 'YAML parse error' not found"
# — an ENVIRONMENT problem wearing the costume of a broken validator, which sends the reader
# hunting for a defect that does not exist.
#
# requirements-ci.txt states the intended split: hooks are stdlib-only, CI deps come from
# `uv run --with-requirements`. So prefer a python3 that already has them, else uv, else SKIP
# with the reason said out loud. A skipped test that names why is honest; a failing one here
# is a lie about the code.
PYV=""
if python3 -c "import jsonschema" >/dev/null 2>&1; then
    PYV="python3"
elif command -v uv >/dev/null 2>&1 && [ -f "$REPO_ROOT/requirements-ci.txt" ]; then
    PYV="uv run --quiet --with-requirements $REPO_ROOT/requirements-ci.txt python"
else
    echo "SKIP: $(basename "${BASH_SOURCE[0]}") — no interpreter can import jsonschema, so the" >&2
    echo "  validator cannot run. This is NOT a validator failure and NOT a pass: nothing was" >&2
    echo "  checked. Install the CI deps, or make uv available." >&2
    exit 0
fi


# Invoke the validator against a fixture canvas dir, capture exit code + output.
run_validator() {
    local fixture="$1"
    $PYV "$VALIDATOR" "$FIXTURES_DIR/$fixture/canvas" 2>&1
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
