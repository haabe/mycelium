#!/usr/bin/env bash
# tests/bash/test_check_47.sh
# G-V12 coverage proof for Check 47: plugin-form operating contract is wired.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_47"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local out
    out=$(check_operating_contract_wiring 2>&1)
    cd "$REPO_ROOT"
    echo "$out"
}

test_check_47_passes_wired_contract() {
    local output
    output=$(capture "good")
    assert_contains "$output" "PASS: Check 47" "passes when contract is present, injected, referenced, and path-clean"
    assert_not_contains "$output" "FAIL" "does not flag the good fixture"
}

test_check_47_flags_legacy_framework_path() {
    local output
    output=$(capture "bad")
    assert_contains "$output" "FAIL: Check 47" "flags a legacy .claude/ framework path in the contract"
    assert_contains "$output" "legacy" "explains the legacy-path failure"
}

echo "=== test_check_47: Check 47 (operating contract wiring) ==="
run_test test_check_47_passes_wired_contract
run_test test_check_47_flags_legacy_framework_path
report
