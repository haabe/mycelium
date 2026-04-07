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
STAMP_FILE="/tmp/mycelium-preflight-stamp"
CORRECTIONS_FILE="$PROJECT_DIR/.claude/memory/corrections.md"

# Parse tool input from stdin
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("tool_name",""))' 2>/dev/null || echo "")
FILE_PATH=$(echo "$INPUT" | python3 -c 'import sys,json;d=json.load(sys.stdin);ti=d.get("tool_input",{});print(ti.get("file_path",ti.get("file","")))' 2>/dev/null || echo "")

# Always allow .claude/ edits (config/harness/canvas changes)
case "$FILE_PATH" in *".claude/"*) exit 0;; esac

# Only gate source code paths
case "$FILE_PATH" in
  *"/src/"*|*"/scripts/"*|*"/tests/"*|*"/test/"*|*"/lib/"*|*"/app/"*|*"/pages/"*|*"/components/"*|*"/server/"*|*"/api/"*) ;;
  *) exit 0;;
esac

# ============================================================
# CHECK 1: Secret detection in content being written (G-S1)
# ============================================================
# Extract content from Write or new_string from Edit
CONTENT=$(echo "$INPUT" | python3 -c '
import sys, json
d = json.load(sys.stdin)
ti = d.get("tool_input", {})
# Write tool uses "content", Edit uses "new_string"
print(ti.get("content", ti.get("new_string", "")))
' 2>/dev/null || echo "")

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

if [ "$NEEDS_RENEWAL" -eq 1 ]; then
  bash "$PROJECT_DIR/.claude/hooks/preflight.sh" 2>/dev/null || {
    echo '{"message": "Mycelium preflight required. Read corrections.md and run validation before code changes."}' >&2
    exit 2
  }
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
    echo '{"message": "corrections.md changed since last preflight. Re-read corrections and re-run preflight."}' >&2
    rm -f "$STAMP_FILE"
    exit 2
  fi
fi

exit 0
