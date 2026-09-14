#!/bin/bash
# Mycelium PreToolUse gate
# Lightweight check before code changes. Exit 0 = allow, Exit 2 = block.
#
# Layer 1 of Mycelium's 6-layer enforcement architecture.
# Fires on every Write/Edit/MultiEdit to source code.
#
# Checks:
# 1. Preflight stamp freshness (corrections.md read recently)
# 2. Corrections.md not stale since last preflight
# 3. Secret detection in content being written (G-S1 ENFORCED)

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
CORRECTIONS_FILE="$PROJECT_DIR/.claude/memory/corrections.md"

# Stamp path: per-user + per-project under $TMPDIR. The old shared
# /tmp/mycelium-preflight-stamp was world-predictable — any local user could
# pre-create or symlink it (clobber / privacy) and two projects/users on one
# box collided on a single stamp. preflight.sh derives this identically.
_stamp_uid=$(id -u 2>/dev/null || echo 0)
_stamp_phash=$(printf '%s' "$PROJECT_DIR" | { md5 2>/dev/null || md5sum 2>/dev/null; } | tr -cd '0-9a-f' | cut -c1-12)
STAMP_FILE="${TMPDIR:-/tmp}/mycelium-preflight-stamp-${_stamp_uid}-${_stamp_phash:-0}"

# Parse tool input from stdin. Single python spawn (not two) emits tool_name
# and file_path NUL-separated — this hook is on the Write/Edit hot path, so we
# avoid paying a second interpreter startup per edit. NUL separation keeps it
# correct even if a path contained a newline. On parse failure both vars stay
# empty (same fallback as before).
# shellcheck disable=SC2034  # INPUT is read by hi_read_input in the sourced library
INPUT=$(cat)
HI_LIB="$(dirname "${BASH_SOURCE[0]}")/../scripts/_hook_input_read.sh"
# shellcheck source=/dev/null
. "$HI_LIB"
hi_read_input
if [ -n "$HI_BAD" ]; then
  hi_deny "Mycelium gate: refused, tool input is not the documented shape ($HI_BAD). A guard that cannot read the call does not guess (adversarial pass 2026-09-11)."
fi

# CHECK 0: guard state is human-owned. A write to the file that switches a blocking hook off asks
# the person; the agent cannot answer for them (adversarial pass 2026-09-11, every off-switch was
# agent-writable). MYCELIUM_GUARD_STATE_EDIT=1 in the human's own shell skips the ask.
if [ "${MYCELIUM_GUARD_STATE_EDIT:-}" != "1" ]; then
  while IFS=$'\t' read -r target _exists _size; do
    case "$target" in
      GUARD:*) hi_ask "Mycelium gate: ${target#GUARD:} switches a blocking hook off, and this tool call writes it. A person decides that, not the agent. Approve if you asked for it; set MYCELIUM_GUARD_STATE_EDIT=1 in your own shell for setup work.";;
    esac
  done <<< "$HI_TARGETS"
fi

