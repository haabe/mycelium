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
except: print('unknown')
" "$CANVAS_DIR/bvssh-health.yml" 2>/dev/null || echo "unknown")

  if [ "$BVSSH_OVERDUE" = "overdue" ] || [ "$BVSSH_OVERDUE" = "never" ]; then
    WARNINGS="${WARNINGS}FEEDBACK LOOP: BVSSH health check overdue (monthly cadence). Run /bvssh-check. "
  fi
fi

if [ -f "$CANVAS_DIR/dora-metrics.yml" ]; then
  DORA_OVERDUE=$(python3 -c "
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
except: print('unknown')
" "$CANVAS_DIR/dora-metrics.yml" 2>/dev/null || echo "unknown")

  if [ "$DORA_OVERDUE" = "overdue" ]; then
    WARNINGS="${WARNINGS}FEEDBACK LOOP: DORA metrics overdue (monthly cadence). Run /dora-check. "
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
if [ -n "$WARNINGS" ]; then
  python3 -c "
import json, sys
warnings = sys.argv[1]
corrections = sys.argv[2]
decisions = sys.argv[3]
output = {
    'additionalContext': f'MYCELIUM GUARDRAIL WARNINGS: {warnings}Before completing, address these warnings or document why they are not applicable for this project type (check .claude/engine/canvas-guidance.yml).',
    'systemMessage': f'Session: {corrections} corrections, {decisions} decisions logged.'
}
print(json.dumps(output))
" "$WARNINGS" "$CORRECTIONS_COUNT" "$DECISIONS_COUNT"
else
  echo "{\"systemMessage\": \"Session ended. ${CORRECTIONS_COUNT} corrections, ${DECISIONS_COUNT} decisions logged.\"}"
fi

exit 0
