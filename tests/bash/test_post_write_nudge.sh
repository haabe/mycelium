#!/usr/bin/env bash
# tests/bash/test_post_write_nudge.sh
# Smoke + regression coverage for the post-write-nudge hook.
# Locks the v0.49.7 fix: the canvas-schema nudge must resolve the schema in
# PLUGIN form (${CLAUDE_PLUGIN_ROOT}/schemas/canvas/) — it previously only
# checked $PROJECT_DIR/.claude/schemas/, so plugin-form users silently lost it.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$REPO_ROOT/plugins/mycelium/hooks/post-write-nudge.sh"
PLUGIN="$REPO_ROOT/plugins/mycelium"

# run_nudge <plugin_root:""|path> <project_dir> <json> -> hook stdout
run_nudge() {
    local plug="$1" pdir="$2" json="$3"
    if [ -n "$plug" ]; then
        printf '%s' "$json" | CLAUDE_PLUGIN_ROOT="$plug" CLAUDE_PROJECT_DIR="$pdir" bash "$HOOK"
    else
        printf '%s' "$json" | env -u CLAUDE_PLUGIN_ROOT CLAUDE_PROJECT_DIR="$pdir" bash "$HOOK"
    fi
}

OPP_JSON='{"tool_input":{"file_path":"/p/.claude/canvas/opportunities.yml"}}'
NONCANVAS_JSON='{"tool_input":{"file_path":"/p/docs/notes.md"}}'

test_plugin_form_schema_nudge_fires() {
    # CLAUDE_PLUGIN_ROOT set → schema resolves in the plugin cache → enhanced nudge fires.
    local out; out=$(run_nudge "$PLUGIN" /tmp "$OPP_JSON")
    assert_contains "$out" "Opportunity Solution Tree" "base OST nudge present for opportunities.yml"
    assert_contains "$out" "Schema exists at schemas/canvas/opportunities.schema.json" "v0.49.7 fix: schema nudge resolves via CLAUDE_PLUGIN_ROOT (plugin form)"
}

test_legacy_fallback_no_error() {
    # No CLAUDE_PLUGIN_ROOT and no project-local schema → base nudge only, clean exit.
    local out; out=$(run_nudge "" /tmp "$OPP_JSON"); local rc=$?
    assert_eq "0" "$rc" "exits clean without CLAUDE_PLUGIN_ROOT (legacy fallback path)"
    assert_contains "$out" "Opportunity Solution Tree" "base nudge still fires in legacy/no-schema case"
    assert_not_contains "$out" "Schema exists" "no false schema-exists claim when schema is absent"
}

test_noncanvas_path_clean() {
    local out; out=$(run_nudge "$PLUGIN" /tmp "$NONCANVAS_JSON"); local rc=$?
    assert_eq "0" "$rc" "non-canvas path runs clean"
    assert_not_contains "$out" "Schema exists" "schema branch not entered for non-canvas path"
}

test_same_session_same_canvas_nudges_once() {
    # v0.212.0: the second write to the same canvas in one session is silent; a new session fires again.
    local pdir; pdir="$(mktemp -d)"; mkdir -p "$pdir/.claude/state"
    local j1='{"session_id":"s-1","tool_input":{"file_path":"/p/.claude/canvas/opportunities.yml"}}'
    local j2='{"session_id":"s-2","tool_input":{"file_path":"/p/.claude/canvas/opportunities.yml"}}'
    local first second third
    first="$(run_nudge "$PLUGIN" "$pdir" "$j1")"
    second="$(run_nudge "$PLUGIN" "$pdir" "$j1")"
    third="$(run_nudge "$PLUGIN" "$pdir" "$j2")"
    assert_contains "$first" "Opportunity Solution Tree edited" "first write in a session nudges"
    assert_eq "$second" "" "second write to the same canvas in the same session is silent"
    assert_contains "$third" "Opportunity Solution Tree edited" "a new session nudges again"
    rm -rf "$pdir"
}

test_no_session_id_keeps_the_old_behaviour() {
    local pdir; pdir="$(mktemp -d)"; mkdir -p "$pdir/.claude/state"
    local a b
    a="$(run_nudge "$PLUGIN" "$pdir" "$OPP_JSON")"; b="$(run_nudge "$PLUGIN" "$pdir" "$OPP_JSON")"
    assert_contains "$a" "Opportunity Solution Tree edited" "no session id: fires"
    assert_contains "$b" "Opportunity Solution Tree edited" "no session id: fires again"
    rm -rf "$pdir"
}

run_test test_plugin_form_schema_nudge_fires
run_test test_same_session_same_canvas_nudges_once
run_test test_no_session_id_keeps_the_old_behaviour
run_test test_legacy_fallback_no_error
run_test test_noncanvas_path_clean

report
