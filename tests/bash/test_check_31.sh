#!/usr/bin/env bash
# tests/bash/test_check_31.sh
# G-V12 coverage proof for Check 31: canvas-write Preflight presence in SKILL.md files.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_31"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

# Note: SKILLS_DIR is a global set during validator sourcing based on which
# skills tree exists in the real repo. The check function reads from
# SKILLS_DIR directly, so we must override it per-fixture to point at the
# fixture's skills tree.
capture() {
    cd "$FIXTURES_DIR/$1"
    local previous_skills_dir="$SKILLS_DIR"
    SKILLS_DIR="plugins/mycelium/skills"
    local out
    out=$(check_canvas_write_preflight 2>&1)
    SKILLS_DIR="$previous_skills_dir"
    cd "$REPO_ROOT"
    echo "$out"
}

test_check_31_flags_missing_preflight() {
    local output
    output=$(capture "missing_preflight")
    assert_contains "$output" "WARN" "issues a warning"
    assert_contains "$output" "missing Preflight" "names the gap"
    assert_contains "$output" "badskill" "names the offending skill"
}

test_check_31_passes_when_present() {
    local output
    output=$(capture "present")
    assert_contains "$output" "PASS" "passes when Preflight block is present"
    assert_not_contains "$output" "WARN" "does not warn"
}

echo "=== test_check_31: Check 31 (canvas-write Preflight presence) ==="
run_test test_check_31_flags_missing_preflight
run_test test_check_31_passes_when_present
report
