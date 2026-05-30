#!/usr/bin/env bash
# G-V12 coverage proof for Check 16: upgrade.sh is manifest-driven.
# Asserts the check (a) passes on a compliant manifest-driven upgrade.sh,
# (b) FAILs naming the missing key, and (c) FAILs the hardcoded-dir drift
# detector when framework-directory literals are re-introduced.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_16"
# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local out
    out=$(check_upgrade_manifest_driven 2>&1)
    cd "$REPO_ROOT"
    echo "$out"
}

test_compliant_passes() {
    local output; output=$(capture "compliant")
    assert_contains "$output" "calls parse_manifest.py for all 6 required lists" "compliant upgrade.sh passes key check"
    assert_contains "$output" "no hardcoded framework-directory literals" "compliant upgrade.sh is drift-free"
    assert_not_contains "$output" "FAIL:" "compliant fixture produces no FAIL"
}

test_missing_key_fails() {
    local output; output=$(capture "missing_key")
    assert_contains "$output" "missing parse_manifest.py call for: evals_replace" "names the missing key"
}

test_hardcoded_drift_fails() {
    local output; output=$(capture "hardcoded_drift")
    assert_contains "$output" "hardcoded framework-directory literals — refactor to manifest-driven" "flags re-introduced drift"
}

echo "=== test_check_16: Check 16 (upgrade.sh manifest-driven) ==="
run_test test_compliant_passes
run_test test_missing_key_fails
run_test test_hardcoded_drift_fails
report
