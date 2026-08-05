#!/bin/bash
# Mycelium Stop guardrail check
# Layer 4: Verify guardrail compliance when Claude finishes responding.
# Returns warnings via additionalContext (does NOT block by default).
#
# Checks:
# 1. If delivering code but required canvas files are empty templates
# 2. Corrections count for session summary
# 3. Decision log check
# 4. Overdue feedback loops (BVSSH, DORA) -- from feedback-loops.md

# SELF-LOCATION, added v0.88.0. This script lives at <plugin_root>/hooks/, so
# its own path resolves the plugin root without anyone setting anything. Needed
# because CLAUDE_PLUGIN_ROOT is a Claude Code variable: Cursor exports
# CLAUDE_PROJECT_DIR instead and Codex exports neither, so every
# "${CLAUDE_PLUGIN_ROOT}/scripts/*.py" lookup below resolved to "/scripts/*.py"
# there, missed, and fell through to a silent no-op. Same class as the
# hardcoded cache path removed from the runtime manifests in this release: an
# artifact asserting a location it cannot know, failing open when wrong.
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  _mycelium_self="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." 2>/dev/null && pwd || true)"
  if [ -n "$_mycelium_self" ] && [ -d "$_mycelium_self/scripts" ]; then
    CLAUDE_PLUGIN_ROOT="$_mycelium_self"
    export CLAUDE_PLUGIN_ROOT
  fi
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
CANVAS_DIR="$PROJECT_DIR/.claude/canvas"
ACTIVE_FILE="$PROJECT_DIR/.claude/diamonds/active.yml"
WARNINGS=""

