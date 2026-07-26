#!/usr/bin/env bash
# Mycelium reflexion hook gate
#
# Filters PostToolUseFailure events to only trigger the reflexion prompt when
# the failure is project-relevant. Prevents reflexion from firing on:
#   - Self-inflicted agent failures outside the project directory
#     (e.g., probing ~/.claude/projects/<id>/memory/ which lives in user home)
#   - Environment/hardware failures unrelated to project work
#
# Addresses dogfood report findings G4 and M4: "Reflexion fired on a failure
# unrelated to the project, demanded writing to the wrong corrections file."
#
# Input:  Claude Code hook JSON on stdin
# Output: Either a reflexion prompt JSON (project-relevant) or empty (skipped)
# Exit:   Always 0 (this hook does not block)

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Read the hook input JSON from stdin
INPUT=$(cat)

# Extract cwd and command via python3 (safer than jq for arbitrary JSON)
CWD=$(printf '%s' "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('cwd', ''))
except Exception:
    print('')
" 2>/dev/null || echo "")

COMMAND=$(printf '%s' "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('command', ''))
except Exception:
    print('')
" 2>/dev/null || echo "")

# Decision logic:
# 1. If cwd is INSIDE the project directory → project-relevant → emit prompt
# 2. If cwd is OUTSIDE the project directory → skip (not our concern)
# 3. If cwd is empty → default to project-relevant (err on the side of catching real failures)

SHOULD_REFLEX=1
if [ -n "$CWD" ]; then
  # Normalize paths
  CWD_REAL=$(cd "$CWD" 2>/dev/null && pwd || echo "$CWD")
  PROJECT_REAL=$(cd "$PROJECT_DIR" 2>/dev/null && pwd || echo "$PROJECT_DIR")

  case "$CWD_REAL" in
    "$PROJECT_REAL"|"$PROJECT_REAL"/*)
      SHOULD_REFLEX=1
      ;;
    *)
      SHOULD_REFLEX=0
      ;;
  esac
fi

# Additional filter: skip known environmental/introspection commands
case "$COMMAND" in
  "which "*|"command -v "*|"type "*|"pwd"|"pwd "*|"whoami"|"whoami "*|"hostname"*|"uname "*|"date"|"date "*)
    SHOULD_REFLEX=0
    ;;
esac

if [ "$SHOULD_REFLEX" -eq 0 ]; then
  # Skip silently — the failure is not project-relevant
  exit 0
fi

# ============================================================
# RECORD THAT THIS FIRED — the missing half of the learning loop
# ============================================================
# Until 2026-07-26 this hook emitted a prompt and left NO trace. So nothing could
# ever ask the obvious question: how many reflexions fired, and how many produced
# a learning? corrections.md counts entries; there was no denominator, and an
# ignored reflexion was indistinguishable from one that never happened.
#
# Found by auditing a session in which three in-flight fixes went unrecorded. One
# of them DID fire this hook, was triaged as "environment, not a learning", and
# left nothing behind — a judgement call that is legitimate, but should leave a
# recorded decision rather than silence.
#
# One line per firing. reconcile_reflexions.py computes fired − reconciled.
STATE_DIR="$PROJECT_DIR/.claude/state"
mkdir -p "$STATE_DIR" 2>/dev/null
python3 -c "
import json, sys, os, time
rec = {
    'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'tool': 'Bash',
    'command_head': sys.argv[2][:160],
}
path = os.path.join(sys.argv[1], 'reflexion-log.jsonl')
try:
    with open(path, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(rec) + '\n')
except OSError:
    pass
" "$STATE_DIR" "$COMMAND" 2>/dev/null || true

# Emit the reflexion prompt as a command hook output
# This mirrors the inline prompt that was previously in settings.json
python3 -c "
import json, sys
prompt = '''REFLEXION REQUIRED: A command failed.

Analyze this failure:
1. What failed and why?
2. Is this a known pattern from .claude/memory/corrections.md?
3. What is the root cause (not just the symptom)?
4. What specific fix is needed?
5. Should this be logged as a new correction?

Do NOT retry blindly. Diagnose first.

After fixing: if this is a PROJECT-relevant mistake, draft a corrections.md entry with the mistake, correction, and prevention rule. Ask: 'Could this be generalized as a pattern in patterns.md?'

If this is an AGENT-USER learning (preference, communication style, tooling quirk), it belongs in your auto-memory, not project corrections.md. See CLAUDE.md two-memory-system section.

If this is an ENVIRONMENT failure (hardware, network, missing tools), it is not a learning — just fix and move on.'''

output = {
    'hookSpecificOutput': {
        'hookEventName': 'PostToolUseFailure',
        'additionalContext': prompt
    }
}
print(json.dumps(output))
"

exit 0
