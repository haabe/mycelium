#!/usr/bin/env bash
# G-V12 coverage proof for Check 17: Python + Bash code-quality regression.
#
# Check 17 is the meta-runner — it shells out to ruff, shellcheck, pytest, and
# the tests/bash runner. Its load-bearing invariant (stated in its own header)
# is that it NEVER blocks a downstream project for missing dev tools or files;
# it degrades to WARN/skip. This proof asserts that invariant on a minimal
# clean fixture: whatever subset of tools is installed, an honest clean project
# must not produce a FAIL. (Running inside the fixture dir also prevents the
# bash-runner block from re-invoking tests/bash/run.sh → no recursion.)

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_17"
# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1"
    local out
    out=$(check_code_quality 2>&1)
    cd "$REPO_ROOT"
    echo "$out"
}

test_clean_project_never_fails() {
    local output; output=$(capture "clean_project")
    assert_not_contains "$output" "FAIL:" "clean project never produces a FAIL"
}

test_runs_to_completion_without_recursion() {
    local output; output=$(capture "clean_project")
    # The bash-runner block must hit the missing-runner skip, proving the
    # function reached its end without re-invoking tests/bash/run.sh.
    assert_contains "$output" "tests/bash" "reaches the bash-runner skip branch"
}

echo "=== test_check_17: Check 17 (code-quality regression, never-block invariant) ==="
run_test test_clean_project_never_fails
run_test test_runs_to_completion_without_recursion
report
