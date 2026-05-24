#!/usr/bin/env bash
# tests/bash/test_check_5.sh
# G-V12 coverage proof for Check 5: every canvas file appears in canvas-update SKILL.md mapping.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_5"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

# SKILLS_DIR is module-global; override per-fixture.
capture() {
    cd "$FIXTURES_DIR/$1"
    local previous_skills_dir="$SKILLS_DIR"
    SKILLS_DIR="plugins/mycelium/skills"
    local out
    out=$(check_canvas_in_update_mapping 2>&1)
    SKILLS_DIR="$previous_skills_dir"
    cd "$REPO_ROOT"
    echo "$out"
}

test_check_5_flags_missing_canvas_in_mapping() {
    local output
    output=$(capture "missing_canvas_in_mapping")
    assert_contains "$output" "orphan.yml" "names the unmapped canvas file"
    assert_contains "$output" "not in canvas-update mapping" "explains the gap"
}

test_check_5_passes_when_all_present() {
    local output
    output=$(capture "all_present")
    assert_contains "$output" "PASS" "passes when all canvas files mapped"
    assert_not_contains "$output" "WARN" "no warning"
}

test_check_5_flags_missing_mapping_file() {
    local output
    output=$(capture "missing_mapping_file")
    assert_contains "$output" "FAIL: canvas-update SKILL.md not found" "flags missing mapping file"
}

echo "=== test_check_5: Check 5 (canvas files in canvas-update mapping) ==="
run_test test_check_5_flags_missing_canvas_in_mapping
run_test test_check_5_passes_when_all_present
run_test test_check_5_flags_missing_mapping_file
report
