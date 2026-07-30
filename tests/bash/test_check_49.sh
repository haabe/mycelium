#!/usr/bin/env bash
# tests/bash/test_check_49.sh
# G-V12 coverage proof for Check 49: receipts case frontmatter carries a
# canonical contributor.
#
# Fixtured on the real drift that motivated the check: 26 cases held 15 distinct
# spellings for 8 people, the founder alone appearing 7 ways, because every
# variant appended session context inside parentheses. The values were
# informative and ungroupable at the same time, and by-contributor.md silently
# under-listed contributors for two months as a result.
#
# The `canonical` fixture guards the other direction: context is not the enemy.
# A case that keeps its context in `contributor_note` must PASS, or the check
# would push people to delete information to satisfy it.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_49"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1" || return 1
    local out
    out=$(check_receipt_contributor_canonical 2>&1)
    cd "$REPO_ROOT" || return 1
    printf '%s' "$out"
}

test_check_49_passes_on_canonical() {
    local output; output=$(capture canonical)
    assert_contains "$output" "PASS: Check 49" "canonical contributor + note passes"
}

test_check_49_flags_parenthetical() {
    local output; output=$(capture parenthetical)
    assert_contains "$output" "FAIL: Check 49" "parenthetical contributor is flagged"
    assert_contains "$output" "contributor_note" "the failure names the fix"
}

test_check_49_flags_missing_field() {
    local output; output=$(capture missing_field)
    assert_contains "$output" "FAIL: Check 49" "missing contributor field is flagged"
}

test_check_49_passes_on_canonical
test_check_49_flags_parenthetical
test_check_49_flags_missing_field

report
