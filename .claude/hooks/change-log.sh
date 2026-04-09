#!/usr/bin/env bash
# Mycelium change log hook (PostToolUse on Edit|Write|MultiEdit)
#
# Appends one JSONL line per successful code modification to
# .claude/state/change-log.jsonl. Creates an audit trail that can be
# cross-referenced with diamond state to answer "what did the agent touch
# during diamond X."
#
# Based on BDSK's change-log pattern (Daniel Bentes feedback). Kept minimal:
# timestamp, tool, file_path, session_id, active_diamond_id (if any).
# No hash computation (keeps append fast, stays under POSIX atomic limit).
#
# Fail-open: audit logging failures never block code changes. A silent log
# failure is better than a broken edit workflow.

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
LOG_FILE="$PROJECT_DIR/.claude/state/change-log.jsonl"
STATE_FILE="$PROJECT_DIR/.claude/state/active-execution.json"

# Ensure state directory exists
mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || exit 0

# Read hook input from stdin
INPUT=$(cat)

# Delegate to Python stdlib for JSON handling
printf '%s' "$INPUT" | python3 -c "
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_FILE = '$LOG_FILE'
STATE_FILE = '$STATE_FILE'

# Parse hook input
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

if not isinstance(data, dict):
    sys.exit(0)

tool_name = data.get('tool_name', 'unknown')
tool_input = data.get('tool_input', {}) if isinstance(data.get('tool_input'), dict) else {}
file_path = tool_input.get('file_path', '')
session_id = data.get('session_id', '')

if not file_path:
    sys.exit(0)

# Look up active diamond_id if state file exists (best-effort)
diamond_id = None
try:
    if Path(STATE_FILE).exists():
        with open(STATE_FILE) as f:
            state = json.load(f)
        if isinstance(state, dict):
            diamond_id = state.get('diamond_id')
except Exception:
    pass  # fail-open: don't block logging on state file issues

entry = {
    'ts': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
    'tool': tool_name,
    'file_path': file_path,
    'session_id': session_id,
}
if diamond_id:
    entry['diamond_id'] = diamond_id

# Append as JSONL (one line, newline-terminated)
try:
    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(entry) + '\n')
except Exception:
    # Fail-open: logging failure never blocks code changes
    pass

sys.exit(0)
" 2>/dev/null

# Hook always exits 0 (observability-only, never blocks)
exit 0
