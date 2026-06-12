#!/usr/bin/env bash
# tests/bash/test_check_45.sh
# G-V12 coverage proof for Check 45: chat-UX axiom markers on graduated
# output templates (framework-health 4e graduation, 2026-06-05 + 2026-06-12).

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_45"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local out
    out=$(check_chat_ux_axiom_markers 2>&1)
    cd "$REPO_ROOT"
    echo "$out"
}

test_check_45_passes_compliant() {
    local output
    output=$(capture "compliant")
    assert_contains "$output" "PASS: Check 45" "passes when markers present (absent skills skipped)"
    assert_not_contains "$output" "FAIL" "no false positive on compliant fixture"
}

test_check_45_flags_missing_markers() {
    local output
    output=$(capture "missing_marker")
    assert_contains "$output" "FAIL: Check 45" "flags missing axiom markers"
    assert_contains "$output" "ice-score/SKILL.md" "names the Hick offender"
    assert_contains "$output" "bvssh-check/SKILL.md" "names the Von Restorff offender"
    assert_contains "$output" "Lead with the verdict" "states the expected marker"
}

echo "=== test_check_45: Check 45 (chat-UX axiom markers) ==="
run_test test_check_45_passes_compliant
run_test test_check_45_flags_missing_markers
report
