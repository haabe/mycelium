#!/usr/bin/env bash
# tests/bash/test_provision_skills_guards.sh
# G-V12 coverage proof for the two fail-closed guards in provision-skills.sh.
#
# GUARD 1 (non-git project root) is a DATA-LOSS guard, not a convenience check.
# opencode resolves its project directory by walking UP from the working
# directory; from a directory with no marker it adopts an ancestor repo, so
# Mycelium's writes land in the wrong repository. Recorded as opp-009 in the
# dogfood project, where the anchor fix lived only in a dogfood-local runner and
# never shipped to consumers. These tests are what keep it shipped.
#
# GUARD 2 (vendoring into the Mycelium checkout) covers the documented-path bug:
# the setup docs said `git clone … && cd mycelium` then `provision-skills.sh .`
# with the comment "'.' = your project root" — after the cd, '.' IS the clone.
#
# The escape-hatch test matters as much as the refusal tests: a fail-closed guard
# with no named way through becomes a guard people work around by deleting it.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PROVISION="$REPO_ROOT/plugins/mycelium/integrations/opencode/provision-skills.sh"

test_guard1_refuses_non_git_project_root() {
    local tmp out rc
    tmp="$(mktemp -d)"
    out="$(bash "$PROVISION" "$tmp" 2>&1)"; rc=$?
    rm -rf "$tmp"

    assert_eq "$rc" "1" "exits non-zero on a non-git project root"
    assert_contains "$out" "not a git root" "names the actual condition"
    assert_contains "$out" "git init" "gives the one-command fix"
    assert_contains "$out" "wrong repo" "explains the consequence, not just the rule"
}

test_guard1_names_an_escape_hatch() {
    local tmp out
    tmp="$(mktemp -d)"
    out="$(bash "$PROVISION" "$tmp" 2>&1)"
    rm -rf "$tmp"

    # A fail-closed guard must surface its own bypass, or users route around it
    # by deleting the check (Theory-X drift per theory-tensions.md Tension 7).
    assert_contains "$out" "MYCELIUM_ALLOW_NONGIT_ROOT" "surfaces the named escape hatch"
}

test_guard1_passes_on_a_real_git_root() {
    local tmp out rc
    tmp="$(mktemp -d)"
    (cd "$tmp" && git init -q 2>/dev/null)
    out="$(bash "$PROVISION" "$tmp" 2>&1)"; rc=$?
    rm -rf "$tmp"

    assert_not_contains "$out" "not a git root" "does not fire on a genuine git root"
    # NOTE argument order: assert_eq is (actual, expected).
    assert_eq "$rc" "0" "provisioning succeeds into a git-rooted project"
}

# REGRESSION — the success path was the failure path.
#
# `RESIDUAL=$(grep ... | wc -l | tr -d ' ')` ran under `set -euo pipefail`. grep
# exits 1 when it finds NOTHING, and finding nothing is the SUCCESS case here
# (every ${CLAUDE_PLUGIN_ROOT} reference rewritten). pipefail propagated that
# into the assignment and `set -e` killed the script — so a perfect run aborted
# at exit 1 with no message, while a run that left residuals behind completed
# and printed "Done." /mycelium:setup Step 5 invokes this script, so setup
# reported failure on a flawless provisioning.
#
# It shipped this way and stayed invisible because nothing had ever run the
# script against a clean project root. This test is that run.
test_clean_provisioning_exits_zero_and_reports_done() {
    local tmp out rc
    tmp="$(mktemp -d)"
    (cd "$tmp" && git init -q 2>/dev/null)
    out="$(bash "$PROVISION" "$tmp" 2>&1)"; rc=$?
    rm -rf "$tmp"

    assert_eq "$rc" "0" "a CLEAN run (zero residual refs) exits 0, not 1"
    assert_contains "$out" "Done." "reaches its final report instead of dying silently"
    assert_contains "$out" "vendored:" "prints the vendored-skill count it exists to report"
    assert_not_contains "$out" "WARNING:" "a clean run reports no residual warning"
}

test_guard2_refuses_the_mycelium_checkout_itself() {
    local out rc
    out="$(bash "$PROVISION" "$REPO_ROOT" 2>&1)"; rc=$?

    assert_eq "$rc" "1" "exits non-zero when target is the Mycelium checkout"
    assert_contains "$out" "Mycelium checkout itself" "names what it detected"
    assert_contains "$out" "vendor Mycelium into Mycelium" "explains the failure it prevents"
}

echo "=== test_provision_skills_guards: opencode consumer-path fail-closed guards ==="
run_test test_guard1_refuses_non_git_project_root
run_test test_guard1_names_an_escape_hatch
run_test test_guard1_passes_on_a_real_git_root
run_test test_clean_provisioning_exits_zero_and_reports_done
run_test test_guard2_refuses_the_mycelium_checkout_itself
report
