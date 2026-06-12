#!/usr/bin/env bash
# tests/bash/test_check_44.sh
# G-V12 coverage proof for Check 44: hooks registration — script existence +
# cross-surface parity (consistency-check-spec.md Rule 5 per-rule promotion).
#
# The codex_drift fixture reproduces the 2026-06-12 historical instance:
# autonomous-evidence-guard.sh registered in hooks.json (v0.42.0) but absent
# from hooks.codex.json + hooks.cursor.json — Codex/Cursor surfaces had zero
# autonomous evidence-integrity enforcement (decision-log 2026-06-12).

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_44"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local out
    out=$(check_hooks_registration_parity 2>&1)
    cd "$REPO_ROOT"
    echo "$out"
}

test_check_44_passes_aligned() {
    local output
    output=$(capture "aligned")
    assert_contains "$output" "PASS: Check 44" "passes when all surfaces aligned (allowlisted codex shim divergence tolerated)"
    assert_not_contains "$output" "FAIL" "no false positive on aligned fixture"
}

test_check_44_flags_codex_drift() {
    # The historical 2026-06-12 shape: guard registered on the reference
    # surface only.
    local output
    output=$(capture "codex_drift")
    assert_contains "$output" "FAIL: Check 44" "flags cross-surface drift"
    assert_contains "$output" "hooks.codex.json missing autonomous-evidence-guard.sh" "names the codex gap"
    assert_contains "$output" "hooks.cursor.json missing autonomous-evidence-guard.sh" "names the cursor gap"
}

test_check_44_flags_missing_script() {
    local output
    output=$(capture "missing_script")
    assert_contains "$output" "FAIL: Check 44" "flags nonexistent registered script"
    assert_contains "$output" "ghost-hook.sh" "names the missing script"
    assert_contains "$output" "does not exist" "states the existence failure"
}

echo "=== test_check_44: Check 44 (hooks registration existence + parity) ==="
run_test test_check_44_passes_aligned
run_test test_check_44_flags_codex_drift
run_test test_check_44_flags_missing_script
report
