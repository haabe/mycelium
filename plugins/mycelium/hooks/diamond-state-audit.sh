#!/usr/bin/env bash
# Mycelium diamond state audit hook (PostToolUse on Edit|Write|MultiEdit)
#
# Observability-only hook that logs direct edits to diamond state files
# (.claude/diamonds/*.yml) to .claude/state/diamond-state-audit.jsonl.
#
# This is NOT a guardrail (does not block). It creates an audit trail for
# the dogfood report finding M1 ("agent bypassed /diamond-progress by
# hand-editing state files"). The agent can still edit these files, but
# the edit becomes visible via the audit log, and stop-check.sh surfaces
# the count at session end.
#
# Why observability instead of BLOCK: the hook cannot reliably distinguish
# between edits from `/diamond-progress` (legitimate) and direct agent edits
# (bypass). A false-positive block would prevent legitimate skill operation.
# Observability creates friction and traceability without false positives.
#
# Fail-open: audit failures never block.

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
AUDIT_LOG="$PROJECT_DIR/.claude/state/diamond-state-audit.jsonl"

mkdir -p "$(dirname "$AUDIT_LOG")" 2>/dev/null || exit 0

INPUT=$(cat)

printf '%s' "$INPUT" | python3 -c "
import json
import sys
from datetime import datetime, timezone

AUDIT_LOG = '$AUDIT_LOG'

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

if not isinstance(data, dict):
    sys.exit(0)

tool_input = data.get('tool_input', {}) if isinstance(data.get('tool_input'), dict) else {}
file_path = tool_input.get('file_path', '')

# Only fire on diamond state files
if not file_path:
    sys.exit(0)

# Normalize: ensure leading / so patterns match relative paths too
if not file_path.startswith('/'):
    file_path = '/' + file_path

if '/.claude/diamonds/' not in file_path:
    sys.exit(0)

tool_name = data.get('tool_name', 'unknown')
session_id = data.get('session_id', '')

entry = {
    'ts': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
    'event': 'direct_diamond_state_edit',
    'tool': tool_name,
    'file_path': file_path,
    'session_id': session_id,
    'note': 'Direct edit to diamond state file outside /diamond-progress. Verify this was intentional.',
}

try:
    with open(AUDIT_LOG, 'a') as f:
        f.write(json.dumps(entry) + '\n')
except Exception:
    pass

sys.exit(0)
" 2>/dev/null

exit 0
