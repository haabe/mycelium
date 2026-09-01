#!/usr/bin/env bash
# tests/bash/test_stop_check.sh
# Smoke + regression coverage for the stop-check hook.
# Locks the v0.49.10 fix: the guardrail-warnings message must reference
# "engine/canvas-guidance.yml in the plugin" — NOT a bare ".claude/engine/..."
# path (dead in plugin form). The warnings branch is triggered cheaply via a
# non-empty diamond-state-audit.jsonl (CHECK 5).

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$REPO_ROOT/plugins/mycelium/hooks/stop-check.sh"
STOP_JSON='{"hook_event_name":"Stop"}'

test_warnings_message_is_plugin_form() {
    local tmp; tmp=$(mktemp -d)
    mkdir -p "$tmp/.claude/state"
    # Non-empty audit log → CHECK 5 sets a warning → the emit branch fires.
    printf '{"event":"direct_edit"}\n' > "$tmp/.claude/state/diamond-state-audit.jsonl"
    local out; out=$(printf '%s' "$STOP_JSON" | CLAUDE_PROJECT_DIR="$tmp" bash "$HOOK")
    rm -rf "$tmp"
    assert_contains "$out" "MYCELIUM SESSION CLOSE" "warnings branch fires on a direct diamond-state edit"
    assert_contains "$out" "engine/canvas-guidance.yml in the plugin" "v0.49.10 fix: plugin-form phrasing, not a dead .claude/ path"
    assert_not_contains "$out" ".claude/engine/canvas-guidance.yml" "no bare legacy .claude/engine/ path in the message"
    assert_contains "$out" "additionalContext" "emits valid hook JSON shape"
}

test_clean_session_no_error() {
    local tmp; tmp=$(mktemp -d)
    local out; out=$(printf '%s' "$STOP_JSON" | CLAUDE_PROJECT_DIR="$tmp" bash "$HOOK"); local rc=$?
    rm -rf "$tmp"
    assert_eq "0" "$rc" "clean session (no warnings) exits 0 without error"
}



# --- grouped session-close output (v0.165.0) ---------------------------------
# This is the LAST thing a session says. It was one run-on string — measured at 1272 characters
# and five findings on a real project, with chronic large-number warnings drowning the actionable
# ones. Grouped per Miller (chunk so the reader can hold it), serial position (actionable first,
# the standing question last) and peak-end (the last message is what is remembered). All three are
# surface-independent laws; see auto-memory reference-laws-of-ux.

test_output_is_grouped_and_counted() {
    local tmp; tmp=$(mktemp -d)
    mkdir -p "$tmp/.claude/state"
    printf '{"event":"direct_edit"}\n' > "$tmp/.claude/state/diamond-state-audit.jsonl"
    local out; out=$(printf '%s' "$STOP_JSON" | CLAUDE_PROJECT_DIR="$tmp" bash "$HOOK")
    rm -rf "$tmp"
    assert_contains "$out" "finding(s) in" "states how many findings and how many groups"
    assert_contains "$out" "OBSERVABILITY (1)" "names the group and its count"
    assert_not_contains "$out" "OBSERVABILITY (1): OBSERVABILITY" \
        "the group label must not be repeated in the body — that is pure interface-load"
}

test_nothing_is_dropped_by_grouping() {
    # The point is CHUNKING, not shortening. Tesler: shortening moves the complexity into the
    # user's head rather than removing it. Every warning must still appear in full.
    local tmp; tmp=$(mktemp -d)
    mkdir -p "$tmp/.claude/state"
    printf '{"event":"direct_edit"}\n' > "$tmp/.claude/state/diamond-state-audit.jsonl"
    local out; out=$(printf '%s' "$STOP_JSON" | CLAUDE_PROJECT_DIR="$tmp" bash "$HOOK")
    rm -rf "$tmp"
    assert_contains "$out" "diamond-state-audit.jsonl" "the warning body survives grouping intact"
    assert_contains "$out" "/diamond-progress" "the remedy inside the warning survives too"
}

test_standing_question_is_last_not_first() {
    # Serial position: first and last are what survive. The in-flight question is a standing
    # prompt rather than a finding, so it must not take the first slot from something actionable.
    local tmp; tmp=$(mktemp -d)
    mkdir -p "$tmp/.claude/state"
    printf '{"event":"direct_edit"}\n' > "$tmp/.claude/state/diamond-state-audit.jsonl"
    local out; out=$(printf '%s' "$STOP_JSON" | CLAUDE_PROJECT_DIR="$tmp" bash "$HOOK")
    rm -rf "$tmp"
    # Reduced to assert_eq, because _assert.sh defines no pass/fail helpers — the first version
    # called them, bash printed "fail: command not found", and the suite still reported 0 failed.
    # A test whose failure path cannot fail is worse than no test.
    # CHARACTER offsets, not line numbers: the hook emits ONE line of JSON with escaped newlines
    # inside it, so every awk NR is 1 and a line-based comparison silently answers "not ordered"
    # for any input. Caught because the assertion failed on output that was visibly correct.
    local before_pos after_pos ordered
    before_pos=$(awk '{print index($0,"BEFORE YOU STOP")}' <<< "$out")
    after_pos=$(awk '{print index($0,"OBSERVABILITY (")}' <<< "$out")
    ordered="no"
    if [ "$before_pos" -gt 0 ] && [ "$after_pos" -gt 0 ] && [ "$before_pos" -gt "$after_pos" ]; then
        ordered="yes"
    fi
    # _assert.sh signature is assert_eq ACTUAL EXPECTED — had it reversed first time.
    assert_eq "$ordered" "yes" "the standing question comes AFTER the actionable findings (serial position)"
}


# Runner LAST, so a test function added to this file is registered by definition.
# Moved 2026-09-01: three new tests were appended after the old runner block and silently
# never ran — the suite reported 5 passed either way. A test that is not registered is the
# same defect as a mechanism with no caller, one layer up.
run_test test_warnings_message_is_plugin_form
run_test test_clean_session_no_error
run_test test_output_is_grouped_and_counted
run_test test_nothing_is_dropped_by_grouping
run_test test_standing_question_is_last_not_first

report
