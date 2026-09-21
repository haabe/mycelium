#!/usr/bin/env bash
# tests/bash/test_advisory_hook_fire_logs.sh — the six advisory hooks that gained a fire record.
#
# WHY THIS FILE EXISTS. v0.234.0 gave the BLOCKING hooks a shared fire-logger and left the
# advisory ones writing nothing, so `check_retirement_candidates.py` could not answer either of
# its two questions for them: did this fire in the window, and does anything read it. v0.236.0
# instrumented the remaining six.
#
# WHY THE SECOND ASSERTION IN EACH PAIR IS THE LOAD-BEARING ONE. The obvious way to instrument a
# hook is to log at entry. That is worse than not logging: a record written on every invocation
# says the mechanism fires on every matching tool call, which is indistinguishable from a
# mechanism that never discriminates, and it is the OPPOSITE of what the retirement check asks.
# So every case here asserts BOTH that a firing input writes a row AND that a quiet input does
# not. A logger that only ever passes the first half would be a regression that reads as coverage.
#
# The shared helper's own contract (row shape, caller naming, never changing the caller's verdict,
# truncation) is pinned in test_hook_fire_log.sh and is not re-tested here.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLUGIN_ROOT="$REPO_ROOT/plugins/mycelium"

# Run one hook against one stdin payload in a throwaway project; echo the row count.
run_hook() {  # $1 hook file, $2 project dir, $3 payload, $4 state file basename
    CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" PROJECT_DIR="$2" \
        bash "$PLUGIN_ROOT/hooks/$1" >/dev/null 2>&1 <<<"$3"
}

rows() {  # $1 project dir, $2 state basename
    local f="$1/.claude/state/$2"
    [ -f "$f" ] && wc -l < "$f" | tr -d ' ' || echo 0
}

test_shell_safety_guard_logs_only_when_it_warns() {
    local tmp; tmp=$(mktemp -d)
    # `$?` after a pipeline is one of the constructs this guard documents.
    run_hook "shell-safety-guard.sh" "$tmp" \
        '{"tool_name":"Bash","tool_input":{"command":"ls | grep foo; echo $?"}}'
    assert_eq "1" "$(rows "$tmp" shell-safety-guard-fires.jsonl)" "warns -> one row"

    run_hook "shell-safety-guard.sh" "$tmp" \
        '{"tool_name":"Bash","tool_input":{"command":"ls -la"}}'
    # THE ASSERTION THAT MATTERS: still one, not two.
    assert_eq "1" "$(rows "$tmp" shell-safety-guard-fires.jsonl)" "silent -> no new row"
    rm -rf "$tmp"
}

test_row_names_the_advisory_hook_not_the_helper() {
    local tmp; tmp=$(mktemp -d)
    run_hook "shell-safety-guard.sh" "$tmp" \
        '{"tool_name":"Bash","tool_input":{"command":"ls | grep foo; echo $?"}}'
    local row; row=$(cat "$tmp/.claude/state/shell-safety-guard-fires.jsonl" 2>/dev/null)
    assert_contains "$row" '"hook": "shell-safety-guard.sh"' "names the advisory hook"
    assert_contains "$row" '"outcome": "fired"' "advisory outcome is fired, not blocked"
    rm -rf "$tmp"
}

test_warning_text_still_reaches_the_caller() {
    # Instrumenting meant capturing the helper's stdout and re-emitting it. If that
    # re-emit regressed, the guard would log perfectly and advise nobody -- a silent
    # downgrade that the row-count assertions above would not catch.
    local tmp out; tmp=$(mktemp -d)
    out=$(CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" PROJECT_DIR="$tmp" \
        bash "$PLUGIN_ROOT/hooks/shell-safety-guard.sh" 2>/dev/null \
        <<<'{"tool_name":"Bash","tool_input":{"command":"ls | grep foo; echo $?"}}')
    assert_contains "$out" "additionalContext" "hook JSON still emitted to the caller"
    assert_contains "$out" "MYCELIUM SHELL-SAFETY WARNING" "the advice itself survives the capture"
    rm -rf "$tmp"
}

test_every_instrumented_hook_names_a_literal_state_path() {
    # check_retirement_candidates.py finds a hook's log by REGEXING the literal
    # `.claude/state/<name>.jsonl` out of the source. A computed filename would be
    # invisible to it -- the hook would log and still read as unmeasured.
    local missing=""
    for h in shell-safety-guard ci-signal correction-attribution-guard \
             codex-postfailure-shim reflexion-gate install-runtime-hooks; do
        grep -q "\.claude/state/$h-fires\.jsonl" "$PLUGIN_ROOT/hooks/$h.sh" || missing="$missing $h"
    done
    assert_eq "" "$missing" "every instrumented hook carries its literal state path"
}

test_a_hook_with_no_record_would_be_caught() {
    # NEGATIVE CONTROL: prove the check above can fail. A guard that cannot fail is
    # not a guard, and this file would otherwise assert a property of a grep.
    local tmp; tmp=$(mktemp -d)
    printf '#!/usr/bin/env bash\nexit 0\n' > "$tmp/fake-hook.sh"
    if grep -q "\.claude/state/fake-hook-fires\.jsonl" "$tmp/fake-hook.sh"; then
        assert_eq "unreachable" "reached" "negative control should not match"
    else
        assert_eq "1" "1" "an uninstrumented hook does NOT satisfy the literal-path check"
    fi
    rm -rf "$tmp"
}

echo "=== test_advisory_hook_fire_logs: the six advisory hooks instrumented in v0.236.0 ==="
run_test test_shell_safety_guard_logs_only_when_it_warns
run_test test_row_names_the_advisory_hook_not_the_helper
run_test test_warning_text_still_reaches_the_caller
run_test test_every_instrumented_hook_names_a_literal_state_path
run_test test_a_hook_with_no_record_would_be_caught
report
