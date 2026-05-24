#!/usr/bin/env bash
# tests/bash/test_check_1.sh
# G-V12 coverage proof for Check 1: YAML parsing of .claude/canvas/*.yml files.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_1"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local out
    out=$(check_yaml_parsing 2>&1)
    cd "$REPO_ROOT"
    echo "$out"
}

test_check_1_flags_broken_yaml() {
    local output
    output=$(capture "broken_yaml")
    assert_contains "$output" "FAIL: YAML parse error" "flags the parse error"
    assert_contains "$output" "broken.yml" "names the failing file"
}

test_check_1_passes_clean() {
    local output
    output=$(capture "clean")
    assert_contains "$output" "PASS: All canvas YAML files parse correctly" "passes on clean fixture"
    assert_not_contains "$output" "FAIL" "does not flag"
}

echo "=== test_check_1: Check 1 (YAML parsing) ==="
run_test test_check_1_flags_broken_yaml
run_test test_check_1_passes_clean
report
