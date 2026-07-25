#!/usr/bin/env bash
# tests/bash/test_session_start_contract_delivery.sh
#
# META-FIX (2026-07-25). Consumer-perspective delivery test: runs the REAL
# SessionStart hook against a project that looks like a downstream CONSUMER
# (plugin installed via CLAUDE_PLUGIN_ROOT, NO root/legacy CLAUDE.md, empty
# .claude/) and asserts the operating contract is actually injected.
#
# This is the test that would have caught the v0.20.0 → v0.58.0 gap. Check 47
# guards the wiring statically (files present + referenced); this proves the
# end-to-end runtime path a consumer session takes — the path that silently
# broke for ~2.5 months and was invisible from the framework repo's own seat,
# because sessions run IN the framework repo load root CLAUDE.md natively.
#
# Discovered + run by tests/bash/run.sh (Check 17), so it executes in CI and
# pre-push, from the consumer vantage the framework repo can't otherwise see.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLUGIN_ROOT="$REPO_ROOT/plugins/mycelium"
HOOK="$PLUGIN_ROOT/hooks/session-start.sh"

# Run the real hook as a consumer would see it, return the injected additionalContext.
run_hook_as_consumer() {
    local proj
    proj="$(mktemp -d)"
    mkdir -p "$proj/.claude"          # a consumer project: empty .claude/, no CLAUDE.md anywhere
    local out
    out=$(CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" CLAUDE_PROJECT_DIR="$proj" bash "$HOOK" 2>/dev/null)
    rm -rf "$proj"
    printf '%s' "$out" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d['hookSpecificOutput']['additionalContext'])
except Exception:
    print('')
"
}

test_contract_reaches_a_consumer_session() {
    local ctx
    ctx=$(run_hook_as_consumer)
    assert_contains "$ctx" "Mycelium Agent Operating Contract" "contract title reaches the consumer session"
    assert_contains "$ctx" "Communication Rules" "Communication Rules delivered"
    assert_contains "$ctx" "Mandatory Pre-Ship Protocol" "Pre-Ship protocol delivered"
    assert_contains "$ctx" "Read before Write" "canvas Read-before-Write rule delivered"
}

test_hook_resolves_contract_via_plugin_root() {
    # The hook must find the contract under CLAUDE_PLUGIN_ROOT (plugin form),
    # not only via an in-repo relative fallback.
    [ -f "$PLUGIN_ROOT/engine/agent-operating-contract.md" ]
    assert_eq "$?" "0" "contract is packaged at \${CLAUDE_PLUGIN_ROOT}/engine/agent-operating-contract.md"
}

echo "=== test_session_start_contract_delivery: a consumer session receives the operating contract ==="
run_test test_contract_reaches_a_consumer_session
run_test test_hook_resolves_contract_via_plugin_root
report
