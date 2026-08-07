#!/usr/bin/env bash
# tests/bash/test_session_start_reply_owed.sh
#
# Coverage proof for hooks/session-start.sh REPLY-OWED detection (v0.68.0).
#
# THE GAP (dogfood 2026-08-01): the staleness label and canvas-health 8c(a) both
# read `touch_log[].date` and never `direction`. Any entry counts as activity, so
# an INBOUND refreshes the clock — a task where the contact answered and the
# founder did not scores as HEALTHIER than one where the founder sent something
# and heard nothing. They are opposite states. Three unanswered inbounds aged
# 4-7 days sat invisible behind a green staleness pass, one of them from a
# practitioner who had said the thesis was already his working flow.
#
# Scenario-per-guardpost:
#   happy  — last contact outbound            -> silence (waiting on them, correctly)
#   sad    — last contact inbound, >=3d       -> REPLY OWED fires
#   bad    — internal note ON TOP of inbound  -> still fires (internal is not contact)
#   bad    — touch_log out of date order      -> newest wins, not last-in-array
#   bad    — inbound but task completed       -> silence (terminal tasks are not owed)
#   bad    — legacy entries with no direction -> silence, no crash (pre-v0.68.0 logs)
#   edge   — inbound 1d old                   -> silence (under the 3d threshold)
#   edge   — bidirectional last               -> silence (the exchange completed)
#   force  — explicit reply_owed: field       -> fires regardless of dates
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

# Dates are computed relative to today so the fixtures never rot.
d_ago() { python3 -c "
from datetime import date,timedelta
print((date.today()-timedelta(days=$1)).isoformat())"; }

mk_project() {
    local proj="$TMP/$1"; shift
    mkdir -p "$proj/.claude/canvas"
    printf 'schema_version: 1\npending_tasks:\n%s\n' "$1" > "$proj/.claude/canvas/human-tasks.yml"
    echo "$proj"
}

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

D10="$(d_ago 10)"; D5="$(d_ago 5)"; D1="$(d_ago 1)"

# --- happy: last contact outbound -> no flag -------------------------------
P=$(mk_project happy "  - id: ht-h1
    type: outreach
    objective: waiting on them
    status: pending
    touch_log:
      - date: \"$D10\"
        direction: \"inbound\"
      - date: \"$D5\"
        direction: \"outbound\"")
assert_not_contains "$(run_hook "$P")" "REPLY OWED" "outbound last contact must not flag"

# --- sad: last contact inbound -> flag -------------------------------------
P=$(mk_project sad "  - id: ht-s1
    type: outreach
    objective: they wrote, we did not answer
    status: pending
    touch_log:
      - date: \"$D10\"
        direction: \"outbound\"
      - date: \"$D5\"
        direction: \"inbound\"")
OUT="$(run_hook "$P")"
assert_contains "$OUT" "REPLY OWED" "inbound last contact must flag"
assert_contains "$OUT" "ht-s1" "flag must name the task"

# --- bad: internal note stacked on top of an inbound must NOT hide it ------
P=$(mk_project internal_mask "  - id: ht-b1
    type: outreach
    objective: metric note logged after their reply
    status: pending
    touch_log:
      - date: \"$D5\"
        direction: \"inbound\"
      - date: \"$D1\"
        direction: \"internal\"")
assert_contains "$(run_hook "$P")" "ht-b1" "internal entry must not conceal an owed reply"

# --- bad: array order must not beat date order -----------------------------
P=$(mk_project order "  - id: ht-b2
    type: outreach
    objective: newest entry is first in the array
    status: pending
    touch_log:
      - date: \"$D5\"
        direction: \"inbound\"
      - date: \"$D10\"
        direction: \"outbound\"")
assert_contains "$(run_hook "$P")" "ht-b2" "newest date must win, not last array element"

# --- bad: terminal tasks are never owed ------------------------------------
P=$(mk_project terminal "  - id: ht-b3
    type: outreach
    objective: closed
    status: completed
    touch_log:
      - date: \"$D5\"
        direction: \"inbound\"")
assert_not_contains "$(run_hook "$P")" "REPLY OWED" "completed tasks must not flag"

# --- bad: legacy logs with no direction -> silence, no crash ---------------
P=$(mk_project legacy "  - id: ht-b4
    type: outreach
    objective: pre-v0.68.0 log
    status: pending
    touch_log:
      - date: \"$D10\"
      - date: \"$D5\"")
OUT="$(run_hook "$P")"
assert_not_contains "$OUT" "REPLY OWED" "missing direction is unevaluable, must not false-fire"
assert_contains "$OUT" "OPEN human task" "hook must still run normally on legacy logs"

# --- edge: under the 3-day threshold ---------------------------------------
P=$(mk_project fresh "  - id: ht-e1
    type: outreach
    objective: they replied yesterday
    status: pending
    touch_log:
      - date: \"$D1\"
        direction: \"inbound\"")
assert_not_contains "$(run_hook "$P")" "REPLY OWED" "inbound under 3d must not flag"

# --- edge: bidirectional completed the exchange ----------------------------
P=$(mk_project bidi "  - id: ht-e2
    type: outreach
    objective: two-way exchange in one entry
    status: pending
    touch_log:
      - date: \"$D5\"
        direction: \"bidirectional\"")
assert_not_contains "$(run_hook "$P")" "REPLY OWED" "bidirectional must not flag"

# --- force: explicit reply_owed overrides dates ----------------------------
P=$(mk_project forced "  - id: ht-f1
    type: outreach
    objective: manually flagged
    status: pending
    reply_owed: \"founder owes an answer\"
    touch_log:
      - date: \"$D5\"
        direction: \"outbound\"")
assert_contains "$(run_hook "$P")" "ht-f1" "explicit reply_owed must force the flag"

# --- bad: SAME-DAY reply -> silence (dogfood 2026-08-07) -------------------
# The comparison was strictly-greater, so on an equal date the first entry seen
# won. Inbound is logged before the reply to it, so "they wrote, you answered the
# same day" scored as UNANSWERED. Both live flags on the dogfood canvas were this:
# ht-060 (reply sent same day) and ht-003 (2026-08-01 inbound, 2026-08-01 reply).
# A false REPLY OWED sends the operator to contact someone already answered.
P=$(mk_project sameday "  - id: ht-s1
    type: outreach
    objective: they wrote and were answered the same day
    status: pending
    touch_log:
      - date: \"$D5\"
        direction: \"inbound\"
      - date: \"$D5\"
        direction: \"outbound\"")
assert_not_contains "$(run_hook "$P")" "REPLY OWED" "a same-day reply must discharge the obligation"

# --- sad: same-day, but THEY wrote back last -> must still fire ------------
# The tiebreak is LOG POSITION, not direction. Preferring outbound on a tie would
# silence this honest case, where the reply went out and they answered it again
# the same day. That is a real owed reply.
P=$(mk_project samedayback "  - id: ht-s2
    type: outreach
    objective: answered, then they wrote back the same day
    status: pending
    touch_log:
      - date: \"$D5\"
        direction: \"outbound\"
      - date: \"$D5\"
        direction: \"inbound\"")
assert_contains "$(run_hook "$P")" "ht-s2" "same-day inbound AFTER an outbound is still owed"

report