# ============================================================
# CHECK 1: Canvas population for delivery diamonds
# ============================================================
# Check if we have active L4 delivery diamonds
if [ -f "$ACTIVE_FILE" ]; then
  HAS_L4=$(python3 -c "
import sys
content = open(sys.argv[1]).read()
# Simple check: does active.yml contain 'scale: L4' or 'L4' with 'deliver' phase
has_l4 = 'L4' in content and ('deliver' in content.lower() or 'develop' in content.lower())
print('yes' if has_l4 else 'no')
" "$ACTIVE_FILE" 2>/dev/null || echo "no")

  if [ "$HAS_L4" = "yes" ]; then
    # Check required canvas files for delivery
    # threat-model.yml should be populated if handling user data
    if [ -f "$CANVAS_DIR/threat-model.yml" ]; then
      COMPONENTS_EMPTY=$(grep -c "^components: \[\]" "$CANVAS_DIR/threat-model.yml" 2>/dev/null || echo "0")
      if [ "$COMPONENTS_EMPTY" -gt 0 ]; then
        WARNINGS="${WARNINGS}GUARDRAIL G-S2: threat-model.yml has no components assessed. If this solution handles user data, run /threat-model before completing delivery. "
      fi
    fi

    # services.yml should be assessed for user-facing work
    if [ -f "$CANVAS_DIR/services.yml" ]; then
      NOT_ASSESSED=$(grep -c "not-assessed" "$CANVAS_DIR/services.yml" 2>/dev/null || echo "0")
      TOTAL_PRINCIPLES=15
      if [ "$NOT_ASSESSED" -ge "$TOTAL_PRINCIPLES" ]; then
        WARNINGS="${WARNINGS}GUARDRAIL G-V2: Downe's 15 service principles have not been assessed. Run /service-check for user-facing work. "
      fi
    fi
  fi
fi

# ============================================================
# CHECK 2: Corrections count summary
# ============================================================
# Count ### headings OUTSIDE code blocks (template includes an example heading
# inside a ```...``` fence that must not be counted as a real correction)
CORRECTIONS_COUNT=0
if [ -f "$PROJECT_DIR/.claude/memory/corrections.md" ]; then
  CORRECTIONS_COUNT=$(awk '
    /^```/ { in_code = !in_code; next }
    !in_code && /^### / { count++ }
    END { print count+0 }
  ' "$PROJECT_DIR/.claude/memory/corrections.md" 2>/dev/null || echo 0)
fi

# ============================================================
# CHECK 3: Decision log check
# ============================================================
# Count ### headings OUTSIDE code blocks (same template-scaffolding concern)
DECISIONS_COUNT=0
if [ -f "$PROJECT_DIR/.claude/harness/decision-log.md" ]; then
  DECISIONS_COUNT=$(awk '
    /^```/ { in_code = !in_code; next }
    !in_code && /^### / { count++ }
    END { print count+0 }
  ' "$PROJECT_DIR/.claude/harness/decision-log.md" 2>/dev/null || echo "0")
fi

# ============================================================
# CHECK 4: Overdue feedback loops (Loop 3 cadence from feedback-loops.md)
# ============================================================
if [ -f "$CANVAS_DIR/bvssh-health.yml" ]; then
  BVSSH_OVERDUE=$(python3 -c "
import yaml, sys
from datetime import datetime, timezone
try:
  with open(sys.argv[1]) as f:
    data = yaml.safe_load(f) or {}
  last = data.get('last_assessed')
  if not last or last in ('null', 'None', None):
    print('never')
  else:
    d = datetime.fromisoformat(str(last).replace('Z','+00:00'))
    days = (datetime.now(timezone.utc) - d).days
    print('overdue' if days > 30 else 'ok')
except Exception: print('unknown')
" "$CANVAS_DIR/bvssh-health.yml" 2>/dev/null || echo "unknown")

  if [ "$BVSSH_OVERDUE" = "overdue" ] || [ "$BVSSH_OVERDUE" = "never" ]; then
    WARNINGS="${WARNINGS}FEEDBACK LOOP: BVSSH health check overdue (monthly cadence). Run /bvssh-check. "
  fi
fi

# Delivery metrics check -- routes to product-type-appropriate canvas (v0.11.0)
METRICS_CANVAS_STOP=""
PRODUCT_TYPE_STOP=$(python3 -c "
import yaml, sys
try:
  with open(sys.argv[1]) as f:
    data = yaml.safe_load(f) or {}
  pt = None
  for d in (data.get('active_diamonds') or []):
    if d.get('product_type'):
      pt = d['product_type']
      break
  print(pt or data.get('product_type') or 'software')
except Exception: print('software')
" "$PROJECT_DIR/.claude/diamonds/active.yml" 2>/dev/null || echo "software")

case "$PRODUCT_TYPE_STOP" in
  content_course|content_publication|content_media) METRICS_CANVAS_STOP="$CANVAS_DIR/content-metrics.yml" ;;
  ai_tool) METRICS_CANVAS_STOP="$CANVAS_DIR/ai-tool-metrics.yml" ;;
  service_offering) METRICS_CANVAS_STOP="$CANVAS_DIR/service-metrics.yml" ;;
  *) METRICS_CANVAS_STOP="$CANVAS_DIR/dora-metrics.yml" ;;
esac

