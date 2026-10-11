#!/usr/bin/env bash
# tests/bash/run.sh
# Discovery + execution for tests/bash/test_*.sh files.
# Invoked from tests/validate-template.sh Check 17 alongside pytest.
#
# Exit code: 0 if all tests pass, 1 if any test fails.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# THE SUITE DOES NOT INHERIT A REPOSITORY FROM WHOEVER STARTED IT (0.319.1). Run from a git hook
# in a worktree, every test file below inherited GIT_DIR=<main>/.git/worktrees/<name>, and the
# three that build a fixture with `git init` built it inside the CALLER'S repository (traced
# 2026-10-11: test_check_26, test_git_pre_commit_hook, test_provision_skills_guards; fixture
# commits on the caller's branch, a branch `other`, a merge left in progress). _assert.sh clears
# the same variables for a test file run on its own, and its scratch_git_init refuses to go on
# when a fixture repository is not where git looks. Until 0.319.1 nothing was cleared.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_COMMON_DIR GIT_PREFIX \
      GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_NAMESPACE
# shellcheck disable=SC2046  # a list of variable NAMES, split on purpose
unset $(git rev-parse --local-env-vars 2>/dev/null || true)

total_pass=0
total_fail=0

for test_file in test_*.sh; do
    [ -f "$test_file" ] || continue
    if bash "$test_file"; then
        total_pass=$((total_pass + 1))
    else
        total_fail=$((total_fail + 1))
    fi
done

echo ""
echo "================================================="
echo "Bash check tests: $total_pass test files passed, $total_fail test files failed"
echo "================================================="

if [ "$total_fail" -gt 0 ]; then
    exit 1
fi
exit 0
