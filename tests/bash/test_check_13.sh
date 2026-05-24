#!/usr/bin/env bash
# G-V12 coverage proof for Check 13: theory count vs README "NN+ frameworks" claim.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_13"
# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local out
    out=$(check_theory_count 2>&1)
    cd "$REPO_ROOT"
    echo "$out"
}

test_handles_stub() {
    local output; output=$(capture "stub")
    assert_contains "$output" "Phase 1 stub" "recognizes stub doc"
    assert_contains "$output" "30+" "names the README claim"
}
test_flags_missing_doc() {
    local output; output=$(capture "missing_doc")
    assert_contains "$output" "FAIL" "flags missing theories doc"
    assert_contains "$output" "not found" "explains the gap"
}

echo "=== test_check_13: Check 13 (theory count) ==="
run_test test_handles_stub
run_test test_flags_missing_doc
report
