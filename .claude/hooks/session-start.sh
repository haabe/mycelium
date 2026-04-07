#!/bin/bash
# Mycelium SessionStart hook
# Checks for overdue strategic feedback loops and reminds the agent.
# Returns additionalContext with overdue loop warnings.

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
REMINDERS=""
NOW=$(date +%s)

# ============================================================
# CHECK 1: BVSSH health check cadence (monthly)
# ============================================================
if [ -f "$PROJECT_DIR/.claude/canvas/bvssh-health.yml" ]; then
  LAST_BVSSH=$(python3 -c "
import yaml, sys
try:
  with open(sys.argv[1]) as f:
    data = yaml.safe_load(f) or {}
  last = data.get('last_assessed')
  print(last if last else 'never')
except: print('never')
" "$PROJECT_DIR/.claude/canvas/bvssh-health.yml" 2>/dev/null || echo "never")

  if [ "$LAST_BVSSH" = "never" ] || [ "$LAST_BVSSH" = "null" ] || [ "$LAST_BVSSH" = "None" ]; then
    REMINDERS="${REMINDERS}BVSSH health has never been assessed. Consider running /bvssh-check. "
  else
    BVSSH_AGE=$(python3 -c "
from datetime import datetime
import sys
try:
  d = datetime.fromisoformat(sys.argv[1].replace('Z','+00:00'))
  print((datetime.now(d.tzinfo) - d).days)
except: print(999)
" "$LAST_BVSSH" 2>/dev/null || echo "999")
    if [ "$BVSSH_AGE" -gt 30 ]; then
      REMINDERS="${REMINDERS}BVSSH health check is ${BVSSH_AGE} days overdue (monthly cadence). Run /bvssh-check. "
    fi
  fi
fi

# ============================================================
# CHECK 2: DORA metrics cadence (per delivery cycle)
# ============================================================
if [ -f "$PROJECT_DIR/.claude/canvas/dora-metrics.yml" ]; then
  LAST_DORA=$(python3 -c "
import yaml, sys
try:
  with open(sys.argv[1]) as f:
    data = yaml.safe_load(f) or {}
  last = data.get('last_measured')
  print(last if last else 'never')
except: print('never')
" "$PROJECT_DIR/.claude/canvas/dora-metrics.yml" 2>/dev/null || echo "never")

  if [ "$LAST_DORA" != "never" ] && [ "$LAST_DORA" != "null" ] && [ "$LAST_DORA" != "None" ]; then
    DORA_AGE=$(python3 -c "
from datetime import datetime
import sys
try:
  d = datetime.fromisoformat(sys.argv[1].replace('Z','+00:00'))
  print((datetime.now(d.tzinfo) - d).days)
except: print(999)
" "$LAST_DORA" 2>/dev/null || echo "999")
    if [ "$DORA_AGE" -gt 30 ]; then
      REMINDERS="${REMINDERS}DORA metrics are ${DORA_AGE} days old. Run /dora-check to measure delivery health. "
    fi
  fi
fi

# ============================================================
# CHECK 3: Corrections count (awareness)
# ============================================================
CORRECTIONS_COUNT=0
if [ -f "$PROJECT_DIR/.claude/memory/corrections.md" ]; then
  CORRECTIONS_COUNT=$(grep -c '^### ' "$PROJECT_DIR/.claude/memory/corrections.md" 2>/dev/null || echo 0)
fi

# ============================================================
# Build output
# ============================================================
if [ -n "$REMINDERS" ]; then
  python3 -c "
import json, sys
reminders = sys.argv[1]
corrections = sys.argv[2]
output = {
    'hookSpecificOutput': {
        'hookEventName': 'SessionStart',
        'additionalContext': f'MYCELIUM FEEDBACK LOOPS: {reminders}Corrections in memory: {corrections}.'
    }
}
print(json.dumps(output))
" "$REMINDERS" "$CORRECTIONS_COUNT"
fi

exit 0
