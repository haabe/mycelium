#!/usr/bin/env bash
# Regression tests for the seven canvas-health check defects fixed in v0.90.0.
#
# HOW THEY WERE FOUND. The 2026-08-05 dogfood run of /canvas-health produced five
# substantive findings; FOUR were defects in the checks rather than in the canvas,
# and two more surfaced while acting on the report. Every one shares a shape: the
# check fired on something that was already correct, and the only way to satisfy it
# would have been to damage the canvas — date a validation nobody performed, close a
# task whose reason for being open was written beside it, or "fix" a Definition of
# Done that was already right.
#
# That shape matters more than the individual bugs. A check that fires on correct
# state trains its reader to skip it, and a skipped check reads as coverage while
# providing none — the failure this repo has logged against its own mechanisms
# repeatedly.
#
# These tests fail if any of the seven comes back.

set -uo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CH="$REPO_ROOT/plugins/mycelium/skills/canvas-health/SKILL.md"
source "$(dirname "${BASH_SOURCE[0]}")/_assert.sh"

echo "canvas-health check defects (v0.90.0)"
echo "======================================================"

body="$(cat "$CH")"

# (1) source_class must be read from the schema, not hardcoded --------------
grep -q 'one of: `external_human`, `external_data`, `internal_stakeholder`, `internal_desk`, `internal_simulated` — flag unknown' "$CH" \
  && assert_eq "found" "absent" "step 5 must not hardcode the 5-value source_class list" \
  || assert_eq "absent" "absent" "step 5 no longer hardcodes the source_class list"
assert_contains "$body" 'source_class` ' "step 5 points at the schema \$defs/source_class"
assert_contains "$body" "Do NOT hardcode the list here" "step 5 says not to hardcode it"

# (2) reply-owed must DELEGATE, not restate the algorithm -------------------
# CHANGED v0.105.0, and the change is the point. This used to assert the prose
# CONTAINED the same-day tie-break. That is a test that a paragraph exists, and it
# passed happily for two days while session-start.sh — the copy that actually runs —
# still had the bug and flagged ht-060 and ht-003 again. Asserting prose is how a
# rule ends up with two implementations and one of them right.
# The BEHAVIOUR now has real coverage in tests/python/test_check_reply_owed.py
# (same-day answered, same-day inbound-after-outbound, internal-note masking).
# What is left to check here is that the skill DELEGATES rather than re-describes.
assert_contains "$body" "check_reply_owed.py" "8c(e) calls the single implementation"
assert_contains "$body" "DO NOT re-derive this from prose" "8c(e) forbids re-deriving the rule"

# (3) 9c must only count a date the gate WAITS FOR --------------------------
assert_contains "$body" "not the date it was AUTHORED ON" "9c distinguishes awaited from authored dates"
assert_contains "$body" "condition-gated hold with no awaited date is not overdue" "9c exempts condition-gated holds"

# (4) staleness must skip files marked inapplicable -------------------------
assert_contains "$body" "_meta.applicability" "step 3 reads _meta.applicability"
assert_contains "$body" "SKIP any file whose" "step 3 skips inapplicable files"

# (5) the version-drift check is wired and real -----------------------------
assert_contains "$body" "check_canvas_version_drift.py" "canvas-health invokes the version-drift check"
script="$REPO_ROOT/plugins/mycelium/scripts/check_canvas_version_drift.py"
[ -f "$script" ] && assert_eq "present" "present" "check_canvas_version_drift.py ships" \
                 || assert_eq "missing" "present" "check_canvas_version_drift.py ships"

# It must be a real guard: exit 1 on a stale claim, 2 when it cannot look.
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/fw/.claude-plugin" "$tmp/proj/.claude/canvas"
printf '{"version": "0.89.0"}' > "$tmp/fw/.claude-plugin/plugin.json"
printf 'model_metrics:\n  version: "Mycelium 0.16.1"\n' > "$tmp/proj/.claude/canvas/ai-tool-metrics.yml"
python3 "$script" --root "$tmp/proj" --framework-root "$tmp/fw" >/dev/null 2>&1
assert_eq "$?" "1" "version-drift check REJECTS a stale claimed version"
python3 "$script" --root "$tmp/proj" --framework-root "$tmp/nowhere" >/dev/null 2>&1
assert_eq "$?" "2" "version-drift check reports UNKNOWN when it cannot read plugin.json"

# (6) 8c(b) must read horizon before demanding a reason ---------------------
assert_contains "$body" "CHECK \`horizon\` / \`scoring_horizon\`" "8c(b) checks horizon first"
assert_contains "$body" "a dated horizon IS the recorded reason" "8c(b) treats a future horizon as the reason"

# (7) build-mode must not match earn-verbs inside negations -----------------
assert_contains "$body" "Ignore a match that sits inside a NEGATION" "8c build-mode has a negation guard"
assert_contains "$body" "disclaiming the earn-bar is the natural way to write one" "8c explains why negation matching is backwards"

echo "------------------------------------------------------"
report
