#!/usr/bin/env bash
# G-V12 coverage proof for Checks 2, 3, 4 (deprecated 2026-05-08 with docs split).
# All three now return a deprecation-pass message; this test asserts the
# deprecation behaviour is intact so a future refactor doesn't accidentally
# reanimate the old logic without a corresponding test rewrite.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

# These checks have no file/state dependencies post-deprecation — they're
# pure pass-emitters. Run them from REPO_ROOT (no fixture cd needed).
test_check_2_deprecated() {
    local output; output=$(check_canvas_count_readme_body 2>&1)
    assert_contains "$output" "PASS" "Check 2 passes (deprecated)"
    assert_contains "$output" "Deprecated by 2026-05-08 docs split" "names the deprecation"
}
test_check_3_deprecated() {
    local output; output=$(check_canvas_count_readme_dir 2>&1)
    assert_contains "$output" "PASS" "Check 3 passes (deprecated)"
    assert_contains "$output" "Deprecated by 2026-05-08 docs split" "names the deprecation"
}
test_check_4_deprecated() {
    local output; output=$(check_canvas_in_readme_table 2>&1)
    assert_contains "$output" "PASS" "Check 4 passes (deprecated)"
    assert_contains "$output" "Deprecated by 2026-05-08 docs split" "names the deprecation"
}

echo "=== test_check_2_3_4_deprecated: Checks 2, 3, 4 (deprecated by 2026-05-08 docs split) ==="
run_test test_check_2_deprecated
run_test test_check_3_deprecated
run_test test_check_4_deprecated
report
