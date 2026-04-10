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
# CHECK 2: Delivery metrics cadence (per delivery cycle)
# Routes to product-type-appropriate metrics canvas (v0.11.0)
# ============================================================
METRICS_CANVAS=""
METRICS_SKILL="/dora-check"
METRICS_LABEL="Delivery metrics"

# Determine which metrics canvas to check based on product_type.
# product_type is per-diamond (v0.11.0). Use the first active diamond's type,
# falling back to root-level product_type (legacy), then to 'software'.
PRODUCT_TYPE=$(python3 -c "
import yaml, sys
try:
  with open(sys.argv[1]) as f:
    data = yaml.safe_load(f) or {}
  diamonds = data.get('active_diamonds', [])
  for d in diamonds:
    pt = d.get('product_type')
    if pt:
      print(pt)
      sys.exit(0)
  print(data.get('product_type', 'software') or 'software')
except: print('software')
" "$PROJECT_DIR/.claude/diamonds/active.yml" 2>/dev/null || echo "software")

case "$PRODUCT_TYPE" in
  content_course|content_publication|content_media)
    METRICS_CANVAS="$PROJECT_DIR/.claude/canvas/content-metrics.yml"
    METRICS_LABEL="Content delivery metrics"
    ;;
  ai_tool)
    METRICS_CANVAS="$PROJECT_DIR/.claude/canvas/ai-tool-metrics.yml"
    METRICS_LABEL="AI tool metrics"
    ;;
  service_offering)
    METRICS_CANVAS="$PROJECT_DIR/.claude/canvas/service-metrics.yml"
    METRICS_LABEL="Service delivery metrics"
    ;;
  *)
    METRICS_CANVAS="$PROJECT_DIR/.claude/canvas/dora-metrics.yml"
    METRICS_LABEL="DORA metrics"
    ;;
esac

if [ -f "$METRICS_CANVAS" ]; then
  LAST_MEASURED=$(python3 -c "
import yaml, sys
try:
  with open(sys.argv[1]) as f:
    data = yaml.safe_load(f) or {}
  last = data.get('last_measured')
  print(last if last else 'never')
except: print('never')
" "$METRICS_CANVAS" 2>/dev/null || echo "never")

  if [ "$LAST_MEASURED" != "never" ] && [ "$LAST_MEASURED" != "null" ] && [ "$LAST_MEASURED" != "None" ]; then
    METRICS_AGE=$(python3 -c "
from datetime import datetime
import sys
try:
  d = datetime.fromisoformat(sys.argv[1].replace('Z','+00:00'))
  print((datetime.now(d.tzinfo) - d).days)
except: print(999)
" "$LAST_MEASURED" 2>/dev/null || echo "999")
    if [ "$METRICS_AGE" -gt 30 ]; then
      REMINDERS="${REMINDERS}${METRICS_LABEL} are ${METRICS_AGE} days old. Review delivery health. "
    fi
  fi
fi

# ============================================================
# CHECK 3: Corrections count (awareness)
# ============================================================
# Count ### headings OUTSIDE code blocks (the template includes an example
# heading inside a ```...``` fence that must not be counted as a real correction)
CORRECTIONS_COUNT=0
if [ -f "$PROJECT_DIR/.claude/memory/corrections.md" ]; then
  CORRECTIONS_COUNT=$(awk '
    /^```/ { in_code = !in_code; next }
    !in_code && /^### / { count++ }
    END { print count+0 }
  ' "$PROJECT_DIR/.claude/memory/corrections.md" 2>/dev/null || echo 0)
fi

# ============================================================
# CHECK 4: External evidence ratio (v0.11.0)
# ============================================================
# Scan canvas provenance for source_classes. Warn if all evidence is internal.
EVIDENCE_WARNING=$(python3 -c "
import yaml, glob, sys, os

project_dir = sys.argv[1]
canvas_dir = os.path.join(project_dir, '.claude', 'canvas')
if not os.path.isdir(canvas_dir):
    sys.exit(0)

total = 0
external = 0

def scan(obj):
    global total, external
    if isinstance(obj, dict):
        if 'evidence_sources' in obj:
            sources = obj.get('evidence_sources', [])
            classes = obj.get('source_classes', [])
            for i, src in enumerate(sources):
                if not src:
                    continue
                total += 1
                if i < len(classes) and classes[i] in ('external_human', 'external_data'):
                    external += 1
        for v in obj.values():
            scan(v)
    elif isinstance(obj, list):
        for item in obj:
            scan(item)

for f in glob.glob(os.path.join(canvas_dir, '*.yml')):
    try:
        with open(f) as fh:
            data = yaml.safe_load(fh)
            if data:
                scan(data)
    except:
        pass

if total > 3 and external == 0:
    print('All {} evidence sources are desk-derived. No external human conversations logged. Consider /handoff to plan a real interview.'.format(total))
elif total > 5 and external > 0 and (external / total) < 0.2:
    print('External evidence is thin ({}/{} sources). Consider more external conversations via /handoff.'.format(external, total))
" "$PROJECT_DIR" 2>/dev/null || echo "")

if [ -n "$EVIDENCE_WARNING" ]; then
  REMINDERS="${REMINDERS}${EVIDENCE_WARNING} "
fi

# ============================================================
# CHECK 5: Pending human tasks (v0.11.0)
# ============================================================
if [ -f "$PROJECT_DIR/.claude/canvas/human-tasks.yml" ]; then
  HUMAN_TASKS=$(python3 -c "
import yaml, sys
try:
  with open(sys.argv[1]) as f:
    data = yaml.safe_load(f) or {}
  pending = data.get('pending_tasks', [])
  if pending:
    objectives = [t.get('objective', 'unnamed task') for t in pending]
    summaries = '; '.join(objectives[:3])
    if len(objectives) > 3:
      summaries += '... and {} more'.format(len(objectives) - 3)
    print('You have {} pending human task(s). If you completed any offline conversations, run /log-evidence. Pending: {}'.format(len(pending), summaries))
except: pass
" "$PROJECT_DIR/.claude/canvas/human-tasks.yml" 2>/dev/null || echo "")

  if [ -n "$HUMAN_TASKS" ]; then
    REMINDERS="${REMINDERS}${HUMAN_TASKS} "
  fi
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
