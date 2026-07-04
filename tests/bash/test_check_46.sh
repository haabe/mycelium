#!/usr/bin/env bash
# tests/bash/test_check_46.sh
# G-V12 coverage proof for Check 46: install-command marketplace ref is canonical.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_46"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local out
    out=$(check_install_command_canonical 2>&1)
    cd "$REPO_ROOT"
    echo "$out"
}

test_check_46_flags_wrong_marketplace_ref() {
    local output
    output=$(capture "bad")
    assert_contains "$output" "FAIL: Check 46" "flags a non-canonical marketplace ref"
    assert_contains "$output" "haabe-mycelium" "names the canonical marketplace"
}

test_check_46_passes_canonical_ref() {
    local output
    output=$(capture "good")
    assert_contains "$output" "PASS: Check 46" "passes when the ref is canonical"
    assert_not_contains "$output" "FAIL" "does not flag the canonical ref"
}

echo "=== test_check_46: Check 46 (install-command marketplace ref) ==="
run_test test_check_46_flags_wrong_marketplace_ref
run_test test_check_46_passes_canonical_ref
report
