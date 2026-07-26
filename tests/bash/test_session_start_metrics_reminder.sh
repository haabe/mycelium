#!/usr/bin/env bash
# tests/bash/test_session_start_metrics_reminder.sh
#
# Coverage proof for hooks/session-start.sh CHECK 2 (metrics staleness), and the
# WIRING test for the /dora-check ↔ session-start contract.
#
# THE BUG (2026-07-26): CHECK 2 reads a top-level `last_measured` from the
# product-type-appropriate metrics canvas, defaulting to dora-metrics.yml for
# `software` — the default product type, so the common case. But /dora-check's
# SOFTWARE "Canvas Output" block never named the field (the three non-software
# blocks all did), and dora-metrics.yml was the only metrics canvas with no
# schema to catch the omission. So for most consumers the field was never
# written. Worse, the absent-field branch was SILENT: the guard was
# `if last_measured != never`, with no else — indistinguishable from
# "measured yesterday". CHECK 1 (BVSSH) had always had a never-assessed branch;
# CHECK 2 did not.
#
# Scenario-per-guardpost: absent field -> never-measured nudge; stale date ->
# age nudge; fresh date -> silence; non-software product_type -> reads its own
# canvas, not dora-metrics.yml.
#
# Discovered + run by tests/bash/run.sh (Check 17), so it executes in CI and
# pre-push.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLUGIN_ROOT="$REPO_ROOT/plugins/mycelium"
HOOK="$PLUGIN_ROOT/hooks/session-start.sh"

# Run the hook against a synthetic consumer project and print the reminder text.
# MYCELIUM_CROSS_REPO_WATCH is cleared so an operator's own env cannot leak
# cross-repo reminders into the assertion (it did, during this test's authoring).
run_hook() {
    local proj="$1"
    MYCELIUM_CROSS_REPO_WATCH="" \
    CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" CLAUDE_PROJECT_DIR="$proj" \
        bash "$HOOK" 2>/dev/null | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d['hookSpecificOutput']['additionalContext'])
except Exception:
    print('')
"
}

# A consumer project with a dora-metrics.yml whose last_measured is \$1 (raw YAML
# value; pass the empty string to omit the key entirely).
make_project() {
    local last="$1" ptype="${2:-software}" canvas="${3:-dora-metrics.yml}"
    local proj; proj="$(mktemp -d)"
    mkdir -p "$proj/.claude/canvas" "$proj/.claude/diamonds"
    cat > "$proj/.claude/diamonds/active.yml" <<YAML
active_diamonds:
  - id: l3-test
    product_type: $ptype
YAML
    {
        echo "deployment_frequency:"
        echo "  current: daily"
        [ -n "$last" ] && echo "last_measured: $last"
    } > "$proj/.claude/canvas/$canvas"
    echo "$proj"
}

test_absent_field_emits_never_measured() {
    local p; p=$(make_project "")
    local out; out=$(run_hook "$p")
    assert_contains "$out" "never been measured" \
        "absent last_measured -> explicit never-measured nudge (was silent)"
    assert_contains "$out" "dora-metrics.yml" \
        "nudge names the canvas the agent must write"
    rm -rf "$p"
}

test_stale_date_emits_age_reminder() {
    local p; p=$(make_project "2020-01-01")
    local out; out=$(run_hook "$p")
    assert_contains "$out" "days old" "stale last_measured -> age reminder"
    rm -rf "$p"
}

test_fresh_date_is_silent() {
    local today; today=$(date -u +%Y-%m-%d)
    local p; p=$(make_project "$today")
    local out; out=$(run_hook "$p")
    if printf '%s' "$out" | grep -q "DORA metrics"; then
        assert_eq "reminder-present" "silence" "fresh last_measured -> no metrics reminder"
    else
        assert_eq "silence" "silence" "fresh last_measured -> no metrics reminder"
    fi
    rm -rf "$p"
}

test_null_field_emits_never_measured() {
    # `last_measured: null` is the HONEST value for an unmeasured project (the
    # dora-metrics schema requires the key but permits null, so a project with an
    # empty measurement_history need not fabricate a date). It must still nudge.
    local p; p=$(make_project "null")
    local out; out=$(run_hook "$p")
    assert_contains "$out" "never been measured" \
        "null last_measured -> never-measured nudge, not silence"
    rm -rf "$p"
}

test_non_software_product_type_reads_its_own_canvas() {
    # product_type: ai_tool routes CHECK 2 to ai-tool-metrics.yml. With that
    # canvas absent entirely, CHECK 2 stays quiet about it — and must NOT fall
    # back to reading dora-metrics.yml.
    local p; p=$(make_project "2020-01-01" "ai_tool" "dora-metrics.yml")
    local out; out=$(run_hook "$p")
    if printf '%s' "$out" | grep -q "DORA metrics are"; then
        assert_eq "read-dora" "read-ai-tool" \
            "ai_tool product_type must not read dora-metrics.yml"
    else
        assert_eq "ok" "ok" "ai_tool product_type routes away from dora-metrics.yml"
    fi
    rm -rf "$p"
}

echo "=== test_session_start_metrics_reminder: CHECK 2 staleness + absence signal ==="
run_test test_absent_field_emits_never_measured
run_test test_null_field_emits_never_measured
run_test test_stale_date_emits_age_reminder
run_test test_fresh_date_is_silent
run_test test_non_software_product_type_reads_its_own_canvas
report
