#!/usr/bin/env bash
# tests/bash/test_session_start_record_size.sh
#
# Founder ruling 2026-11-12, "Size warning only": session start names the canonical record files
# past what the Read tool returns whole (scripts/check_record_size.py), and only when one is.
#
#   happy  — every record small        -> no RECORDS PAST ONE READ line
#   sad    — a record past 256 KB       -> the line, naming the file; the file is not moved
#
# Discovered + run by tests/bash/run.sh, so it executes in CI and pre-push.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLUGIN_ROOT="$REPO_ROOT/plugins/mycelium"
HOOK="$PLUGIN_ROOT/hooks/session-start.sh"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

run_hook() {
    MYCELIUM_CROSS_REPO_WATCH="" \
    CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" CLAUDE_PROJECT_DIR="$1" \
        bash "$HOOK" 2>/dev/null | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin)['hookSpecificOutput']['additionalContext'])
except Exception:
    print('')
"
}

P="$TMP/small"
mkdir -p "$P/.claude/canvas" "$P/.claude/harness"
printf 'schema_version: 1\n' > "$P/.claude/canvas/purpose.yml"
assert_not_contains "$(run_hook "$P")" "RECORDS PAST ONE READ" "small records must not be named"

P="$TMP/big"
mkdir -p "$P/.claude/canvas" "$P/.claude/harness"
printf 'schema_version: 1\n' > "$P/.claude/canvas/purpose.yml"
head -c 300000 /dev/zero | tr '\0' 'x' > "$P/.claude/harness/decision-log.md"
OUT="$(run_hook "$P")"
assert_contains "$OUT" "RECORDS PAST ONE READ: 1 record file(s)" "a record past 256 KB is named"
assert_contains "$OUT" ".claude/harness/decision-log.md 293 KB" "the line names the file and its size"
assert_eq "$(wc -c < "$P/.claude/harness/decision-log.md" | tr -d ' ')" "300000" "nothing is moved"

report
