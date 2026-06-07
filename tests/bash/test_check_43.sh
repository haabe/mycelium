#!/usr/bin/env bash
# tests/bash/test_check_43.sh
# G-V12 coverage proof for Check 43: Identifier-exposure declaration on
# render-fleet skills (engine/render-conventions.md HARD RULE).

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_43"

# shellcheck disable=SC1091  # path is resolved at runtime
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

reset_counters() {
    PASS=0
    FAIL=0
    WARN=0
}

capture_check_43() {
    local fixture_subdir="$1"
    cd "$FIXTURES_DIR/$fixture_subdir"
    reset_counters
    local prev_skills_dir="${SKILLS_DIR:-}"
    SKILLS_DIR="$FIXTURES_DIR/$fixture_subdir/plugins/mycelium/skills"
    local out
    out=$(check_render_identifier_exposure_declaration 2>&1)
    SKILLS_DIR="$prev_skills_dir"
    cd "$REPO_ROOT"
    echo "$out"
}

test_check_43_flags_missing_frontmatter() {
    local output
    output=$(capture_check_43 "missing_frontmatter")
    assert_contains "$output" "FAIL: Check 43" "flags missing frontmatter as failure"
    assert_contains "$output" "missing 'identifier_exposure:' frontmatter" "names the specific failure mode"
    assert_contains "$output" "ost-render/SKILL.md" "names the offending skill file"
}

test_check_43_flags_invalid_value() {
    local output
    output=$(capture_check_43 "invalid_value")
    assert_contains "$output" "FAIL: Check 43" "flags invalid value as failure"
    assert_contains "$output" "invalid identifier_exposure value" "names the specific failure mode"
}

test_check_43_flags_missing_body() {
    local output
    output=$(capture_check_43 "missing_body")
    assert_contains "$output" "FAIL: Check 43" "flags missing body section as failure"
    assert_contains "$output" "missing '## Identifier exposure' body section" "names the specific failure mode"
}

test_check_43_passes_valid_yes() {
    local output
    output=$(capture_check_43 "valid_yes")
    assert_contains "$output" "PASS: Check 43" "passes when YES is properly declared"
    assert_not_contains "$output" "FAIL" "does not flag a failure"
}

test_check_43_passes_valid_none() {
    local output
    output=$(capture_check_43 "valid_none")
    assert_contains "$output" "PASS: Check 43" "passes when NONE is properly declared"
    assert_not_contains "$output" "FAIL" "does not flag a failure"
}

echo "=== test_check_43: Check 43 (identifier-exposure declaration on render skills) ==="
run_test test_check_43_flags_missing_frontmatter
run_test test_check_43_flags_invalid_value
run_test test_check_43_flags_missing_body
run_test test_check_43_passes_valid_yes
run_test test_check_43_passes_valid_none
report
