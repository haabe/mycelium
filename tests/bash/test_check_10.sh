#!/usr/bin/env bash
# G-V12 coverage proof for Check 10: version consistency CLAUDE.md vs README.md.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_10"
# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local out
    out=$(check_version_consistency 2>&1)
    cd "$REPO_ROOT"
    echo "$out"
}

test_passes_on_match() {
    local output; output=$(capture "match")
    assert_contains "$output" "PASS" "passes when versions match"
    assert_contains "$output" "1.2.3" "names the version"
}
test_flags_mismatch() {
    local output; output=$(capture "mismatch")
    assert_contains "$output" "FAIL: Version mismatch" "flags mismatch"
    assert_contains "$output" "9.9.9" "names the conflicting README version"
}
test_passes_when_readme_omits_version() {
    local output; output=$(capture "no_readme_version")
    assert_contains "$output" "README omits version (acceptable)" "treats missing README version as acceptable"
}

echo "=== test_check_10: Check 10 (version consistency) ==="
run_test test_passes_on_match
run_test test_flags_mismatch
run_test test_passes_when_readme_omits_version
report
