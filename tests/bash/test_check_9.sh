#!/usr/bin/env bash
# G-V12 coverage proof for Check 9: skills auto-discoverable from CLAUDE.md.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_9"
# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local previous_skills_dir="$SKILLS_DIR"
    SKILLS_DIR="plugins/mycelium/skills"
    local previous_form="$SKILLS_FORM"
    SKILLS_FORM="plugin"
    local out
    out=$(check_skills_in_claude_md 2>&1)
    SKILLS_DIR="$previous_skills_dir"
    SKILLS_FORM="$previous_form"
    cd "$REPO_ROOT"
    echo "$out"
}

test_passes_auto_discovered() {
    local output; output=$(capture "auto_discovered")
    assert_contains "$output" "PASS" "passes when auto-discovered + path reference present"
    assert_not_contains "$output" "FAIL" "no failure"
}
test_flags_missing_path_reference() {
    local output; output=$(capture "missing_path")
    assert_contains "$output" "FAIL" "flags missing path reference"
    assert_contains "$output" "auto-discovered" "explains the gap"
}

echo "=== test_check_9: Check 9 (skills discoverable from CLAUDE.md) ==="
run_test test_passes_auto_discovered
run_test test_flags_missing_path_reference
report
