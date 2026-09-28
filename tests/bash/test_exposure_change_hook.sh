#!/bin/bash
# exposure-change.sh (v0.279.0): says a ready -> not-ready flip right after a diamonds write,
# and stays silent on every other write.
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

printf 'ready\n' > "$TMP/.claude/state/exposure-last"
out=$(printf '{"tool_input":{"file_path":".claude/diamonds/active.yml"}}' \
  | CLAUDE_PROJECT_DIR="$TMP" CLAUDE_PLUGIN_ROOT="$ROOT/plugins/mycelium" bash "$HOOK")
case "$out" in
  *'"hookEventName": "PostToolUse"'*'EXPOSURE STATE CHANGED WITH THIS WRITE'*) ;;
  *) echo "FAIL: the ready -> not-ready flip was not said: $out"; fail=1 ;;
esac

out=$(printf '{"tool_input":{"file_path":".claude/diamonds/active.yml"}}' \
  | CLAUDE_PROJECT_DIR="$TMP" CLAUDE_PLUGIN_ROOT="$ROOT/plugins/mycelium" bash "$HOOK")
[ -z "$out" ] || { echo "FAIL: said again with no new change: $out"; fail=1; }

[ "$fail" -eq 0 ] && echo "PASS: exposure-change hook"
exit "$fail"
