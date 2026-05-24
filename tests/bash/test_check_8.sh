#!/usr/bin/env bash
# G-V12 coverage proof for Check 8: skill SKILL.md frontmatter (name + description).
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_8"
# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local previous_skills_dir="$SKILLS_DIR"
    SKILLS_DIR="plugins/mycelium/skills"
    local out
    out=$(check_skill_frontmatter 2>&1)
    SKILLS_DIR="$previous_skills_dir"
    cd "$REPO_ROOT"
    echo "$out"
}

test_passes_valid() {
    local output; output=$(capture "valid")
    assert_contains "$output" "PASS" "passes valid frontmatter"
    assert_not_contains "$output" "FAIL" "no failure"
}
test_flags_missing_name() {
    local output; output=$(capture "missing_name")
    assert_contains "$output" "FAIL" "flags missing name"
    assert_contains "$output" "bad_skill" "names the skill"
    assert_contains "$output" "missing 'name:'" "explains the gap"
}
test_flags_missing_skill_md() {
    local output; output=$(capture "missing_skill_md")
    assert_contains "$output" "has no SKILL.md" "flags missing SKILL.md file"
}

echo "=== test_check_8: Check 8 (skill SKILL.md frontmatter) ==="
run_test test_passes_valid
run_test test_flags_missing_name
run_test test_flags_missing_skill_md
report
