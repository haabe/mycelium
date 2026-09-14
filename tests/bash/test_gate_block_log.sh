#!/usr/bin/env bash
# tests/bash/test_gate_block_log.sh — a gate.sh block leaves a line (v0.204.0).
#
# gate.sh exited 2 on a stale stamp or a changed corrections hash and wrote nothing anywhere
# when it did, so whether it fires on real users was unmeasurable. Each block now appends one
# JSON line to .claude/state/gate-block-log.jsonl. Scenario-per-guardpost:
#   sad   — no stamp and a preflight that fails  -> exit 2 AND a stale-stamp line with the session id
#   happy — a clean allow                        -> no log line written
#   bad   — state dir unwritable                 -> still exit 2 (the log never changes the verdict)
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLUG="$REPO_ROOT/plugins/mycelium"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export MYCELIUM_CROSS_REPO_WATCH=""
unset MYCELIUM_GUARD_STATE_EDIT

# A fake plugin root whose preflight always fails, so the stamp path blocks. gate.sh resolves its
# input library from its OWN location, so the real hook runs with the fake root for preflight only.
FAKE="$TMP/fakeplug"; mkdir -p "$FAKE/hooks"
printf '#!/usr/bin/env bash\nexit 1\n' > "$FAKE/hooks/preflight.sh"

P="$TMP/proj"; mkdir -p "$P/src" "$P/.claude/memory" "$P/.claude/state"
echo "# corrections" > "$P/.claude/memory/corrections.md"
export TMPDIR="$TMP/stampdir"; mkdir -p "$TMPDIR"   # no stamp exists here, so renewal is needed

payload='{"tool_name":"Write","tool_input":{"file_path":"'"$P"'/src/a.py","content":"x = 1"},"session_id":"sess-42"}'
printf '%s' "$payload" | CLAUDE_PROJECT_DIR="$P" CLAUDE_PLUGIN_ROOT="$FAKE" bash "$PLUG/hooks/gate.sh" >/dev/null 2>&1; rc=$?
assert_eq "$rc" "2" "sad: no stamp + failing preflight blocks"
assert_eq "$(test -f "$P/.claude/state/gate-block-log.jsonl" && echo yes || echo no)" "yes" "sad: a block leaves a log line"
assert_contains "$(cat "$P/.claude/state/gate-block-log.jsonl")" '"reason": "stale-stamp"' "sad: the line names the reason"
assert_contains "$(cat "$P/.claude/state/gate-block-log.jsonl")" '"session_id": "sess-42"' "sad: the line carries the session id"

# happy: with the real plugin root the preflight succeeds and stamps; a clean write allows and logs nothing new.
before="$(wc -l < "$P/.claude/state/gate-block-log.jsonl")"
printf '%s' "$payload" | CLAUDE_PROJECT_DIR="$P" CLAUDE_PLUGIN_ROOT="$PLUG" bash "$PLUG/hooks/gate.sh" >/dev/null 2>&1; rc=$?
assert_eq "$rc" "0" "happy: a clean write with a fresh stamp allows"
assert_eq "$(wc -l < "$P/.claude/state/gate-block-log.jsonl")" "$before" "happy: an allow writes no log line"

# bad: a log file the hook cannot append to must not change the verdict.
Q="$TMP/proj2"; mkdir -p "$Q/src" "$Q/.claude/memory" "$Q/.claude/state"; echo "# c" > "$Q/.claude/memory/corrections.md"
printf '' > "$Q/.claude/state/gate-block-log.jsonl"; chmod 444 "$Q/.claude/state/gate-block-log.jsonl"
trap 'chmod -R u+w "$TMP" 2>/dev/null; rm -rf "$TMP"' EXIT
export TMPDIR="$TMP/stampdir2"; mkdir -p "$TMPDIR"
qpayload='{"tool_name":"Write","tool_input":{"file_path":"'"$Q"'/src/a.py","content":"x = 1"},"session_id":"sess-43"}'
printf '%s' "$qpayload" | CLAUDE_PROJECT_DIR="$Q" CLAUDE_PLUGIN_ROOT="$FAKE" bash "$PLUG/hooks/gate.sh" >/dev/null 2>&1; rc=$?
assert_eq "$rc" "2" "bad: an unappendable log still blocks"
assert_eq "$(wc -c < "$Q/.claude/state/gate-block-log.jsonl" | tr -d ' ')" "0" "bad: and the read-only log is untouched"

report
