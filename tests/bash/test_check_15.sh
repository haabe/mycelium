#!/usr/bin/env bash
# G-V12 coverage proof for Check 15: untrusted-content wrapping convention in
# skills handling user input. Part A: curated at-risk skill list MUST acknowledge
# the wrapping convention. Part B: heuristic detector for new skills outside
# the curated list showing strong user-content-handling signals.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_15"
# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local previous_skills_dir="$SKILLS_DIR"
    SKILLS_DIR="plugins/mycelium/skills"
    local out
    out=$(check_untrusted_content_wrapping 2>&1)
    SKILLS_DIR="$previous_skills_dir"
    cd "$REPO_ROOT"
    echo "$out"
}

# Note: the check's curated list has 16 names. Any fixture with fewer than all
# 16 will WARN on the missing ones. These tests verify the WRAPPING-DETECTION
# behaviour for the present skill(s) — assertions target presence/absence of
# specific signal strings, not overall WARN count.

test_compliant_skill_recognized() {
    local output; output=$(capture "compliant")
    # The interview skill in this fixture DOES acknowledge wrapping, so it
    # should NOT appear in the "missing wrapping acknowledgment" list.
    assert_not_contains "$output" "- interview" "compliant skill not in missing list"
}

test_missing_wrapping_flagged() {
    local output; output=$(capture "missing_wrapping")
    assert_contains "$output" "lack wrapping acknowledgment" "flags missing wrapping"
    assert_contains "$output" "- interview" "names the non-compliant skill"
}

test_heuristic_candidate_surfaced() {
    local output; output=$(capture "heuristic_candidate")
    assert_contains "$output" "strong user-content-handling signal" "surfaces heuristic candidate"
    assert_contains "$output" "new_user_intake" "names the candidate skill"
}

echo "=== test_check_15: Check 15 (untrusted-content wrapping convention) ==="
run_test test_compliant_skill_recognized
run_test test_missing_wrapping_flagged
run_test test_heuristic_candidate_surfaced
report
