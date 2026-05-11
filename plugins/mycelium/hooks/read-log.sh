#!/usr/bin/env bash
# Mycelium read log hook (PostToolUse on Read)
#
# Appends one JSONL line per Read tool use to .claude/state/read-log.jsonl.
# Creates session-scoped evidence of which files the agent actually opened —
# the ground truth that `verify_citations.py` cross-references against the
# agent's citation claims to detect Level-3 anti-pattern #7 instances
# (fabricated file references in `(per: <source>)` citations).
#
# Sister mechanism to change-log.sh (which logs Write|Edit|MultiEdit).
# Together they answer: "what did the agent claim to read, read, and write
# during session X?"
#
# Schema (per line): {ts, tool: "Read", file_path, session_id, diamond_id?}
#
# Fail-open: audit logging failures never block reads. Observability-only.

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
LOG_FILE="$PROJECT_DIR/.claude/state/read-log.jsonl"
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
    pass  # fail-open

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
    # Fail-open: logging failure never blocks reads
    pass

sys.exit(0)
" 2>/dev/null

# Hook always exits 0 (observability-only, never blocks)
exit 0