if [ -f "$METRICS_CANVAS_STOP" ]; then
  METRICS_OVERDUE=$(python3 -c "
import yaml, sys
from datetime import datetime, timezone
try:
  with open(sys.argv[1]) as f:
    data = yaml.safe_load(f) or {}
  last = data.get('last_measured')
  if not last or last in ('null', 'None', None):
    print('ok')  # Don't nag if never measured -- SessionStart handles that
  else:
    d = datetime.fromisoformat(str(last).replace('Z','+00:00'))
    days = (datetime.now(timezone.utc) - d).days
    print('overdue' if days > 30 else 'ok')
except Exception: print('unknown')
" "$METRICS_CANVAS_STOP" 2>/dev/null || echo "unknown")

  if [ "$METRICS_OVERDUE" = "overdue" ]; then
    WARNINGS="${WARNINGS}FEEDBACK LOOP: Delivery metrics overdue (monthly cadence). Review delivery health. "
  fi
fi

# ============================================================
# CHECK 5: Direct diamond state edits (observability from diamond-state-audit.sh)
# ============================================================
# Count entries in the audit log for this session. If > 0, surface a reminder
# that /diamond-progress is the idiomatic path for diamond state transitions.
DIAMOND_DIRECT_EDITS=0
AUDIT_LOG="$PROJECT_DIR/.claude/state/diamond-state-audit.jsonl"
if [ -f "$AUDIT_LOG" ]; then
  DIAMOND_DIRECT_EDITS=$(wc -l < "$AUDIT_LOG" 2>/dev/null | tr -d ' ' || echo 0)
fi

if [ "$DIAMOND_DIRECT_EDITS" -gt 0 ]; then
  WARNINGS="${WARNINGS}OBSERVABILITY: ${DIAMOND_DIRECT_EDITS} direct diamond state edit(s) this session (outside /diamond-progress). Verify these were intentional -- /diamond-progress is the idiomatic path for gate evaluation and phase transitions. See .claude/state/diamond-state-audit.jsonl for details. "
fi

# ============================================================
# Build output
# ============================================================
# CHECK 8: Unreconciled reflexions — the learning loop's denominator
# ============================================================
# corrections.md was the numerator with nothing to divide by: an ignored
# reflexion looked exactly like one that never fired. reflexion-gate.sh now
# records each firing, and a reflexion is answered by a DECISION — either a
# corrections entry or an explicit dismissal with a reason. Silence is not a
# decision.
#
# Reports, never blocks. Learning debt should accumulate visibly (and resurface
# at SessionStart) rather than gate a session end.
RECONCILE="${CLAUDE_PLUGIN_ROOT}/scripts/reconcile_reflexions.py"
if [ -f "$RECONCILE" ]; then
  OUTSTANDING=$(python3 "$RECONCILE" --project-dir "$PROJECT_DIR" --json 2>/dev/null \
    | python3 -c "import json,sys;print(json.load(sys.stdin).get('outstanding',0))" 2>/dev/null || echo 0)
  if [ "${OUTSTANDING:-0}" -gt 0 ]; then
    WARNINGS="${WARNINGS}${OUTSTANDING} reflexion(s) fired this session and produced no recorded decision. Each needs a corrections.md entry OR 'reconcile_reflexions.py --dismiss \"why this was not a learning\"'. Run the script to see which commands. | "
  fi
fi

# ============================================================
# CHECK 9: the class no hook can see — asked in prose, deliberately
# ============================================================
# CHECK 8 only sees failures that FIRED the reflexion hook. The costlier class
# leaves no failure at all: a command that printed a confident wrong answer, or
# a fix applied inline while building and explained only in a code comment. Two
# of the three unlogged learnings that motivated this check were of that shape.
# No mechanical signal for it was found, so this asks — and is labelled a
# stopgap rather than dressed up as a mechanism.
if [ "$CORRECTIONS_COUNT" -gt 0 ] || [ -n "$WARNINGS" ]; then
  WARNINGS="${WARNINGS}Before ending: did you fix anything in-flight without recording it — a wrong answer you quietly re-ran, or a bug you fixed and explained only in a code comment? A code comment is read by whoever opens that file; corrections.md is read at every session start. | "
fi

# ============================================================
if [ -n "$WARNINGS" ]; then
  python3 -c "
import json, sys
warnings = sys.argv[1]
corrections = sys.argv[2]
decisions = sys.argv[3]
output = {
    'additionalContext': f'MYCELIUM GUARDRAIL WARNINGS: {warnings}Before completing, address these warnings or document why they are not applicable for this project type (check engine/canvas-guidance.yml in the plugin).',
    'systemMessage': f'Session: {corrections} corrections, {decisions} decisions logged.'
}
print(json.dumps(output))
" "$WARNINGS" "$CORRECTIONS_COUNT" "$DECISIONS_COUNT"
elif [ "$CORRECTIONS_COUNT" -gt 0 ] || [ "$DECISIONS_COUNT" -gt 0 ]; then
  # Surface counts only when something was actually logged this session.
  # Silence is the correct output when nothing happened — emitting
  # "Session ended. 0 corrections, 0 decisions logged." on every turn
  # reads as visual noise / error to first-run users (per opp-003).
  echo "{\"systemMessage\": \"Session: ${CORRECTIONS_COUNT} corrections, ${DECISIONS_COUNT} decisions logged.\"}"
fi

exit 0
