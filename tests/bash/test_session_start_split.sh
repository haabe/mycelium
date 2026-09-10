#!/usr/bin/env bash
# tests/bash/test_session_start_split.sh
#
# Coverage proof for the fast / async split of hooks/session-start.sh (v0.186.0).
#
# THE GAP (dogfood 2026-09-10): the hook takes ~18 s on a real canvas, all of it real
# work, and the founder waits for it at every start. Claude Code's `async: true` runs a
# hook without blocking but its output is not documented as delivered, so the contract
# must stay synchronous. The split: --fast delivers the contract and the cheap checks
# now and announces the heavy tier; --async runs the heavy tier into a cache;
# preflight.sh delivers the cache once at the next prompt and settles the ledger then;
# an unchanged canvas (same fingerprint) is served from the cache inline.
#
# Scenario-per-guardpost:
#   happy — fast, no cache: contract delivered, heavy tier announced, pending marker,
#           NO ledger settle (a partial block must never settle)
#   happy — async: cache written with the fingerprint and the session id, no stdout
#   happy — preflight, same session: block delivered once, ledger settled, marker gone
#   edge  — preflight again: nothing delivered twice
#   happy — fast, fresh cache: heavy tier inline, no announcement, ledger settles
#   sad   — canvas changed: fingerprint differs, fast announces again
#   edge  — no flag: full run as before (Codex/Cursor manifests, hand runs)
#
# Discovered + run by tests/bash/run.sh, so it executes in CI and pre-push.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLUGIN_ROOT="$REPO_ROOT/plugins/mycelium"
HOOK="$PLUGIN_ROOT/hooks/session-start.sh"
PREFLIGHT="$PLUGIN_ROOT/hooks/preflight.sh"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

P="$TMP/proj"
mkdir -p "$P/.claude/canvas" "$P/.claude/memory"
cat > "$P/.claude/canvas/human-tasks.yml" <<'YAML'
schema_version: 1
pending_tasks:
  - id: ht-1
    type: outreach
    objective: an open task
    status: pending
    created_at: "2026-01-01"
YAML
printf 'opportunities: []\n' > "$P/.claude/canvas/opportunities.yml"
printf '# corrections\n' > "$P/.claude/memory/corrections.md"
LEDGER="$P/.claude/state/advisory-ledger.jsonl"
CACHE="$P/.claude/state/session-checks.json"
PENDING="$P/.claude/state/session-checks.pending"

start() {  # $1 flag ('' for full), $2 session id
    printf '{"hook_event_name":"SessionStart","source":"startup","session_id":"%s"}' "$2" \
      | MYCELIUM_CROSS_REPO_WATCH="" \
        CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" CLAUDE_PROJECT_DIR="$P" \
        bash "$HOOK" $1 2>/dev/null | python3 -c "
import json, sys
raw = sys.stdin.read()
try:
    print(json.loads(raw)['hookSpecificOutput']['additionalContext'])
except Exception:
    print(raw)
"
}
prompt() {  # $1 session id
    printf '{"hook_event_name":"UserPromptSubmit","session_id":"%s"}' "$1" \
      | CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" CLAUDE_PROJECT_DIR="$P" bash "$PREFLIGHT" 2>/dev/null
}
ledger_lines() { [ -f "$LEDGER" ] && grep -c '"kind"' "$LEDGER" || echo 0; }

# --- fast, no cache ---------------------------------------------------------
OUT=$(start --fast s1)
assert_contains "$OUT" "Communication Rules" "fast tier delivers the contract"
assert_contains "$OUT" "OPEN human task" "fast tier runs the cheap checks"
assert_contains "$OUT" "BACKGROUND CHECKS" "fast tier announces the heavy tier"
assert_contains "$OUT" "evidence-landing" "the announcement names a heavy check"
assert_not_contains "$OUT" "Skipped for time" "a background announcement is not a time skip"
assert_eq "$(cat "$PENDING")" "s1" "pending marker carries the session id"
assert_eq "$(ledger_lines)" "0" "a partial block never settles the ledger"

# --- async ---------------------------------------------------------------------
OUT=$(start --async s1)
assert_eq "$OUT" "" "async tier emits nothing"
assert_eq "$(python3 -c "import json;print(json.load(open('$CACHE'))['session'])")" "s1" "cache carries the session id"
assert_contains "$(python3 -c "import json;print(json.load(open('$CACHE'))['reminders'])")" "OPEN human task" "cache carries the full block"

# --- preflight delivers once and settles -------------------------------------
OUT=$(prompt s1)
assert_contains "$OUT" "MYCELIUM FEEDBACK LOOPS (background run, delivered now)" "preflight delivers the block"
assert_contains "$OUT" "OPEN human task" "the delivered block carries the advisories"
assert_contains "$OUT" "Mycelium preflight complete" "preflight still prints its own line"
assert_eq "$([ -f "$PENDING" ] && echo present || echo absent)" "absent" "pending marker removed after delivery"
assert_eq "$(ledger_lines)" "1" "the ledger settled on the full block (one seen event)"
OUT=$(prompt s1)
assert_not_contains "$OUT" "background run" "a second prompt does not deliver twice"

# --- fast with a fresh cache ----------------------------------------------------
OUT=$(start --fast s2)
assert_contains "$OUT" "from a background run" "fresh cache is served inline"
assert_not_contains "$OUT" "BACKGROUND CHECKS" "no announcement when the cache is fresh"
assert_eq "$(ledger_lines)" "3" "a full inline block settles the ledger (settled + seen)"

# --- canvas changed -> fingerprint differs ------------------------------------------
sleep 1
printf 'opportunities: []\n# touched\n' > "$P/.claude/canvas/opportunities.yml"
OUT=$(start --fast s3)
assert_contains "$OUT" "BACKGROUND CHECKS" "a changed canvas invalidates the cache"

# --- no flag: full run -----------------------------------------------------------
OUT=$(start "" s4)
assert_contains "$OUT" "Communication Rules" "full mode delivers the contract"
assert_not_contains "$OUT" "BACKGROUND CHECKS" "full mode announces nothing"
assert_not_contains "$OUT" "from a background run" "full mode serves no cache"

report
