#!/usr/bin/env bash
. "$(dirname "${BASH_SOURCE[0]}")/../scripts/_hook_prelude.sh" 2>/dev/null || true  # no-op outside a Mycelium project; state ignore file (v0.318.0)
# Mycelium change log hook (PostToolUse on Edit|Write|MultiEdit)
#
# Appends one JSONL line per successful code modification to
# .claude/state/change-log.jsonl. Creates an audit trail that can be
# cross-referenced with diamond state to answer "what did the agent touch
# during diamond X."
#
# Based on BDSK's change-log pattern (Daniel Bentes feedback). Kept minimal:
# timestamp, tool, file_path, session_id.
# Until 0.324.0 a row could also carry `diamond_id`, read from
# .claude/state/active-execution.json. Nothing Mycelium ships ever wrote that file, so no row
# carried it, and since 0.324.0 the file is read by nothing.
# No hash computation (keeps append fast, stays under POSIX atomic limit).
#
# Fail-open: audit logging failures never block code changes. A silent log
# failure is better than a broken edit workflow.

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
LOG_FILE="$PROJECT_DIR/.claude/state/change-log.jsonl"

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

entry = {
    'ts': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
    'tool': tool_name,
    'file_path': file_path,
    'session_id': session_id,
}

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
