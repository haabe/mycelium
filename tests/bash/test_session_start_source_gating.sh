#!/usr/bin/env bash
# tests/bash/test_session_start_source_gating.sh
#
# Coverage proof for SessionStart source gating (v0.104.0).
#
# THE GAP (dogfood 2026-08-07): the hook was registered for `startup|resume`
# only, so after a /clear the agent had no canvas, no diamond state, no open
# loops AND no reminders — the one moment orientation is most needed was the one
# moment it was absent. SessionStart actually fires for five sources: startup,
# resume, clear, compact, fork (code.claude.com/docs/en/hooks, read 2026-08-07).
#
# But widening the matcher alone would have made things WORSE, because CHECK 6
# WRITES: it increments a session counter for longitudinal assumption tests. A
# counter that counts hook firings instead of sessions reports a shadow-log as
# more observed than it is — it inflates N, which is the dangerous direction.
# `resume` has been incrementing since v0.68.0, so the error predates the
# widening; the widening would have multiplied it.
#
# Scenario-per-guardpost:
#   happy — source=startup            -> counter increments (a real new session)
#   sad   — source=resume             -> no increment (continuation)
#   sad   — source=clear              -> no increment (continuation)
#   sad   — source=compact            -> no increment (continuation)
#   sad   — source=fork               -> no increment (continuation)
#   bad   — no payload at all         -> increments (legacy runtimes keep working
#                                        rather than silently freezing forever)
#   bad   — malformed payload         -> increments, no crash
#   happy — reminders print regardless of source (they are read-only)
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
HOOK="$REPO/plugins/mycelium/hooks/session-start.sh"

PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); echo "    ✓ : $1"; }
bad()  { FAIL=$((FAIL+1)); echo "    ✗ : $1"; }

mk_project() {
  local d; d="$(mktemp -d)"
  mkdir -p "$d/.claude/evals/assumption-tests"
  cat > "$d/.claude/evals/assumption-tests/t.count.json" <<'JSON'
{"test":"t","started":"2026-08-07","target":10,"sessions":3,"closed":false,"doc":"d.md"}
JSON
  echo "$d"
}

sessions_in() {
  python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['sessions'])" \
    "$1/.claude/evals/assumption-tests/t.count.json"
}

run_with_payload() {
  local dir="$1" payload="$2"
  printf '%s' "$payload" | CLAUDE_PLUGIN_ROOT="$REPO/plugins/mycelium" \
    CLAUDE_PROJECT_DIR="$dir" bash "$HOOK" 2>/dev/null
}

echo "  session-start source gating"

# --- happy: a real start counts --------------------------------------------
D="$(mk_project)"
run_with_payload "$D" '{"source":"startup"}' >/dev/null
if [ "$(sessions_in "$D")" = "4" ]; then ok "startup increments the counter"
else bad "startup must increment (got $(sessions_in "$D"), want 4)"; fi
rm -rf "$D"

# --- sad: every continuation does NOT count --------------------------------
for SRC in resume clear compact fork; do
  D="$(mk_project)"
  run_with_payload "$D" "{\"source\":\"$SRC\"}" >/dev/null
  if [ "$(sessions_in "$D")" = "3" ]; then ok "$SRC must not inflate N"
  else bad "$SRC incremented the counter (got $(sessions_in "$D"), want 3)"; fi
  rm -rf "$D"
done

# --- bad: no payload -> keep legacy behaviour ------------------------------
# Runtimes that send no stdin (Codex CLI, manual invocation) must keep counting.
# Freezing every counter silently would be a worse failure than over-counting.
D="$(mk_project)"
run_with_payload "$D" '' >/dev/null
if [ "$(sessions_in "$D")" = "4" ]; then ok "no payload still counts (legacy runtimes)"
else bad "missing payload froze the counter (got $(sessions_in "$D"), want 4)"; fi
rm -rf "$D"

# --- bad: malformed payload -> no crash, keep counting ---------------------
D="$(mk_project)"
run_with_payload "$D" 'not json at all' >/dev/null
if [ "$(sessions_in "$D")" = "4" ]; then ok "malformed payload counts, does not crash"
else bad "malformed payload changed counting (got $(sessions_in "$D"), want 4)"; fi
rm -rf "$D"

# --- happy: reminders are read-only and fire on every source ---------------
# The whole point of widening the matcher. After a /clear the agent has nothing,
# so the orientation output must still be produced even though the write is skipped.
D="$(mk_project)"
OUT="$(run_with_payload "$D" '{"source":"clear"}')"
if [ -n "$OUT" ]; then ok "clear still produces orientation output"
else bad "clear produced no output — the widening bought nothing"; fi
rm -rf "$D"

echo "  $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
