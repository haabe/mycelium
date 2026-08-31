#!/usr/bin/env bash
# tests/bash/test_read_log_bash_reads.sh
# Coverage proof for read-log.sh's Bash half (added v0.143.0).
#
# THE GAP IT CLOSES. The hook was bound PostToolUse matcher=Read, so reads done
# with cat/head/sed/grep/python were logged nowhere -- while sessions are
# routinely instructed to prefer Bash. On the dogfood repo the log held 3,401
# rows and every one came from the Read tool, so nothing could establish that a
# record had been consulted before an agent characterised it.
#
# Scenario-per-guardpost:
#   happy — a read verb naming a project file        -> one row, inferred
#   happy — a Read tool call                          -> one row, NOT inferred
#   sad   — several files in one command              -> one row each
#   edge  — rm / git add (path named, not read)       -> silent
#   edge  — a redirect target (that is a write)       -> silent
#   edge  — a file outside the project                -> silent
#   edge  — a path that does not exist                -> silent
#   bad   — unparseable payload                       -> silent, exit 0

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$REPO_ROOT/plugins/mycelium/hooks/read-log.sh"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/.claude/state" "$TMP/canvas"
printf 'a: 1\n' > "$TMP/canvas/one.yml"
printf 'b: 2\n' > "$TMP/canvas/two.yml"
LOG="$TMP/.claude/state/read-log.jsonl"

# emit <tool_name> <json_for_tool_input> ; returns rows added
emit() {
    : > "$LOG"
    python3 -c "
import json,sys
print(json.dumps({'tool_name': sys.argv[1], 'session_id': 'T',
                  'tool_input': json.loads(sys.argv[2])}))" "$1" "$2" \
      | CLAUDE_PROJECT_DIR="$TMP" bash "$HOOK" >/dev/null 2>&1
    wc -l < "$LOG" | tr -d ' '
}
field() { python3 -c "
import json,sys
rows=[json.loads(l) for l in open(sys.argv[1]) if l.strip()]
print(rows[0].get(sys.argv[2], 'ABSENT') if rows else 'NOROWS')" "$LOG" "$1"; }

assert_eq "$(emit Bash "{\"command\":\"sed -n 1,5p canvas/one.yml\"}")" "1" \
    "a read verb naming a project file logs one row"
assert_eq "$(field inferred)" "True" "a Bash-derived row is marked inferred"
assert_eq "$(field tool)" "Bash" "the row records the tool that produced it"

assert_eq "$(emit Read "{\"file_path\":\"$TMP/canvas/one.yml\"}")" "1" \
    "a Read tool call still logs one row"
assert_eq "$(field inferred)" "ABSENT" \
    "an OBSERVED read carries no inferred flag -- the distinction is the point"

assert_eq "$(emit Bash "{\"command\":\"grep -n x canvas/one.yml canvas/two.yml\"}")" "2" \
    "two files in one command log one row each"

assert_eq "$(emit Bash "{\"command\":\"rm canvas/one.yml\"}")" "0" \
    "rm names a path and does not read it"
assert_eq "$(emit Bash "{\"command\":\"git add canvas/one.yml\"}")" "0" \
    "git add names a path and does not read it"
assert_eq "$(emit Bash "{\"command\":\"echo hi > canvas/one.yml\"}")" "0" \
    "a redirect target is a write, not a read"
assert_eq "$(emit Bash "{\"command\":\"cat /etc/hosts\"}")" "0" \
    "a file outside the project is not a project read"
assert_eq "$(emit Bash "{\"command\":\"cat canvas/missing.yml\"}")" "0" \
    "a path that does not exist is not logged"

: > "$LOG"
printf 'not json' > "$TMP/payload.txt"
CLAUDE_PROJECT_DIR="$TMP" bash "$HOOK" < "$TMP/payload.txt" >/dev/null 2>&1
RC=$?
assert_eq "$RC" "0" "an unparseable payload exits 0"
assert_eq "$(wc -l < "$LOG" | tr -d ' ')" "0" "and writes nothing"

report
