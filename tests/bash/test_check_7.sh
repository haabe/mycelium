#!/usr/bin/env bash
# G-V12 coverage proof for Check 7: skill count in CLAUDE.md vs disk.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_7"
# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local previous_skills_dir="$SKILLS_DIR"
    SKILLS_DIR="plugins/mycelium/skills"
    local out
    out=$(check_skill_count_claude 2>&1)
    SKILLS_DIR="$previous_skills_dir"
    cd "$REPO_ROOT"
    echo "$out"
}

test_passes_on_match() {
    local output; output=$(capture "match")
    assert_contains "$output" "PASS" "passes when CLAUDE.md count matches disk"
    assert_not_contains "$output" "FAIL" "no failure"
}
test_flags_mismatch() {
    local output; output=$(capture "mismatch")
    assert_contains "$output" "FAIL" "flags count mismatch"
    assert_contains "$output" "5 skills" "names CLAUDE.md count"
}

echo "=== test_check_7: Check 7 (skill count in CLAUDE.md) ==="
run_test test_passes_on_match
run_test test_flags_mismatch
report
