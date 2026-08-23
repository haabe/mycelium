#!/usr/bin/env bash
# tests/bash/test_check_54.sh
# G-V12 coverage proof for Check 54: has the Promise registry been SWEPT?
#
# THE DEFECT (2026-08-23). engine/consistency-check-spec.md carries a Promise
# registry for framework prose claiming a surface does something nothing
# implements. It held four rows — all closed, all from a single 2026-06-12
# analysis — and gained nothing for ten weeks, while a rule census that same day
# found two fresh instances: a fully specified mutation-log subsystem with no
# writer, and a BLOCK-tier guardrail unmet for three of its four named scripts.
#
# THE REGISTRY DID NOT FAIL. NOTHING SWEPT IT. The sweep lives in
# /framework-health step 4f — prose in a skill, run when someone remembers — so
# the file could not distinguish "nothing to add" from "nobody looked", which are
# the two states it most needs to tell apart.
#
# WHAT THIS CHECK IS NOT. It does not verify promises are kept. Both forms of that
# were built and measured the same day and both rejected: the broad form produced
# 61 hits, nearly all consumer-repo canvas files that correctly do not ship inside
# the plugin; the narrow form produced 3 flags, all false, AND MISSED the very
# instance it was written from. A matcher that misses its own founding case is
# worse than no check.
#
# Scenario-per-guardpost:
#   fresh   — marker inside cadence                 -> ok
#   stale   — marker older than the limit           -> STALE
#   missing — no marker at all                      -> MISSING (a DIFFERENT finding:
#             absent means never adopted, stale means adopted then not honoured)
#   future  — marker dated ahead                    -> FUTURE. This is the bypass
#             path: without it, anyone can silence the check forever by typing a
#             far-off date, which is the cheapest way to turn an instrument into
#             decoration.
#   no-spec — no framework spec at all              -> PRECONDITION UNMET (exit 2).
#             NOT a pass: a check that looked at nothing and reports success is
#             indistinguishable from one that works, and reads green forever.
#
# --today is pinned throughout so no fixture decays with the calendar.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES="$SCRIPT_DIR/fixtures/check_54"
CHECK="$REPO_ROOT/plugins/mycelium/scripts/check_promise_registry_swept.py"
TODAY="2026-08-23"

run_fixture() {
    python3 "$CHECK" --root "$FIXTURES/$1" --today "$TODAY" 2>&1
}

test_fresh_is_ok() {
    local out; out=$(run_fixture fresh)
    assert_contains "$out" "ok — last swept" "a recent sweep passes"
    assert_contains "$out" "22d ago" "the age is reported, not just a verdict"
}

test_stale_is_reported() {
    local out; out=$(run_fixture stale)
    assert_contains "$out" "STALE" "an old sweep is flagged"
    assert_contains "$out" "EVEN IF" "the remedy says to update the marker even when nothing is added"
}

test_missing_marker_is_a_distinct_finding() {
    local out; out=$(run_fixture missing)
    assert_contains "$out" "MISSING" "an absent marker is flagged"
    assert_contains "$out" "nobody looked" "and it names why absence differs from staleness"
}

test_future_date_is_refused() {
    local out; out=$(run_fixture future)
    assert_contains "$out" "FUTURE" "a future date is not accepted as a sweep"
}

test_strict_exits_nonzero_on_stale() {
    python3 "$CHECK" --root "$FIXTURES/stale" --today "$TODAY" --strict >/dev/null 2>&1
    assert_eq "1" "$?" "--strict fails on a stale sweep"
}

test_advisory_default_never_fails_a_build() {
    local rc
    python3 "$CHECK" --root "$FIXTURES/stale" --today "$TODAY" >/dev/null 2>&1; rc=$?
    assert_eq "0" "$rc" "default is advisory — a consumer's build is not broken by a date they did not set"
}

test_missing_spec_is_a_precondition_failure() {
    # A MISSING SPEC and a SPEC WITH NO ROWS are different states; only the second is a
    # legitimate zero. check_empty_input_honesty flagged the first draft for exiting 0 here.
    local out rc
    out=$(python3 "$CHECK" --root "$SCRIPT_DIR" --today "$TODAY" 2>&1); rc=$?
    assert_contains "$out" "PRECONDITION UNMET" "a missing spec is not reported as a pass"
    assert_eq "2" "$rc" "precondition failure exits 2, distinct from both pass and fail"
}

run_test test_fresh_is_ok
run_test test_stale_is_reported
run_test test_missing_marker_is_a_distinct_finding
run_test test_future_date_is_refused
run_test test_strict_exits_nonzero_on_stale
run_test test_advisory_default_never_fails_a_build
run_test test_missing_spec_is_a_precondition_failure
report
