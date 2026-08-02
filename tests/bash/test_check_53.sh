#!/usr/bin/env bash
# tests/bash/test_check_53.sh
# G-V12 coverage proof for Check 53: scenarios migrated off the 4-block model.
#
# THE DEFECT (dogfood 2026-08-03). Hoskins's model has THREE elements —
# Motivation, Persona, Simulation. An in-repo model listing four, with a "Means",
# was identified as a fabrication on 2026-07-01 and cleaned from five files in
# v0.66.3. A sixth instance surfaced in leaf-lifecycle.md in v0.71.0. On
# 2026-08-03 a hand-run canvas-health found all seven scenarios in the dogfood
# repo still carrying `means` + `motive` and none carrying `motivation` — a full
# month after the correction.
#
# WHAT WAS ACTUALLY WRONG, stated precisely because the first report got it
# wrong: the schema does NOT bless these fields. It marks both as legacy, and its
# own description says "'Means' is NOT a Hoskins element; fold this into the
# simulation." Keeping them declared is a deliberate migration allowance so
# historical files keep validating. That is correct.
#
# The gap was that TOLERANCE HAD NO EXPIRY. Nothing anywhere told a project it
# was still on the old shape, so the corrected model could be documented in five
# files while the data sat unmigrated indefinitely — and did, for a month.
#
# The `archived_keeps_legacy` fixture guards the direction that would make this
# check harmful: an archived scenario is history, and rewriting history to satisfy
# a lint is worse than the lint. Migration pressure applies to live scenarios only.
#
# Scenario-per-guardpost:
#   migrated             — motivation + simulation.context      -> pass
#   legacy_motive        — `motive`, no `motivation`            -> FAIL (unmigrated)
#   legacy_means         — `means` present at all               -> FAIL (no successor field; it folds in)
#   archived_keeps_legacy— both, on status: archived            -> pass (history is exempt)
#   empty                — zero scenarios                       -> N/A (see below)
#
# The `empty` fixture changed during authoring and the reason is worth keeping.
# It first asserted FAIL, importing the empty-input rule the fitness functions
# follow — and Check 53 then failed the FRAMEWORK repo's own CI, because its
# scenarios.yml ships as an empty template. The rules are not the same: an empty
# population there means the check could not SEE what it guards; here it means
# the project has written no scenarios yet, which is a legitimate early state.
# Migration pressure applies to scenarios that exist.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_53"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1" || return 1
    local out
    out=$(check_scenario_legacy_model 2>&1)
    cd "$REPO_ROOT" || return 1
    printf '%s' "$out"
}

test_migrated_passes() {
    local output; output=$(capture migrated)
    assert_contains "$output" "PASS: Check 53" "a migrated scenario passes"
    assert_contains "$output" "Motivation/Persona/Simulation" "the pass names the three elements"
}

test_legacy_motive_fails() {
    local output; output=$(capture legacy_motive)
    assert_contains "$output" "FAIL: Check 53" "motive without motivation fails"
    assert_contains "$output" "superseded name" "the failure says what to rename it to"
}

test_legacy_means_fails() {
    local output; output=$(capture legacy_means)
    assert_contains "$output" "FAIL: Check 53" "a means block fails even beside a correct motivation"
    assert_contains "$output" "simulation.context" "the failure says where it folds to"
}

test_archived_may_keep_the_legacy_shape() {
    local output; output=$(capture archived_keeps_legacy)
    assert_contains "$output" "PASS: Check 53" "archived scenarios are history and must not be rewritten"
}

test_zero_scenarios_is_not_applicable() {
    local output; output=$(capture empty)
    assert_not_contains "$output" "FAIL: Check 53" "an unwritten scenarios.yml is not a defect"
    assert_contains "$output" "N/A" "it reports N/A rather than a pass over a population"
}

run_test test_migrated_passes
run_test test_legacy_motive_fails
run_test test_legacy_means_fails
run_test test_archived_may_keep_the_legacy_shape
run_test test_zero_scenarios_is_not_applicable
report
