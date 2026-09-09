#!/usr/bin/env bash
# tests/bash/test_session_start_stderr_clean.sh
#
# Coverage proof that hooks/session-start.sh runs with EMPTY stderr (v0.183.1).
#
# THE GAP (dogfood 2026-09-09): CHECK 5 embeds Python inside a double-quoted
# `python3 -c "..."` string. Four Python COMMENT lines in it carried markdown
# backticks, which bash command-substitutes before Python ever runs, so every
# SessionStart printed `line 836: cancelled: command not found` and four siblings
# to stderr. Harmless to the injected context (the substitution landed inside a
# comment) and invisible in Claude Code, which swallows hook stderr; it was found
# only by running the hook by hand. The hook's own shell-safety guard names this
# exact trap on every Bash call.
#
# Scenario-per-guardpost:
#   happy — a project with tasks in every status the block handles -> stderr empty
#   sad   — a project with no canvas at all                        -> stderr empty
#
# A future backtick anywhere in any embedded -c string fails this test, which is
# why it asserts on the WHOLE stderr and not on the five known lines.
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

hook_stderr() {
    MYCELIUM_CROSS_REPO_WATCH="" \
    CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" CLAUDE_PROJECT_DIR="$1" \
        bash "$HOOK" 2>&1 >/dev/null
}

P="$TMP/full"
mkdir -p "$P/.claude/canvas"
cat > "$P/.claude/canvas/human-tasks.yml" <<'YAML'
schema_version: 1
pending_tasks:
  - id: ht-1
    type: outreach
    objective: open task
    status: pending
    created_at: "2026-09-01"
  - id: ht-2
    type: outreach
    objective: cancelled task
    status: cancelled
    created: "2026-09-01"
  - id: ht-3
    type: outreach
    objective: task with dated reply keys
    status: pending
    reply_sent_2026_08_11: yes
    third_reply_inbound_2026_08_12: yes
YAML
assert_eq "" "$(hook_stderr "$P")" "hook on a populated project writes nothing to stderr"

P2="$TMP/empty"
mkdir -p "$P2"
assert_eq "" "$(hook_stderr "$P2")" "hook on a project with no canvas writes nothing to stderr"

report
