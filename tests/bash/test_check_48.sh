#!/usr/bin/env bash
# tests/bash/test_check_48.sh
# G-V12 coverage proof for Check 48: a release that CORRECTS an earlier release
# owes a corrections.md entry.
#
# Fixtured on the real case that motivated the check: v0.57.3 -> v0.57.4 ->
# v0.57.5, where v0.57.5's own changelog heading reads "corrects v0.57.4" and
# no corrections entry was written in either repo.
#
# The `completes_only` fixture guards the deliberate narrowness: completing
# earlier work is follow-through, not a mistake, and must NOT warn — otherwise
# the check trains people to ignore it.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_48"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local out
    out=$(check_self_correcting_release_capture 2>&1)
    cd "$REPO_ROOT"
    echo "$out"
}

test_check_48_warns_on_uncaptured_correcting_release() {
    local output
    output=$(capture "uncaptured")
    assert_contains "$output" "WARN: Check 48" "warns when a correcting release has no corrections entry"
    assert_contains "$output" "v0.57.5" "names the offending release"
}

test_check_48_passes_when_captured() {
    local output
    output=$(capture "captured")
    assert_contains "$output" "PASS: Check 48" "passes when a corrections entry lands inside the window"
    # Match the emitted warning, not the section title (which contains the
    # literal string "WARN tier" and would false-positive a bare "WARN").
    assert_not_contains "$output" "WARN: Check 48" "does not warn on the captured fixture"
}

test_check_48_ignores_completes_language() {
    local output
    output=$(capture "completes_only")
    assert_contains "$output" "PASS: Check 48" "'completes' is follow-through, not a mistake — must not warn"
}

test_check_48_passes_when_no_changelog() {
    local output
    output=$(capture "no_changelog")
    assert_contains "$output" "PASS: Check 48" "a repo without a changelog has nothing to check"
}

echo "=== test_check_48: Check 48 (self-correcting release capture) ==="
run_test test_check_48_warns_on_uncaptured_correcting_release
run_test test_check_48_passes_when_captured
run_test test_check_48_ignores_completes_language
run_test test_check_48_passes_when_no_changelog
report
