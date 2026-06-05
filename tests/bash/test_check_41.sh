#!/usr/bin/env bash
# tests/bash/test_check_41.sh
# G-V12 coverage proof for Check 41: Read-before-Recommend preamble on
# gate-narrating skills (anti-pattern #7 graduation v0.39.16).
#
# Fixture covers diamond-assess only; diamond-progress takes the same
# path and would add no test signal. Both surface skills in the check's
# hardcoded list; one fixture demonstrates the pass/fail contract.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_41"

# shellcheck disable=SC1091  # path is resolved at runtime
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

reset_counters() {
    PASS=0
    FAIL=0
    WARN=0
}

capture_check_41() {
    local fixture_subdir="$1"
    cd "$FIXTURES_DIR/$fixture_subdir"
    reset_counters
    # SKILLS_DIR is computed in validate-template.sh's preamble — override
    # to point at the fixture's plugin skills tree for this invocation.
    local prev_skills_dir="${SKILLS_DIR:-}"
    SKILLS_DIR="$FIXTURES_DIR/$fixture_subdir/plugins/mycelium/skills"
    local out
    out=$(check_read_before_recommend_preamble 2>&1)
    SKILLS_DIR="$prev_skills_dir"
    cd "$REPO_ROOT"
    echo "$out"
}

test_check_41_flags_missing() {
    local output
    output=$(capture_check_41 "missing_preamble")
    assert_contains "$output" "FAIL: Check 41" "flags the missing preamble"
    assert_contains "$output" "diamond-assess/SKILL.md" "names the offending skill file"
}

test_check_41_passes_when_present() {
    local output
    output=$(capture_check_41 "with_preamble")
    assert_contains "$output" "PASS: Check 41" "passes when the preamble is present"
    assert_not_contains "$output" "FAIL" "does not flag a failure"
}

echo "=== test_check_41: Check 41 (Read-before-Recommend preamble) ==="
run_test test_check_41_flags_missing
run_test test_check_41_passes_when_present
report
