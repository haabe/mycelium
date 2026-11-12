#!/bin/bash
# exposure-change.sh (v0.279.0): says a ready -> not-ready flip right after a diamonds write,
# and stays silent on every other write. Each time it speaks it leaves one row in
# .claude/state/exposure-change-fires.jsonl, and none when it is silent.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOOK="$ROOT/plugins/mycelium/hooks/exposure-change.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/.claude/diamonds" "$TMP/.claude/state"
printf 'active_diamonds: []\n' > "$TMP/.claude/diamonds/active.yml"
fail=0

out=$(printf '{"tool_input":{"file_path":"src/app.py"}}' | CLAUDE_PROJECT_DIR="$TMP" bash "$HOOK")
[ -z "$out" ] || { echo "FAIL: a write to another file said something: $out"; fail=1; }
FIRES="$TMP/.claude/state/exposure-change-fires.jsonl"
rows() { if [ -f "$FIRES" ]; then grep -c . "$FIRES"; else echo 0; fi; }
[ "$(rows)" = 0 ] || { echo "FAIL: a silent write left a fire row"; fail=1; }

printf 'ready\n' > "$TMP/.claude/state/exposure-last"
out=$(printf '{"tool_input":{"file_path":".claude/diamonds/active.yml"}}' \
  | CLAUDE_PROJECT_DIR="$TMP" CLAUDE_PLUGIN_ROOT="$ROOT/plugins/mycelium" bash "$HOOK")
case "$out" in
  *'"hookEventName": "PostToolUse"'*'EXPOSURE STATE CHANGED WITH THIS WRITE'*) ;;
  *) echo "FAIL: the ready -> not-ready flip was not said: $out"; fail=1 ;;
esac
[ "$(rows)" = 1 ] || { echo "FAIL: speaking left $(rows) fire row(s), not 1"; fail=1; }
grep -q '"hook": "exposure-change.sh", "outcome": "fired", "detail": "ready->not-ready"' "$FIRES" 2>/dev/null \
  || { echo "FAIL: the fire row does not say which hook fired on which change: $(cat "$FIRES" 2>/dev/null)"; fail=1; }

out=$(printf '{"tool_input":{"file_path":".claude/diamonds/active.yml"}}' \
  | CLAUDE_PROJECT_DIR="$TMP" CLAUDE_PLUGIN_ROOT="$ROOT/plugins/mycelium" bash "$HOOK")
[ -z "$out" ] || { echo "FAIL: said again with no new change: $out"; fail=1; }
[ "$(rows)" = 1 ] || { echo "FAIL: after one fire and one silent write there are $(rows) fire row(s), not 1"; fail=1; }

[ "$fail" -eq 0 ] && echo "PASS: exposure-change hook"
exit "$fail"
