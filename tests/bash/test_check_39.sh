#!/usr/bin/env bash
# tests/bash/test_check_39.sh
# G-V12 coverage proof for Check 39: rendering-spec docs carry STRICT or illustrative marker (Rule 4).

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_39"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    local fixture="$1"
    (
        cd "$FIXTURES_DIR/$fixture" || exit 1
        check_rendering_spec_strict_marker 2>&1
    )
}

test_check_39_passes_on_strict_marker() {
    local output
    output=$(capture "compliant_strict")
    assert_contains "$output" "PASS: Check 39" "passes when STRICT marker present"
    assert_not_contains "$output" "FAIL" "does not flag compliant doc"
}

test_check_39_passes_on_illustrative_disclaimer() {
    local output
    output=$(capture "compliant_illustrative")
    assert_contains "$output" "PASS: Check 39" "accepts illustrative disclaimer as alternative"
    assert_not_contains "$output" "FAIL" "does not flag illustrative doc"
}

test_check_39_fails_on_missing_marker() {
    local output
    output=$(capture "violation")
    assert_contains "$output" "FAIL: Check 39" "flags doc with Template+Render but no marker"
    assert_contains "$output" "rendering.md" "names the offending doc"
    assert_contains "$output" "Rule 4" "cites the spec rule"
}

test_check_39_skips_out_of_scope_docs() {
    local output
    output=$(capture "out_of_scope")
    # The out_of_scope fixture has "rendering" / "renderer" but no "Template" — should be N/A
    assert_contains "$output" "no rendering-spec docs in scope" "treats non-template docs as out of scope"
    assert_not_contains "$output" "FAIL" "does not false-positive on general docs"
}

echo "=== test_check_39: Check 39 (rendering-spec STRICT marker) ==="
run_test test_check_39_passes_on_strict_marker
run_test test_check_39_passes_on_illustrative_disclaimer
run_test test_check_39_fails_on_missing_marker
run_test test_check_39_skips_out_of_scope_docs
report
