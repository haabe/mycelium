#!/usr/bin/env bash
# tests/bash/test_next_action_check.sh
# Fixture coverage for hooks/next-action-check.sh (Downe P10: a framework turn ends on one next action).
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$REPO_ROOT/plugins/mycelium/hooks/next-action-check.sh"

_transcript() {
    # $1 = skill name or "" ; $2 = last assistant text
    local tmp; tmp=$(mktemp)
    printf '%s\n' '{"type":"user","message":{"role":"user","content":"please run it"}}' > "$tmp"
    if [ -n "$1" ]; then
        printf '{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","name":"Skill","input":{"skill":"%s"}}]}}\n' "$1" >> "$tmp"
        printf '%s\n' '{"type":"user","message":{"role":"user","content":[{"type":"tool_result","content":"ok"}]}}' >> "$tmp"
    fi
    python3 - "$tmp" "$2" <<'PY'
import json,sys
open(sys.argv[1],'a').write(json.dumps({"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":sys.argv[2]}]}})+"\n")
PY
    echo "$tmp"
}

_run() { printf '{"hook_event_name":"Stop","stop_hook_active":%s,"transcript_path":"%s"}' "$2" "$1" | bash "$HOOK"; }

test_blocks_when_skill_ran_and_no_next_line() {
    local tr; tr=$(_transcript "mycelium:start" "Here is your brief. Good luck.")
    local out; out=$(_run "$tr" false); rm -f "$tr"
    assert_contains "$out" '"decision": "block"' "a framework turn with no Next: line is blocked"
    assert_contains "$out" "mycelium:start" "the reason names the skill that ran"
}

test_passes_when_next_line_present() {
    local tr; tr=$(_transcript "mycelium:start" $'Here is your brief.\n\nNext: run /mycelium:assumption-test on the riskiest one.')
    local out; out=$(_run "$tr" false); rm -f "$tr"
    assert_eq "" "$out" "a Next: line satisfies the check; hook is silent"
}

test_silent_when_no_framework_skill_ran() {
    local tr; tr=$(_transcript "" "Sure, the answer is 42.")
    local out; out=$(_run "$tr" false); rm -f "$tr"
    assert_eq "" "$out" "an ordinary turn is not a framework state; no block"
}

test_silent_for_non_mycelium_skill() {
    local tr; tr=$(_transcript "code-review" "Findings above.")
    local out; out=$(_run "$tr" false); rm -f "$tr"
    assert_eq "" "$out" "a non-Mycelium skill run is out of scope"
}

test_honours_stop_hook_active() {
    local tr; tr=$(_transcript "mycelium:start" "Here is your brief.")
    local out; out=$(_run "$tr" true); rm -f "$tr"
    assert_eq "" "$out" "stop_hook_active=true exits silently; no loop"
}

test_fails_open_without_transcript() {
    local out; out=$(printf '{"hook_event_name":"Stop"}' | bash "$HOOK"); local rc=$?
    assert_eq "0" "$rc" "no transcript_path exits 0"
    assert_eq "" "$out" "no transcript_path is silent (fail-open, documented in the hook header)"
}

test_person_override() {
    local tr; tr=$(_transcript "mycelium:start" "Here is your brief.")
    local out; out=$(printf '{"hook_event_name":"Stop","stop_hook_active":false,"transcript_path":"%s"}' "$tr" | MYCELIUM_NEXT_ACTION_CHECK=off bash "$HOOK"); rm -f "$tr"
    assert_eq "" "$out" "MYCELIUM_NEXT_ACTION_CHECK=off disables the check"
}

test_last_assistant_message_wins_over_lagging_transcript() {
    local tr; tr=$(_transcript "mycelium:start" "Here is your brief.")
    local out; out=$(printf '{"hook_event_name":"Stop","stop_hook_active":false,"transcript_path":"%s","last_assistant_message":"Brief above.\\n\\nNext: nothing until the tester replies."}' "$tr" | bash "$HOOK"); rm -f "$tr"
    assert_eq "" "$out" "last_assistant_message is read in preference to a lagging transcript"
}

test_unreadable_transcript_says_so() {
    local out; out=$(printf '{"hook_event_name":"Stop","stop_hook_active":false,"transcript_path":"/nonexistent/%s.jsonl"}' "$$" | bash "$HOOK")
    assert_contains "$out" "did not run this turn" "an unreadable transcript is reported, not swallowed (anti-pattern #9)"
    assert_not_contains "$out" '"decision"' "and it does not block on its own read failure"
}

run_test test_unreadable_transcript_says_so
run_test test_last_assistant_message_wins_over_lagging_transcript
run_test test_blocks_when_skill_ran_and_no_next_line
run_test test_passes_when_next_line_present
run_test test_silent_when_no_framework_skill_ran
run_test test_silent_for_non_mycelium_skill
run_test test_honours_stop_hook_active
run_test test_fails_open_without_transcript
run_test test_person_override
report
