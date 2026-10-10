#!/usr/bin/env bash
# tests/bash/test_next_action_check.sh
# Fixture coverage for hooks/next-action-check.sh (Downe P10: a framework turn ends on one next action).
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$REPO_ROOT/plugins/mycelium/hooks/next-action-check.sh"

# Every case runs in a project that uses Mycelium: 0.318.0 hooks do nothing outside one (founder
# ruling 2026-10-10). An EMPTY .claude/canvas/ is the realistic state right after /mycelium:setup.
PROJ="$(mktemp -d)"; mkdir -p "$PROJ/.claude/canvas"
trap 'rm -rf "$PROJ"' EXIT
export CLAUDE_PROJECT_DIR="$PROJ"

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
    local tr; tr=$(_transcript "mycelium:start" $'Here is your brief.\n\nNext: run /mycelium:assumption-test on the riskiest one (per: the brief, section 3).')
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
    local out; out=$(printf '{"hook_event_name":"Stop","stop_hook_active":false,"transcript_path":"%s","last_assistant_message":"Brief above.\\n\\nNext: nothing until the tester replies (per: ht-121)."}' "$tr" | bash "$HOOK"); rm -f "$tr"
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
_cmd_transcript() {
    # A slash command the PERSON typed: the command line, then a meta skill body, then the reply.
    local tmp; tmp=$(mktemp)
    printf '%s\n' '{"type":"user","message":{"role":"user","content":"<command-message>mycelium:xai-check</command-message>\n<command-name>/mycelium:xai-check</command-name>"}}' > "$tmp"
    printf '%s\n' '{"type":"user","isMeta":true,"message":{"role":"user","content":[{"type":"text","text":"Base directory for this skill: ..."}]}}' >> "$tmp"
    python3 - "$tmp" "$1" <<'PY'
import json,sys
open(sys.argv[1],'a').write(json.dumps({"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":sys.argv[2]}]}})+"\n")
PY
    echo "$tmp"
}

test_blocks_next_line_without_per() {
    local tr; tr=$(_transcript "mycelium:start" $'Brief above.\n\nNext: run /mycelium:assumption-test.')
    local out; out=$(_run "$tr" false); rm -f "$tr"
    assert_contains "$out" '"decision": "block"' "a Next: line with no (per ...) is blocked"
    assert_contains "$out" "per: <source>" "the reason shows the form to add"
}

test_per_elsewhere_in_message_does_not_count() {
    local tr; tr=$(_transcript "mycelium:start" $'Gates pass (per: active.yml).\n\nNext: run /mycelium:assumption-test.')
    local out; out=$(_run "$tr" false); rm -f "$tr"
    assert_contains "$out" '"decision": "block"' "the citation must be on the Next: line itself"
}

test_slash_command_turn_is_checked() {
    local tr; tr=$(_cmd_transcript "Audit written. Commit?")
    local out; out=$(_run "$tr" false); rm -f "$tr"
    assert_contains "$out" '"decision": "block"' "a turn started by a typed /mycelium: command is a framework turn"
    assert_contains "$out" "mycelium:xai-check" "the reason names the typed command"
}

test_slash_command_turn_passes_with_cited_next() {
    local tr; tr=$(_cmd_transcript $'Audit written.\n\nNext: commit DL-1411 (per: the person asked to commit).')
    local out; out=$(_run "$tr" false); rm -f "$tr"
    assert_eq "" "$out" "a cited Next: line ends a typed-command turn"
}

test_meta_entry_does_not_reset_the_turn() {
    local tr; tr=$(_transcript "mycelium:start" "placeholder")
    local tmp; tmp=$(mktemp)
    head -3 "$tr" > "$tmp"
    printf '%s\n' '{"type":"user","isMeta":true,"message":{"role":"user","content":[{"type":"text","text":"<system-reminder>x</system-reminder>"}]}}' >> "$tmp"
    printf '%s\n' '{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"Done."}]}}' >> "$tmp"
    local out; out=$(_run "$tmp" false); rm -f "$tr" "$tmp"
    assert_contains "$out" '"decision": "block"' "an injected meta entry does not hide the skill that ran earlier in the turn"
}

run_test test_blocks_next_line_without_per
run_test test_per_elsewhere_in_message_does_not_count
run_test test_slash_command_turn_is_checked
run_test test_slash_command_turn_passes_with_cited_next
run_test test_meta_entry_does_not_reset_the_turn
report
