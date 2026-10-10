#!/usr/bin/env bash
# tests/bash/test_preflight_stdin.sh
# Locks the 0.316.3 bounded stdin read in hooks/preflight.sh.
#
# preflight.sh reads the UserPromptSubmit payload from stdin. It used `$(cat)` whenever stdin was not
# a terminal. An agent told to re-run preflight runs it through its shell tool, and in Claude Code a
# tool command containing a heredoc gets a stdin socket that never reaches EOF, so `$(cat)` waited
# forever (35 minutes observed on 2026-10-07). The read is now bounded.
#
# Two ways this goes wrong, one test each:
#   - the payload stops reaching the helpers that need it (the bound cuts the hook's real input), or
#   - a stdin that never closes hangs preflight again.
# A stdin held open by `sleep` stands in for the socket: both deliver no data and no EOF.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLUGIN_SRC="$REPO_ROOT/plugins/mycelium"
PAYLOAD='{"hook_event_name":"UserPromptSubmit","prompt":"line one\nline two","session_id":"stdin-test"}'

# A plugin copy whose next_item.py records exactly what preflight passes it, and a project in which
# preflight calls it (it needs .claude/state/next-item.json).
_fixture() {  # $1 tmp dir
    cp -R "$PLUGIN_SRC" "$1/plugin"
    cat > "$1/plugin/scripts/next_item.py" <<'PY'
import os, sys
open(os.environ["STUB_OUT"], "w").write(sys.stdin.read())
PY
    # .claude/canvas/ makes it a Mycelium project: 0.318.0 hooks do nothing outside one (founder
    # ruling 2026-10-10). Empty, as right after /mycelium:setup.
    mkdir -p "$1/proj/.claude/state" "$1/proj/.claude/canvas"
    printf '{}' > "$1/proj/.claude/state/next-item.json"
}

test_the_payload_reaches_the_helpers_unchanged() {
    local tmp; tmp=$(mktemp -d); _fixture "$tmp"
    printf '%s' "$PAYLOAD" | STUB_OUT="$tmp/got" CLAUDE_PROJECT_DIR="$tmp/proj" \
        CLAUDE_PLUGIN_ROOT="$tmp/plugin" bash "$tmp/plugin/hooks/preflight.sh" >/dev/null 2>&1
    local got; got=$(cat "$tmp/got" 2>/dev/null)
    rm -rf "$tmp"
    assert_eq "$got" "$PAYLOAD" "the payload passes through byte for byte, newlines included"
}

test_a_stdin_that_never_closes_does_not_hang() {
    local tmp; tmp=$(mktemp -d); _fixture "$tmp"
    local out="$tmp/out" start pid elapsed
    start=$(date +%s)
    # Process substitution, not a pipe: $! is then preflight itself, not a pipeline that also waits
    # for `sleep` to end.
    STUB_OUT="$tmp/got" CLAUDE_PROJECT_DIR="$tmp/proj" CLAUDE_PLUGIN_ROOT="$tmp/plugin" \
        bash "$tmp/plugin/hooks/preflight.sh" < <(sleep 20) > "$out" 2>/dev/null &
    pid=$!
    while kill -0 "$pid" 2>/dev/null && [ $(( $(date +%s) - start )) -lt 12 ]; do sleep 0.5; done
    elapsed=$(( $(date +%s) - start ))
    local finished=yes
    if kill -0 "$pid" 2>/dev/null; then
        finished=no
        pkill -P "$pid" 2>/dev/null; kill "$pid" 2>/dev/null
    fi
    pkill -f "sleep 20" 2>/dev/null || true
    local text; text=$(cat "$out" 2>/dev/null)
    rm -rf "$tmp"
    assert_eq "$finished" "yes" "preflight finishes with an open, empty stdin (took ${elapsed}s; it hung before 0.316.3)"
    assert_contains "$text" "Mycelium preflight complete" "and still does its work"
}

test_the_read_is_bounded_in_the_source() {
    # Positive control for the hang test's premise: an unbounded `$(cat)` on stdin must not return.
    local src; src=$(grep -v '^[[:space:]]*#' "$PLUGIN_SRC/hooks/preflight.sh")
    assert_not_contains "$src" '_PF_INPUT="$(cat' "no unbounded \$(cat) read of stdin"
    assert_contains "$src" "read -r -d '' -t" "the stdin read carries a timeout"
}

run_test test_the_payload_reaches_the_helpers_unchanged
run_test test_a_stdin_that_never_closes_does_not_hang
run_test test_the_read_is_bounded_in_the_source
report
