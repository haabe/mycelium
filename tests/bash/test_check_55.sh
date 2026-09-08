#!/usr/bin/env bash
# tests/bash/test_check_55.sh
# G-V12 coverage proof for Check 55: next-action rule + Stop hook + manifests agree.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_55"
# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local out
    out=$(check_next_action_wiring 2>&1)
    cd "$REPO_ROOT"
    echo "$out"
}

test_check_55_passes_when_all_three_agree() {
    local output; output=$(capture "good")
    assert_contains "$output" "PASS: Check 55" "passes when rule, blocking hook and all three manifests agree"
    assert_not_contains "$output" "FAIL" "does not flag the good fixture"
}

test_check_55_flags_unregistered_hook() {
    local output; output=$(capture "bad")
    assert_contains "$output" "FAIL: Check 55" "flags a hook that exists and is not registered (built, not wired)"
    assert_contains "$output" "hooks.json" "names the manifest that lacks it"
}

echo "=== test_check_55: Check 55 (next-action wiring) ==="
run_test test_check_55_passes_when_all_three_agree
run_test test_check_55_flags_unregistered_hook
report
