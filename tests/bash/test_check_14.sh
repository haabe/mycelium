#!/usr/bin/env bash
# tests/bash/test_check_14.sh
# G-V12 coverage proof for Check 14: AGENTS.md router discipline.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_14"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local out
    out=$(check_agents_md 2>&1)
    cd "$REPO_ROOT"
    echo "$out"
}

test_check_14_flags_missing_file() {
    local output
    output=$(capture "missing_file")
    assert_contains "$output" "FAIL: AGENTS.md not found" "flags absent file"
}

test_check_14_flags_missing_sections() {
    local output
    output=$(capture "missing_sections")
    assert_contains "$output" "PASS: AGENTS.md exists" "confirms file presence"
    assert_contains "$output" "FAIL: AGENTS.md missing required '## What's available'" "flags missing What's available section"
    assert_contains "$output" "FAIL: AGENTS.md missing required '## Minimal path'" "flags missing Minimal path section"
}

test_check_14_passes_valid() {
    local output
    output=$(capture "valid")
    assert_contains "$output" "PASS: AGENTS.md exists" "confirms file presence"
    assert_contains "$output" "PASS: AGENTS.md contains 'What's available'" "passes Whats available"
    assert_contains "$output" "PASS: AGENTS.md contains 'Minimal path'" "passes Minimal path"
    assert_not_contains "$output" "FAIL" "no failures"
}

echo "=== test_check_14: Check 14 (AGENTS.md router discipline) ==="
run_test test_check_14_flags_missing_file
run_test test_check_14_flags_missing_sections
run_test test_check_14_passes_valid
report