# Which targets does the secret scan apply to? Every real path inside the project that is not
# under .claude/ (2026-09-11: config.py, source/, Src/ were all outside the old directory list).
SCAN=0
while IFS=$'\t' read -r target _exists _size; do
  case "$target" in
    ""|OUTSIDE:*|GUARD:*|OPAQUE:*) ;;
    .claude/*) ;;
    *) SCAN=1;;
  esac
done <<< "$HI_TARGETS"
[ "$HI_TOOL" = "Bash" ] && SCAN=1   # the command text itself can carry the secret
[ "$SCAN" = "1" ] || exit 0

# ============================================================
# CHECK 1: Secret detection in content being written (G-S1)
# ============================================================
CONTENT="$HI_CONTENT"

if [ -n "$CONTENT" ]; then
  # Check for common secret patterns
  # API keys, tokens, passwords, connection strings
  SECRET_PATTERNS=(
    '[Aa][Pp][Ii]_?[Kk][Ee][Yy]\s*[=:]\s*["\x27][A-Za-z0-9_\-]{20,}'
    '[Ss][Ee][Cc][Rr][Ee][Tt]_?[Kk][Ee][Yy]\s*[=:]\s*["\x27][A-Za-z0-9_\-]{20,}'
    '[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]\s*[=:]\s*["\x27][^\s"\x27]{8,}'
    'Bearer\s+[A-Za-z0-9_\-\.]{20,}'
    'sk-[A-Za-z0-9]{20,}'
    'ghp_[A-Za-z0-9]{36}'
    'gho_[A-Za-z0-9]{36}'
    'glpat-[A-Za-z0-9\-]{20,}'
    'xox[bpas]-[A-Za-z0-9\-]{10,}'
    'AKIA[0-9A-Z]{16}'
    'eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.'
    '[Pp][Rr][Ii][Vv][Aa][Tt][Ee]_?[Kk][Ee][Yy]\s*[=:]\s*["\x27]'
    'mongodb\+srv://[^"\x27\s]{10,}'
    'postgres://[^"\x27\s]{10,}'
    'mysql://[^"\x27\s]{10,}'
    'redis://[^"\x27\s]*:[^"\x27\s]*@'
  )

  for PATTERN in "${SECRET_PATTERNS[@]}"; do
    if echo "$CONTENT" | grep -qE "$PATTERN" 2>/dev/null; then
      # Output JSON for Claude with deny decision
      cat << 'DENY_EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "GUARDRAIL G-S1 VIOLATION: Potential secret/credential detected in code being written. Secrets must never be hardcoded. Use environment variables or a secrets manager instead. Review the content and remove any API keys, tokens, passwords, or connection strings."
  }
}
DENY_EOF
      exit 0
    fi
  done
fi

# ============================================================
# CHECK 2: Preflight stamp freshness
# ============================================================
NEEDS_RENEWAL=0
if [ ! -f "$STAMP_FILE" ]; then
  NEEDS_RENEWAL=1
else
  STAMP_MOD=$(stat -f %m "$STAMP_FILE" 2>/dev/null || stat -c %Y "$STAMP_FILE" 2>/dev/null || echo 0)
  STAMP_AGE=$(( $(date +%s) - STAMP_MOD ))
  if [ "$STAMP_AGE" -gt 14400 ]; then
    NEEDS_RENEWAL=1
  fi
fi

# A BLOCK LEAVES A LINE (v0.204.0). gate.sh exits 2 on a stale preflight stamp or a changed
# corrections hash, mid-session, on every source write, and until now wrote nothing anywhere
# when it did: no log, no session id, no count. The one human complaint on record about
# "too many gates" (plugin 0.23.4) predates every hook that was checked when it was ruled
# on, and this is the hook that fires repeatedly mid-flow; whether it fires on real users
# was unmeasurable for the same reason discovery-gate's was. One JSON line per block to
# .claude/state/gate-block-log.jsonl (gitignored with the rest of state/), read by
# check_hook_delivery.py. Best effort: a log that cannot be written never changes the verdict.
_gate_block_log() {  # $1 reason
  local dir="$PROJECT_DIR/.claude/state"
  mkdir -p "$dir" 2>/dev/null || return 0
  printf '%s' "$INPUT" | python3 -c '
import json, sys, datetime
reason = sys.argv[1]
try:
    sid = (json.load(sys.stdin) or {}).get("session_id", "")
except Exception:
    sid = ""
ts = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
print(json.dumps({"ts": ts, "hook": "gate.sh", "reason": reason, "session_id": sid}))
' "$1" >> "$dir/gate-block-log.jsonl" 2>/dev/null || true
}

if [ "$NEEDS_RENEWAL" -eq 1 ]; then
  # Preflight resolution — prefer plugin path (post-0.20.x), fall back to legacy.
  # Mirrors framework-guard.sh: plugin installs have no .claude/hooks/ tree, so
  # the hardcoded legacy path silently no-op'd (2>/dev/null swallowed the missing
  # file) and preflight never ran for plugin users.
  PREFLIGHT=""
  if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/hooks/preflight.sh" ]; then
    PREFLIGHT="${CLAUDE_PLUGIN_ROOT}/hooks/preflight.sh"
  elif [ -f "$PROJECT_DIR/.claude/hooks/preflight.sh" ]; then
    PREFLIGHT="$PROJECT_DIR/.claude/hooks/preflight.sh"
  fi
  if [ -n "$PREFLIGHT" ]; then
    bash "$PREFLIGHT" 2>/dev/null || {
      _gate_block_log "stale-stamp"
      echo '{"message": "Mycelium preflight required. Read corrections.md and run validation before code changes."}' >&2
      exit 2
    }
  fi
fi

# ============================================================
# CHECK 3: Corrections.md hash consistency
# ============================================================
if [ -f "$CORRECTIONS_FILE" ] && [ -f "$STAMP_FILE" ]; then
  if command -v md5 &>/dev/null; then
    CURRENT_HASH=$(md5 -q "$CORRECTIONS_FILE")
  elif command -v md5sum &>/dev/null; then
    CURRENT_HASH=$(md5sum "$CORRECTIONS_FILE" | cut -d' ' -f1)
  else
    CURRENT_HASH="unknown"
  fi

  STAMP_HASH=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["corrections_hash"])' "$STAMP_FILE" 2>/dev/null || echo "")

  if [ "$CURRENT_HASH" != "unknown" ] && [ -n "$STAMP_HASH" ] && [ "$CURRENT_HASH" != "$STAMP_HASH" ]; then
    _gate_block_log "corrections-hash"
    echo '{"message": "corrections.md changed since last preflight. Re-read corrections and re-run preflight."}' >&2
    rm -f "$STAMP_FILE"
    exit 2
  fi
fi

exit 0
