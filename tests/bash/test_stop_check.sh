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
    assert_contains "$out" "MYCELIUM GUARDRAIL WARNINGS" "warnings branch fires on a direct diamond-state edit"
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

run_test test_warnings_message_is_plugin_form
run_test test_clean_session_no_error

report
