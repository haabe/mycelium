#!/usr/bin/env bash
# tests/bash/test_check_28.sh
# G-V12 coverage proof for Check 28: manifest dual-source byte-match.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_28"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local out
    out=$(check_manifest_byte_match 2>&1)
    cd "$REPO_ROOT"
    echo "$out"
}

test_check_28_flags_drift() {
    local output
    output=$(capture "drift")
    assert_contains "$output" "FAIL: Manifest dual-source DRIFT" "flags byte-mismatch between legacy and canonical"
    assert_contains "$output" ".claude/manifest.yml" "names the legacy path"
    assert_contains "$output" "plugins/mycelium/manifest.yml" "names the canonical path"
}

test_check_28_passes_byte_match() {
    local output
    output=$(capture "match")
    assert_contains "$output" "PASS: Manifest dual-source byte-matches" "passes when files are byte-identical"
    assert_not_contains "$output" "FAIL" "does not flag"
}

echo "=== test_check_28: Check 28 (manifest dual-source byte-match) ==="
run_test test_check_28_flags_drift
run_test test_check_28_passes_byte_match
report
