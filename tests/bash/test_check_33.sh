#!/usr/bin/env bash
# tests/bash/test_check_33.sh
# G-V12 coverage proof for Check 33: plugin tree contains no unconsented personal identifiers.
#
# Check 33 reads MYCELIUM_ATTRIBUTION_REGISTRY env var pointing at a YAML
# registry of {name, consent} entries. Names with consent=generic_only or
# consent=unknown are flagged if they appear in the public-visibility scope.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_33"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

# Capture-and-restore the env var so the test doesn't leak fixture state
# back into the rest of the runner.
PREV_REGISTRY="${MYCELIUM_ATTRIBUTION_REGISTRY:-}"

capture() {
    local scenario="$1"
    cd "$FIXTURES_DIR/$scenario"
    export MYCELIUM_ATTRIBUTION_REGISTRY="$PWD/registry.yml"
    local out
    out=$(check_plugin_identifier_leak 2>&1)
    cd "$REPO_ROOT"
    if [ -z "$PREV_REGISTRY" ]; then
        unset MYCELIUM_ATTRIBUTION_REGISTRY
    else
        export MYCELIUM_ATTRIBUTION_REGISTRY="$PREV_REGISTRY"
    fi
    echo "$out"
}

test_check_33_flags_leak() {
    local output
    output=$(capture "leak")
    assert_contains "$output" "FAIL: Check 33" "flags the leak"
    assert_contains "$output" "FixtureTestPersonA" "names the leaked identifier"
    assert_contains "$output" "leak" "labels the finding as a leak"
}

test_check_33_passes_clean() {
    local output
    output=$(capture "clean")
    assert_contains "$output" "PASS: Check 33" "passes when no flagged identifiers appear in scope"
    assert_not_contains "$output" "FAIL" "does not flag"
}

echo "=== test_check_33: Check 33 (named-attribution leak detection) ==="
run_test test_check_33_flags_leak
run_test test_check_33_passes_clean
report
