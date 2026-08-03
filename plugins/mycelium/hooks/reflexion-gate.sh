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

# The payload has carried the outcome all along; this gate never read it.
# codex-postfailure-shim.sh reads tool_response.exit_code / .is_error from the
# same envelope. Without them every firing looked identical in the log, so no
# one could tell a real failure from a grep that matched nothing.
EXIT_CODE=$(printf '%s' "$INPUT" | python3 -c "
import json, sys
try:
    r = json.load(sys.stdin).get('tool_response') or {}
    print(r.get('exit_code') if isinstance(r, dict) and r.get('exit_code') is not None else '')
except Exception:
    print('')
" 2>/dev/null || echo "")

STDERR_HEAD=$(printf '%s' "$INPUT" | python3 -c "
import json, sys
try:
    r = json.load(sys.stdin).get('tool_response') or {}
    s = (r.get('stderr') or '') if isinstance(r, dict) else ''
    print(' '.join(s.split())[:200])
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

# ============================================================
# DOCUMENTED NON-FAILURES (added 2026-08-03)
# ============================================================
# THE DEFECT: this gate fired on any non-zero exit, and several standard tools
# use non-zero to report a RESULT rather than an error. Their own man pages say
# so, so this is a category error rather than a judgement call:
#
#   grep(1)  "Exit status is 0 if any line is selected, 1 if no lines were
#            selected, and 2 if an error occurred."
#   diff(1)  0 = same, 1 = differences found, 2 = trouble.
#   test(1)  1 = the expression is false.
#
# MEASURED COST, dogfood 2026-08-03: 39 firings had accumulated, 23 of them in a
# single session, and the five most recent were all `grep`/`sed` reads. The
# counter reported "30 outstanding learnings" that were overwhelmingly greps
# finding nothing. It printed that at session start and was ignored — the correct
# response to a counter made of noise, and also how a guard dies.
#
# Suppressed firings are still LOGGED, with the reason. Dropping them silently
# would make this classifier unauditable, which is the failure one level up.
NON_EVENT=""
FIRST_WORD=$(printf '%s' "$COMMAND" | sed 's/^[[:space:]]*//' | cut -d' ' -f1 | xargs basename 2>/dev/null || echo "")
if [ "$EXIT_CODE" = "1" ]; then
  case "$FIRST_WORD" in
    grep|egrep|fgrep|rg|ugrep|zgrep)
      NON_EVENT="grep-family exit 1 = no match, not an error (grep(1))" ;;
    diff|colordiff)
      NON_EVENT="diff exit 1 = differences found, not an error (diff(1))" ;;
    test|[)
      NON_EVENT="test exit 1 = expression false, not an error (test(1))" ;;
    git)
      case "$COMMAND" in
        *"git diff"*|*"git grep"*)
          NON_EVENT="git diff/grep exit 1 = differences/no-match, not an error" ;;
      esac ;;
  esac
fi

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
    'exit_code': sys.argv[3] or None,
    'stderr_head': sys.argv[4] or None,
}
# A suppressed row stays in the log WITH its reason. Silent dropping would make
# the classifier unauditable — and an unauditable filter on a learning loop is
# the same defect the loop exists to catch.
if sys.argv[5]:
    rec['suppressed'] = sys.argv[5]
path = os.path.join(sys.argv[1], 'reflexion-log.jsonl')
try:
    with open(path, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(rec) + '\n')
except OSError:
    pass
" "$STATE_DIR" "$COMMAND" "$EXIT_CODE" "$STDERR_HEAD" "$NON_EVENT" 2>/dev/null || true

# A documented non-failure is recorded and then dropped: no prompt, no learning debt.
if [ -n "$NON_EVENT" ]; then
  exit 0
fi

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
