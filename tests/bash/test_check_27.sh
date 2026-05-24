#!/usr/bin/env bash
# G-V12 coverage proof for Check 27: skills-tree parity (plugin vs legacy).
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_27"
# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local previous_plugin="$PLUGIN_SKILLS"
    local previous_legacy="$LEGACY_SKILLS"
    PLUGIN_SKILLS="plugins/mycelium/skills"
    LEGACY_SKILLS=".claude/skills"
    local out
    out=$(check_skills_tree_parity 2>&1)
    PLUGIN_SKILLS="$previous_plugin"
    LEGACY_SKILLS="$previous_legacy"
    cd "$REPO_ROOT"
    echo "$out"
}

test_passes_match() {
    local output; output=$(capture "match")
    assert_contains "$output" "PASS" "passes when skill set matches"
    assert_not_contains "$output" "WARN" "no warnings"
}
test_flags_divergence() {
    local output; output=$(capture "diverge")
    assert_contains "$output" "WARN" "warns on divergence"
    assert_contains "$output" "skill_b" "names the plugin-only skill"
}

echo "=== test_check_27: Check 27 (skills-tree parity) ==="
run_test test_passes_match
run_test test_flags_divergence
report
