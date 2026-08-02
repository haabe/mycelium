#!/usr/bin/env bash
# tests/bash/test_check_52.sh
# G-V12 coverage proof for Check 52: one fact, one field name.
#
# THE DRIFT (dogfood 2026-08-02). A structural audit of the roadmap canvas found
# 44 defects, and three of them were the same failure wearing different clothes:
# ONE FACT RECORDED UNDER TWO FIELD NAMES, so a reader's answer depended on which
# field they happened to open.
#
#   * confidence — 19 opportunities carried it at `provenance.confidence`; the
#     four newest carried it at BOTH top level and provenance. opp-022 held 0.35
#     at the top and 0.3 in provenance, because a founder correction ("it is
#     still just n=1 on that") landed in one place and not the other. An agent
#     writing a decision-log entry read the wrong one and published a confidence
#     value the canvas contradicted.
#   * completion date — some tasks used `closed_at`, some `completed_at`, and a
#     staleness sweep reading only the latter reported 13 terminal tasks as
#     undated when three of them had the date under the other name.
#   * four_risks — two key shapes coexisted, `{level, evidence}` from June and
#     `{risk_level, assessment}` from August. Every structured reader saw half.
#
# WHY SCHEMA VALIDATION CANNOT CATCH THIS: both fields are individually valid,
# and the opportunities schema sets `additionalProperties: true` while declaring
# neither `id`, `status`, nor `confidence`. Every field the framework routes on
# was unvalidated, which is exactly how three conventions accumulated unnoticed.
#
# The `consistent_level` fixture guards the direction that matters most: a
# project consistently on the OLD shape is not drifting and must pass. Flagging
# it would force a migration on every existing canvas to satisfy a check about
# internal consistency — and the fastest way to kill a check is to make it demand
# work from people who have no problem.
#
# Scenario-per-guardpost:
#   good              — one location per fact, one shape        -> pass
#   conf_two_places   — top-level AND provenance confidence     -> FAIL (the real drift)
#   date_two_names    — closed_at and completed_at disagree     -> FAIL
#   mixed_shapes      — both four_risks shapes in one canvas    -> FAIL
#   consistent_level  — old shape used everywhere               -> pass (consistent, not drifted)

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_52"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1" || return 1
    local out
    out=$(check_canonical_field_location 2>&1)
    cd "$REPO_ROOT" || return 1
    printf '%s' "$out"
}

test_passes_when_each_fact_has_one_home() {
    local output; output=$(capture good)
    assert_contains "$output" "PASS: Check 52" "one location per fact passes"
}

test_fails_on_confidence_in_two_places() {
    local output; output=$(capture conf_two_places)
    assert_contains "$output" "FAIL: Check 52" "confidence at both levels fails"
    assert_contains "$output" "DISAGREE" "the failure names that the two values differ"
}

test_fails_on_two_names_for_the_completion_date() {
    local output; output=$(capture date_two_names)
    assert_contains "$output" "FAIL: Check 52" "closed_at vs completed_at disagreement fails"
    assert_contains "$output" "ht-001" "the failure names the task"
}

test_fails_on_mixed_four_risks_shapes() {
    local output; output=$(capture mixed_shapes)
    assert_contains "$output" "FAIL: Check 52" "two four_risks shapes in one canvas fails"
}

test_consistent_old_shape_is_not_drift() {
    local output; output=$(capture consistent_level)
    assert_contains "$output" "PASS: Check 52" "a canvas consistently on the old shape must pass"
}

run_test test_passes_when_each_fact_has_one_home
run_test test_fails_on_confidence_in_two_places
run_test test_fails_on_two_names_for_the_completion_date
run_test test_fails_on_mixed_four_risks_shapes
run_test test_consistent_old_shape_is_not_drift
report
