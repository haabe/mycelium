#!/usr/bin/env bash
# Mycelium read log hook (PostToolUse on Read|Bash)
#
# Appends one JSONL line per file the agent opened, to
# .claude/state/read-log.jsonl.
#
# BASH READS ADDED v0.143.0, from a measured failure rather than for
# completeness. This hook was bound to the Read tool alone, so reads performed
# with cat/head/sed/grep/python were logged NOWHERE -- and sessions are routinely
# instructed to prefer Bash, so the record of what the agent consulted was
# near-empty by construction: 3,401 rows on the dogfood repo, every one from the
# Read tool. On 2026-08-31 an agent characterised four canvas records it had
# never opened -- a user_type field, two breadth_notes, a kill_criterion date --
# all four caught by the operator and none by any check, because nothing could
# tell that the records were unread.
#
# AN INFERRED READ IS NOT AN OBSERVED ONE, AND THE LOG SAYS SO. A Read tool call
# is proof a file was opened. A path named in a shell command is evidence it was
# consulted: strong, but inference. Bash rows carry inferred=true so a consumer
# can weight or ignore them rather than discovering the distinction later.
# Creates session-scoped evidence of which files the agent actually opened —
# the ground truth that `verify_citations.py` cross-references against the
# agent's citation claims to detect Level-3 anti-pattern #7 instances
# (fabricated file references in `(per: <source>)` citations).
#
# Sister mechanism to change-log.sh (which logs Write|Edit|MultiEdit).
# Together they answer: "what did the agent claim to read, read, and write
# during session X?"
#
# Schema (per line): {ts, tool: "Read"|"Bash", file_path, session_id,
#                    inferred?: true, diamond_id?}
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
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_FILE = '$LOG_FILE'
STATE_FILE = '$STATE_FILE'
PROJECT_DIR = '$PROJECT_DIR'

# Parse hook input
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

if not isinstance(data, dict):
    sys.exit(0)

tool_name = data.get('tool_name', 'unknown')
tool_input = data.get('tool_input', {}) if isinstance(data.get('tool_input'), dict) else {}
session_id = data.get('session_id', '')

# Commands that READ. A path named by rm, git add or mkdir is not a
# consultation, and logging it would inflate the very record this exists to make
# trustworthy -- it would let an agent 'prove' it read what it only deleted.
READ_VERBS = ('cat', 'head', 'tail', 'sed', 'grep', 'rg', 'egrep', 'awk',
              'less', 'more', 'diff', 'wc', 'jq', 'yq', 'python3', 'python')


def _bash_paths(command, project_dir):
    # Existing project files that a read-shaped command names.
    # Conservative on three axes, because a log that over-reports is worse than
    # one that under-reports:
    #   * a READ VERB must appear, so rm/git-add/mkdir are excluded;
    #   * the path must EXIST on disk, which drops globs, typos and prose;
    #   * it must resolve INSIDE the project, which drops /tmp scratch.
    # Redirect targets are stripped first: '> out.txt' is a write, not a read.
    if not any(re.search(r'(?:^|[\s;|&(])' + v + r'\b', command)
               for v in READ_VERBS):
        return []
    stripped = re.sub(r'[12]?>>?\s*\S+', ' ', command)
    try:
        root = Path(project_dir).resolve()
    except OSError:
        return []
    out, seen = [], set()
    for tok in re.findall(r'[\w./~-]*[\w-]\.[A-Za-z][\w]{0,7}', stripped):
        try:
            cand = Path(os.path.expanduser(tok))
            full = (cand if cand.is_absolute() else root / cand).resolve()
            if not full.is_file():
                continue
            full.relative_to(root)
        except (OSError, ValueError):
            continue
        s = str(full)
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


if tool_name == 'Bash':
    paths = _bash_paths(tool_input.get('command', '') or '', PROJECT_DIR)
    inferred = True
else:
    fp = tool_input.get('file_path', '')
    paths = [fp] if fp else []
    inferred = False

if not paths:
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

# Append as JSONL, one line per distinct path (newline-terminated)
try:
    with open(LOG_FILE, 'a') as f:
        for file_path in paths:
            entry = {
                'ts': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                'tool': tool_name,
                'file_path': file_path,
                'session_id': session_id,
            }
            if inferred:
                entry['inferred'] = True
            if diamond_id:
                entry['diamond_id'] = diamond_id
            f.write(json.dumps(entry) + '\n')
except Exception:
    # Fail-open: logging failure never blocks reads
    pass

sys.exit(0)
" 2>/dev/null

# Hook always exits 0 (observability-only, never blocks)
exit 0
