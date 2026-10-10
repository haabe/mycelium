#!/bin/bash
. "$(dirname "${BASH_SOURCE[0]}")/../scripts/_state_ignore.sh" 2>/dev/null || true  # .claude/state never lacks its ignore file (v0.318.0)
# Mycelium contract part (SessionStart; v0.310.16). Emits part $1 of the operating contract.
#
# The contract used to ride inside session-start.sh's one additionalContext string, which Claude
# Code caps at 10,000 characters: over the cap the model saw a 2,000-character preview and the
# rest went to a file nobody read. Each part now has its own handler, so each stays under the cap.
# The split, the cap and the CI guard live in scripts/contract_parts.py. A part number past the
# last part prints nothing. Fail-open: a missing python3 or contract never blocks a session.
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
command -v python3 >/dev/null 2>&1 || exit 0
python3 "$here/../scripts/contract_parts.py" --part "${1:-1}" 2>/dev/null || true
exit 0
