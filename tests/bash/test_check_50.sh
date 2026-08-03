#!/usr/bin/env bash
# tests/bash/test_check_50.sh
# G-V12 coverage proof for Check 50: theories.md claims name artifacts that exist.
#
# Fixtured on the 2026-08-02 theory-fidelity audit. docs/theories.md is the file
# that states what the framework claims to implement, and every claim ends in an
# "Implemented as:" line naming gates, skills and files. Nothing verified those
# names, and three were wrong:
#
#   - gate 10 cited as "Delivery Health" — that is a section heading in
#     jit-tooling/definition-of-done.md, not a gate. The gate is "DORA /
#     Delivery Metrics".
#   - gate 4 cited as "Domain Fit" — the gate is "Cynefin Gate". This one the
#     manual audit missed entirely; the check found it on first run.
#   - a Wardley "NUDGE at Develop->Deliver" that exists nowhere in the tree.
#
# A theory claim naming an artifact that does not exist is worse than no claim:
# it reads as evidence the theory was operationalised, and theories.md is the
# first file a skeptical reader opens.
#
# The `quoted_correction` fixture guards the direction that bit during
# authoring: a correction note QUOTES the old wrong citation, and the first
# version of the check flagged the quotation. Documenting a fix must never
# permanently re-trip the check that prompted it, or the only way to stay green
# is to stop recording corrections.
#
# SCOPE, so this is not mistaken for more: it verifies artifacts EXIST. It
# cannot verify they behave as described. The same audit found
# adaptive-thresholds.md documenting a gate removed a month earlier, and a
# fabricated Hoskins element surviving in leaf-lifecycle.md — neither is
# reachable by name-matching, and both needed a human reading the prose.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/check_50"

# shellcheck disable=SC1091
set +e
source "$REPO_ROOT/tests/validate-template.sh"
set -uo pipefail

capture() {
    cd "$FIXTURES_DIR/$1" || return 1
    local out
    out=$(check_theory_claim_artifacts 2>&1)
    cd "$REPO_ROOT" || return 1
    printf '%s' "$out"
}

test_passes_on_correct_claims() {
    local output; output=$(capture good)
    assert_contains "$output" "PASS: Check 50" "correctly-named gates and real paths pass"
}

test_fails_on_wrong_gate_name() {
    local output; output=$(capture wrong_name)
    assert_contains "$output" "FAIL: Check 50" "a gate cited by the wrong name fails"
    assert_contains "$output" "Delivery Health" "the failure names the wrong citation"
}

test_fails_on_nonexistent_gate() {
    local output; output=$(capture missing_gate)
    assert_contains "$output" "FAIL: Check 50" "a gate number with no heading fails"
}

test_fails_on_missing_implemented_as_path() {
    local output; output=$(capture bad_path)
    assert_contains "$output" "FAIL: Check 50" "an Implemented-as path that does not resolve fails"
}

test_quoted_correction_does_not_retrip() {
    local output; output=$(capture quoted_correction)
    assert_contains "$output" "PASS: Check 50" "a correction note quoting the old wrong citation must not fail"
}

test_prose_hint_word_does_not_hide_a_live_miscitation() {
    # FINDING 7, 2026-08-03. Suppression used to be decided by a six-word
    # vocabulary list, and `correct` fires on "correctly" and "incorrect".
    # theories.md paragraphs are ONE LINE EACH (line 15 is 1368 chars), so a
    # single unrelated word blanked every quoted span in the paragraph.
    # Measured on the live file: 9 lines blanked, 8 by ordinary prose.
    # This fixture is prose — "formerly", "correctly", a quoted aside — carrying
    # a REAL miscitation. It must fail.
    local output; output=$(capture prose_hint_word)
    assert_contains "$output" "FAIL: Check 50" "prose containing a hint word must not suppress the check"
    assert_contains "$output" "Delivery Health" "and the live miscitation must be named"
}

test_pragma_suppresses_regardless_of_wording() {
    # FINDING 8, same root cause, other direction. A note reading
    # "(Fixed v0.80.0: this read ...)" matched no magic word, so the historical
    # citation was scanned and CI went red because the author wrote "Fixed"
    # instead of "Corrected". With an explicit pragma the wording is irrelevant.
    local output; output=$(capture pragma_any_wording)
    assert_contains "$output" "PASS: Check 50" "the pragma must work whatever the prose says"
}

test_pragma_with_unpaired_quote_fails_loudly() {
    # EDGE. Quoted-span blanking needs paired delimiters. Silently not blanking
    # would re-trip the check on the historical citation with a message that
    # blames the wrong thing, so the unpaired quote is reported as itself.
    local output; output=$(capture pragma_unpaired_quote)
    assert_contains "$output" "FAIL: Check 50" "an unpaired quote on a pragma line must fail"
    assert_contains "$output" "odd" "and say the quotes are unpaired"
}

test_zero_citations_refuses_instead_of_reporting_green() {
    # FINDING 10. The N/A guard was `if not citations_checked and not
    # paths_checked`, so it only refused when BOTH populations were empty. A
    # citation-regex change that dropped citations to 0 still printed green off
    # the back of 9 verified paths. Either population being empty must refuse.
    local output; output=$(capture no_citations)
    assert_contains "$output" "N/A" "zero citations must refuse even when paths were checked"
    assert_contains "$output" "0 gate citations" "and name WHICH population was empty"
}

run_test test_passes_on_correct_claims
run_test test_fails_on_wrong_gate_name
run_test test_fails_on_nonexistent_gate
run_test test_fails_on_missing_implemented_as_path
run_test test_quoted_correction_does_not_retrip
run_test test_prose_hint_word_does_not_hide_a_live_miscitation
run_test test_pragma_suppresses_regardless_of_wording
run_test test_pragma_with_unpaired_quote_fails_loudly
run_test test_zero_citations_refuses_instead_of_reporting_green
report
