#!/usr/bin/env bash
# tests/bash/test_check_40.sh
# G-V12 coverage proof for Check 40: docs/ai-system-card.md + cross-file
# mechanical tokens in sync via sync_derived.py --check.
#
# Fixture strategy: stub sync_derived.py in place rather than replicate
# the full CLAUDE.md + plugin.json + 49 SKILL.md environment the real
# script reads. The wrapper check is what's under test; the real
# script's drift-detection logic is exercised by direct invocation
# in CI (Check 40 itself, against the live repo).

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_40"

# shellcheck disable=SC1091  # path is resolved at runtime
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

reset_counters() {
    PASS=0
    FAIL=0
    WARN=0
}

capture_check_40() {
    local fixture_subdir="$1"
    cd "$FIXTURES_DIR/$fixture_subdir"
    reset_counters
    local out
    out=$(check_sync_derived_drift 2>&1)
    cd "$REPO_ROOT"
    echo "$out"
}

test_check_40_flags_drift() {
    local output
    output=$(capture_check_40 "drift")
    assert_contains "$output" "FAIL: Check 40: sync_derived --check reports drift" "flags the drift in the output"
    assert_contains "$output" "DRIFT" "surfaces the script's own drift message"
    assert_contains "$output" "python3 plugins/mycelium/scripts/sync_derived.py" "names the remediation command"
}

test_check_40_passes_synced() {
    local output
    output=$(capture_check_40 "synced")
    assert_contains "$output" "PASS: Check 40: mechanical tokens in sync" "passes when sync_derived reports no drift"
    assert_not_contains "$output" "FAIL" "does not flag a failure"
}

echo "=== test_check_40: Check 40 (sync_derived --check pre-push gate) ==="
run_test test_check_40_flags_drift
run_test test_check_40_passes_synced
report
