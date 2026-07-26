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
    # Copy the fixture to scratch and drop the LIVE ruff.toml + requirements-ci.txt
    # in, rather than committing snapshots of them.
    #
    # A committed config copy DRIFTS BY CONSTRUCTION, and this one did — on the very
    # next policy edit. The fixture briefly carried its own ruff.toml (added when
    # Check 17 started requiring a declared policy); moving the pin to ruff 0.16.0
    # introduced CPY001, the snapshot lacked the new ignore, and Check 17 failed
    # INSIDE its own coverage proof. Same enumerate-vs-derive defect this release is
    # about, in the test harness. Deriving the config at run time makes the drift
    # structurally impossible instead of something to remember.
    local tmp; tmp=$(mktemp -d)
    cp -R "$FIXTURES_DIR/$1/." "$tmp/"
    [ -f "$REPO_ROOT/ruff.toml" ] && cp "$REPO_ROOT/ruff.toml" "$tmp/ruff.toml"
    [ -f "$REPO_ROOT/requirements-ci.txt" ] && cp "$REPO_ROOT/requirements-ci.txt" "$tmp/requirements-ci.txt"
    local out
    out=$(cd "$tmp" && check_code_quality 2>&1)
    rm -rf "$tmp"
    echo "$out"
}

test_clean_project_never_fails() {
    # The fixture carries its own ruff.toml (added v0.61.0) because Check 17 now
    # requires the lint policy to be DECLARED on disk and gates lint at 0 rather
    # than warning against a hand-listed file subset. A fixture without a policy
    # file is not a "clean project", it is an unconfigured one — so the fixture
    # gained the config rather than the check losing its teeth.
    local output; output=$(capture "clean_project")
    assert_not_contains "$output" "FAIL:" "clean project never produces a FAIL"
}

test_missing_policy_in_framework_repo_fails() {
    # Negative control for the policy requirement. Without it, "0 errors" is
    # ambiguous between "policy declared and met" and "no policy, so nothing was
    # measured" — the vacuous-green shape this release exists to eliminate.
    # plugins/mycelium/ present => this is the framework repo => policy required.
    local tmp; tmp=$(mktemp -d)
    mkdir -p "$tmp/plugins/mycelium"
    local out
    out=$(cd "$tmp" && check_code_quality 2>&1)
    rm -rf "$tmp"
    assert_contains "$out" "ruff.toml missing" \
        "framework repo without a declared lint policy -> FAIL, not a silent pass"
}

test_missing_policy_in_consumer_project_is_skipped() {
    # The other direction, and Check 17's standing invariant: a downstream project
    # is never blocked for a missing file. No plugins/mycelium/ => not ours to
    # police => skip, not fail.
    local tmp; tmp=$(mktemp -d)
    local out
    out=$(cd "$tmp" && check_code_quality 2>&1)
    rm -rf "$tmp"
    assert_not_contains "$out" "ruff.toml missing" \
        "consumer project without ruff.toml is not failed (Check 17 never-block invariant)"
}

test_runs_to_completion_without_recursion() {
    local output; output=$(capture "clean_project")
    # The bash-runner block must hit the missing-runner skip, proving the
    # function reached its end without re-invoking tests/bash/run.sh.
    assert_contains "$output" "tests/bash" "reaches the bash-runner skip branch"
}


test_ruff_pin_divergence_fails() {
    # NEGATIVE CONTROL for the version-match guard. select=ALL makes the ruff
    # VERSION part of the policy, so an installed-vs-pinned mismatch means two
    # environments hold two different definitions of "clean" — PR #17 shipped
    # 0 errors locally and 59 in CI for exactly this reason.
    local tmp; tmp=$(mktemp -d)
    mkdir -p "$tmp/plugins/mycelium"
    cp "$REPO_ROOT/ruff.toml" "$tmp/ruff.toml"
    printf 'ruff==9.9.9\n' > "$tmp/requirements-ci.txt"
    local out; out=$(cd "$tmp" && check_code_quality 2>&1)
    rm -rf "$tmp"
    assert_contains "$out" "ruff version divergence" \
        "installed != pinned -> FAIL (two policies, not one)"
}

test_unpinned_ruff_spec_fails_and_does_not_die_silently() {
    # THE REGRESSION THIS TEST EXISTS FOR: the first cut of the guard read the pin
    # with an unguarded `grep` under `set -euo pipefail`. A no-match grep exits 1,
    # so on an UNPINNED spec the substitution aborted check_code_quality mid-check
    # and the guard reported NOTHING — failing open on the very condition it was
    # written to detect. Assert both halves: the finding is emitted, AND the check
    # keeps running afterwards (the ruff-count line still appears).
    local tmp; tmp=$(mktemp -d)
    mkdir -p "$tmp/plugins/mycelium"
    cp "$REPO_ROOT/ruff.toml" "$tmp/ruff.toml"
    printf 'ruff>=0.1.0\n' > "$tmp/requirements-ci.txt"
    local out; out=$(cd "$tmp" && check_code_quality 2>&1)
    rm -rf "$tmp"
    assert_contains "$out" "ruff is not pinned" \
        "unbounded spec -> FAIL, not a silent abort"
    assert_contains "$out" "0 errors repo-wide" \
        "check continues past the pin finding (proves it did not die mid-check)"
}

echo "=== test_check_17: Check 17 (code-quality regression, never-block invariant) ==="
run_test test_clean_project_never_fails
run_test test_ruff_pin_divergence_fails
run_test test_unpinned_ruff_spec_fails_and_does_not_die_silently
run_test test_missing_policy_in_framework_repo_fails
run_test test_missing_policy_in_consumer_project_is_skipped
run_test test_runs_to_completion_without_recursion
report
