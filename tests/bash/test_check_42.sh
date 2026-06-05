#!/usr/bin/env bash
# tests/bash/test_check_42.sh
# G-V12 coverage proof for Check 42: Postflight Verify-After-Write
# preamble on multi-field-canvas-writing skills (AP#7 Stage 2a v0.39.18).
#
# Mirrors test_check_41.sh layout. Fixture covers dora-check only;
# xai-check takes the same path and would add no test signal.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_42"

# shellcheck disable=SC1091  # path is resolved at runtime
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

reset_counters() {
    PASS=0
    FAIL=0
    WARN=0
}

capture_check_42() {
    local fixture_subdir="$1"
    cd "$FIXTURES_DIR/$fixture_subdir"
    reset_counters
    local prev_skills_dir="${SKILLS_DIR:-}"
    SKILLS_DIR="$FIXTURES_DIR/$fixture_subdir/plugins/mycelium/skills"
    local out
    out=$(check_postflight_verify_after_write_preamble 2>&1)
    SKILLS_DIR="$prev_skills_dir"
    cd "$REPO_ROOT"
    echo "$out"
}

test_check_42_flags_missing() {
    local output
    output=$(capture_check_42 "missing_preamble")
    assert_contains "$output" "FAIL: Check 42" "flags the missing preamble"
    assert_contains "$output" "dora-check/SKILL.md" "names the offending skill file"
}

test_check_42_passes_when_present() {
    local output
    output=$(capture_check_42 "with_preamble")
    assert_contains "$output" "PASS: Check 42" "passes when the preamble is present"
    assert_not_contains "$output" "FAIL" "does not flag a failure"
}

echo "=== test_check_42: Check 42 (Postflight Verify-After-Write preamble) ==="
run_test test_check_42_flags_missing
run_test test_check_42_passes_when_present
report
