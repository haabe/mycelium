#!/usr/bin/env bash
# tests/bash/test_session_start_budget.sh
#
# Coverage proof for the in-hook deadline in hooks/session-start.sh (v0.185.0).
#
# THE GAP (dogfood 2026-09-10): hooks.json carried `"timeout": 5` on this hook while the
# hook grew to ~18 s on a real canvas. The harness cancelled it on 32 of 33 session starts
# in a month and discarded its output: no operating contract, no advisories, and every
# test green, because tests run the script and not the harness.
#
# Scenario-per-guardpost:
#   sad   — MYCELIUM_SESSION_START_BUDGET=0: optional checks are skipped, the skip is named,
#           the contract is STILL delivered (it must never be the thing that gets cut)
#   happy — default budget on a small fixture: no skip line, and the run finishes well
#           inside the manifest timeout
#
# Discovered + run by tests/bash/run.sh, so it executes in CI and pre-push.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLUGIN_ROOT="$REPO_ROOT/plugins/mycelium"
HOOK="$PLUGIN_ROOT/hooks/session-start.sh"
MANIFEST_TIMEOUT=$(python3 -c "
import json
d=json.load(open('$PLUGIN_ROOT/hooks/hooks.json'))
print([h['timeout'] for e in d['hooks']['SessionStart'] for h in e['hooks'] if 'session-start.sh' in h['command'] and 'timeout' in h][0])")

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

P="$TMP/proj"
mkdir -p "$P/.claude/canvas" "$P/.claude/evals/assumption-tests"
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

run_hook() {  # $1 budget (empty = default)
    printf '{"hook_event_name":"SessionStart","source":"startup","session_id":"b-%s"}' "${1:-d}" \
      | MYCELIUM_SESSION_START_BUDGET="${1:-25}" MYCELIUM_CROSS_REPO_WATCH="" MYCELIUM_ADVISORY_LEDGER=off \
        CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" CLAUDE_PROJECT_DIR="$P" HOME="$TMP/home" \
        bash "$HOOK" 2>/dev/null | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin)['hookSpecificOutput']['additionalContext'])
except Exception:
    print('')
"
}

# --- sad: zero budget -> skips named, contract still delivered ----------
OUT0=$(run_hook 0)
assert_contains "$OUT0" "SESSION-START BUDGET" "a zero budget reports itself"
assert_contains "$OUT0" "Skipped for time" "the skipped checks are named"
assert_contains "$OUT0" "evidence-landing" "evidence landing is among the skipped optional checks"
assert_contains "$OUT0" "Communication Rules" "the operating contract is still delivered under a zero budget"

# --- happy: default budget on a small fixture -> no skip, inside timeout --
T0=$(date +%s)
OUT1=$(run_hook)
T1=$(date +%s)
assert_not_contains "$OUT1" "Skipped for time" "a small fixture skips nothing at the default budget"
assert_contains "$OUT1" "Communication Rules" "the contract is delivered on the happy path"
ELAPSED=$(( T1 - T0 ))
if [ "$ELAPSED" -lt "$MANIFEST_TIMEOUT" ]; then
    assert_eq "inside" "inside" "fixture run (${ELAPSED}s) is inside the manifest timeout (${MANIFEST_TIMEOUT}s)"
else
    assert_eq "inside" "outside(${ELAPSED}s)" "fixture run must finish inside the manifest timeout (${MANIFEST_TIMEOUT}s)"
fi

report
